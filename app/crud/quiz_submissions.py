from bson import ObjectId
from datetime import datetime
from app.db.database import db
from typing import Optional, Tuple

# --- helper: serialize submission for API ---
def serialize_submission(submission: dict) -> dict:
    """
    Convert MongoDB doc to JSON-friendly dict,
    converting ObjectIds to strings and preserving answers.
    """
    return {
        "id": str(submission["_id"]),
        "studentId": str(submission["studentId"]),
        "quizId": str(submission["quizId"]),
        "courseId": str(submission["courseId"]),
        "tenantId": str(submission["tenantId"]),
        "submittedAt": submission["submittedAt"],
        "answers": submission.get("answers", []),
        "percentage": submission.get("percentage"),
        "obtainedMarks": submission.get("obtainedMarks"),
        "status": submission.get("status", "pending"),
    }

# -------------------------
# Submit answers and auto-grade immediately
# -------------------------
async def submit_and_grade_submission(payload):
    """
    1) store student submission (answers)
    2) fetch quiz, compare answers
    3) calculate obtainedMarks & percentage
    4) update submission document with grading results
    5) return serialized submission
    """
    # Convert request model -> dict
    data = payload.dict()

    # Convert ID strings to ObjectId for DB storage/queries
    data.update({
        "studentId": ObjectId(data["studentId"]),
        "quizId": ObjectId(data["quizId"]),
        "courseId": ObjectId(data["courseId"]),
        "tenantId": ObjectId(data["tenantId"]),
        "submittedAt": datetime.utcnow(),
        "status": "pending",  # initially pending until graded
    })

    # Prevent duplicate submission (optional policy)
    existing = await db.quizSubmissions.find_one({
        "studentId": data["studentId"],
        "quizId": data["quizId"]
    })
    if existing:
        # If duplicate, we can choose to reject or re-grade — here return a specific flag
        return "AlreadySubmitted"

    # Insert the raw submission first
    res = await db.quizSubmissions.insert_one(data)
    submission_doc = await db.quizSubmissions.find_one({"_id": res.inserted_id})

    # Fetch the quiz document to grade
    quiz = await db.quizzes.find_one({"_id": ObjectId(data["quizId"])})
    if not quiz:
        # If quiz not found, mark submission as failed (should ideally never happen)
        await db.quizSubmissions.update_one(
            {"_id": res.inserted_id},
            {"$set": {"status": "error", "percentage": None, "obtainedMarks": None}}
        )
        return None

    # Perform auto-marking
    obtained_marks, total_marks, per_question_details = _grade_submission(quiz, submission_doc)

    # Calculate percentage
    percentage = (obtained_marks / total_marks) * 100 if total_marks > 0 else 0.0
    percentage = round(percentage, 2)

    # Update the submission document with grading results
    await db.quizSubmissions.update_one(
        {"_id": res.inserted_id},
        {"$set": {
            "obtainedMarks": obtained_marks,
            "percentage": percentage,
            "status": "graded",
            "gradedAt": datetime.utcnow(),
            "gradingDetails": per_question_details  # optional: store per-question correctness
        }}
    )

    # Fetch updated submission and return serialized
    updated = await db.quizSubmissions.find_one({"_id": res.inserted_id})
    return serialize_submission(updated)


# -------------------------
# Internal pure function to grade a submission against a quiz
# Returns (obtained_marks, total_marks, per_question_details)
# -------------------------
def _grade_submission(quiz_doc: dict, submission_doc: dict) -> Tuple[float, float, list[dict]]:
    """
    - quiz_doc['questions'] is expected to be list of objects with 'answer' and 'totalMarks' (if per-question marks)
    - submission_doc['answers'] is list of items {questionIndex, selected}
    - scoring strategy:
       * If quiz.questions includes explicit per-question marks (e.g., question.get('marks')), use that.
       * Otherwise divide quiz['totalMarks'] equally across questions.
    """
    questions = quiz_doc.get("questions", [])
    total_quiz_marks = quiz_doc.get("totalMarks", len(questions)) or len(questions)

    # Determine marks per question if not specified individually
    marks_per_question = []
    explicit_marks_present = False
    for q in questions:
        if isinstance(q, dict) and q.get("marks") is not None:
            explicit_marks_present = True
            break

    if explicit_marks_present:
        # use each question's 'marks' field if present, default to 1 if missing
        for q in questions:
            marks_per_question.append(float(q.get("marks", 1)))
    else:
        # fair split
        per_q = float(total_quiz_marks) / max(len(questions), 1)
        marks_per_question = [per_q for _ in questions]

    # build a mapping from questionIndex -> selected for quick lookup
    answer_map = {a["questionIndex"]: a["selected"] for a in submission_doc.get("answers", [])}

    obtained = 0.0
    per_q_details = []

    # iterate each question and award marks if answer matches quiz's 'answer'
    for idx, q in enumerate(questions):
        correct_answer = None
        if isinstance(q, dict):
            correct_answer = q.get("answer")
        else:
            # if stored as Pydantic dicts they should be dict-like, but protect anyway
            correct_answer = None

        selected = answer_map.get(idx, None)
        q_marks = marks_per_question[idx] if idx < len(marks_per_question) else 0.0

        # determine correctness
        is_correct = (selected is not None) and (selected == correct_answer)
        awarded = q_marks if is_correct else 0.0

        obtained += awarded

        per_q_details.append({
            "questionIndex": idx,
            "selected": selected,
            "correctAnswer": correct_answer,
            "isCorrect": is_correct,
            "awardedMarks": awarded,
            "possibleMarks": q_marks
        })

    return obtained, total_quiz_marks, per_q_details


# -------------------------
# QUIZ RESULTS SUMMARY (for a given quiz)
# returns aggregated stats: count, average, topScores, distribution
# -------------------------
async def get_quiz_summary(quiz_id: str, top_n: int = 5):
    """
    Uses MongoDB aggregation to compute:
      - totalAttempts
      - averagePercentage
      - averageMarks
      - top N scores (studentId, obtainedMarks, percentage)
      - passRate (percentage >= 50)
      - distribution bins (0-10,10-20,...90-100)
    """
    q_oid = ObjectId(quiz_id)

    # pipeline: filter submissions for quiz and graded only
    pipeline = [
        {"$match": {"quizId": q_oid, "status": "graded"}},
        {
            "$group": {
                "_id": None,
                "totalAttempts": {"$sum": 1},
                "avgPercentage": {"$avg": "$percentage"},
                "avgMarks": {"$avg": "$obtainedMarks"},
            }
        }
    ]
    basic = await db.quizSubmissions.aggregate(pipeline).to_list(length=1)
    basic_stats = basic[0] if basic else {"totalAttempts": 0, "avgPercentage": None, "avgMarks": None}

    # top N scores
    top_cursor = db.quizSubmissions.find(
        {"quizId": q_oid, "status": "graded"},
        {"studentId": 1, "obtainedMarks": 1, "percentage": 1}
    ).sort("obtainedMarks", -1).limit(top_n)
    top_list = []
    async for doc in top_cursor:
        top_list.append({
            "studentId": str(doc["studentId"]),
            "obtainedMarks": doc.get("obtainedMarks"),
            "percentage": doc.get("percentage")
        })

    # pass rate (>=50) and distribution bins using aggregation
    pass_pipeline = [
        {"$match": {"quizId": q_oid, "status": "graded"}},
        {"$group": {
            "_id": None,
            "passCount": {"$sum": {"$cond": [{"$gte": ["$percentage", 50]}, 1, 0]}},
            "total": {"$sum": 1}
        }}
    ]
    pass_result = await db.quizSubmissions.aggregate(pass_pipeline).to_list(length=1)
    pass_stats = pass_result[0] if pass_result else {"passCount": 0, "total": 0}
    pass_rate = (pass_stats["passCount"] / pass_stats["total"] * 100) if pass_stats["total"] else 0.0

    # simple distribution: create buckets of size 10
    buckets_pipeline = [
        {"$match": {"quizId": q_oid, "status": "graded", "percentage": {"$ne": None}}},
        {"$bucket": {
            "groupBy": "$percentage",
            "boundaries": [0,10,20,30,40,50,60,70,80,90,100],
            "default": "100+",
            "output": {"count": {"$sum": 1}}
        }}
    ]
    bucket_results = await db.quizSubmissions.aggregate(buckets_pipeline).to_list(length=20)
    # convert bucket results to friendly dict
    distribution = {str(b["_id"]): b["count"] for b in bucket_results}

    return {
        "totalAttempts": basic_stats.get("totalAttempts", 0),
        "avgPercentage": basic_stats.get("avgPercentage"),
        "avgMarks": basic_stats.get("avgMarks"),
        "topScores": top_list,
        "passRate": pass_rate,
        "distribution": distribution
    }


# -------------------------
# STUDENT ANALYTICS (per student overall)
# returns: total quizzes taken, averagePercentage, lastAttempts (recent N), accuracy
# -------------------------
async def get_student_analytics(student_id: str, recent: int = 5):
    """
    - totalTaken: count of graded submissions
    - avgPercentage: average across graded submissions
    - lastAttempts: list of most recent 'recent' attempts with quizId, percentage, date
    - accuracy: same as avgPercentage for now (could be refined)
    """
    s_oid = ObjectId(student_id)

    # aggregated stats
    pipeline = [
        {"$match": {"studentId": s_oid, "status": "graded"}},
        {"$group": {
            "_id": "$studentId",
            "totalTaken": {"$sum": 1},
            "avgPercentage": {"$avg": "$percentage"}
        }}
    ]
    agg = await db.quizSubmissions.aggregate(pipeline).to_list(length=1)
    stats = agg[0] if agg else {"totalTaken": 0, "avgPercentage": None}

    # recent attempts
    recent_cursor = db.quizSubmissions.find(
        {"studentId": s_oid, "status": "graded"},
        {"quizId": 1, "percentage": 1, "submittedAt": 1}
    ).sort("submittedAt", -1).limit(recent)
    recent_attempts = []
    async for doc in recent_cursor:
        recent_attempts.append({
            "quizId": str(doc["quizId"]),
            "percentage": doc.get("percentage"),
            "submittedAt": doc.get("submittedAt")
        })

    return {
        "totalTaken": stats.get("totalTaken", 0),
        "avgPercentage": stats.get("avgPercentage"),
        "recentAttempts": recent_attempts,
    }


# -------------------------
# TEACHER DASHBOARD
# For a teacher: per-course and per-quiz aggregates (avg score, attempts, pass rate, pending)
# -------------------------
async def get_teacher_dashboard(teacher_id: str, course_id: Optional[str] = None):
    """
    Steps:
    - find quizzes authored by teacher (optionally filtered by course)
    - for those quizzes, aggregate submissions (avg, attempts, pass rate)
    - also count pending submissions for teacher to grade (if manual)
    """
    t_oid = ObjectId(teacher_id)

    # find quizzes by teacher
    quiz_query = {"teacherId": t_oid}
    if course_id:
        quiz_query["courseId"] = ObjectId(course_id)

    # fetch quiz ids
    quiz_cursor = db.quizzes.find(quiz_query, {"_id": 1, "quizNumber": 1, "courseId": 1})
    quiz_list = []
    quiz_ids = []
    async for q in quiz_cursor:
        quiz_ids.append(q["_id"])
        quiz_list.append({"quizId": str(q["_id"]), "quizNumber": q.get("quizNumber"), "courseId": str(q.get("courseId"))})

    if not quiz_ids:
        return {"quizzes": [], "pendingSubmissions": 0}

    # aggregate submissions by quiz
    agg_pipeline = [
        {"$match": {"quizId": {"$in": quiz_ids}, "status": "graded"}},
        {"$group": {
            "_id": "$quizId",
            "attempts": {"$sum": 1},
            "avgPercentage": {"$avg": "$percentage"},
            "avgMarks": {"$avg": "$obtainedMarks"},
            "passCount": {"$sum": {"$cond": [{"$gte": ["$percentage", 50]}, 1, 0]}}
        }}
    ]
    agg_results = await db.quizSubmissions.aggregate(agg_pipeline).to_list(length=len(quiz_ids))

    # map results by quizId string
    agg_map = {str(r["_id"]): r for r in agg_results}

    # pending submissions count (status != graded)
    pending_count = await db.quizSubmissions.count_documents({"quizId": {"$in": quiz_ids}, "status": {"$ne": "graded"}})

    # build final per-quiz entries
    quizzes_summary = []
    for q in quiz_list:
        stats = agg_map.get(q["quizId"])
        total_attempts = stats["attempts"] if stats else 0
        avg_percentage = stats["avgPercentage"] if stats else None
        pass_count = stats["passCount"] if stats else 0
        pass_rate = (pass_count / total_attempts * 100) if total_attempts else 0.0

        quizzes_summary.append({
            "quizId": q["quizId"],
            "quizNumber": q.get("quizNumber"),
            "courseId": q.get("courseId"),
            "attempts": total_attempts,
            "avgPercentage": avg_percentage,
            "passRate": pass_rate
        })

    return {
        "quizzes": quizzes_summary,
        "pendingSubmissions": pending_count
    }

async def get_by_quiz(quiz_id, sort=None):
    """ Fetch submissions for a specific quiz """

    # Build query filter
    query = {"quizId": ObjectId(quiz_id)}

    # Get cursor from MongoDB
    cursor = db.quizSubmissions.find(query)

    # Apply sorting if provided (?sort=submittedAt or ?sort=-submittedAt)
    if sort:
        cursor = cursor.sort(sort)

    # Convert each Mongo document into serialized form
    return [serialize_submission(s) async for s in cursor]


async def get_by_student(student_id, sort=None):
    """ Fetch submissions for a specific student """

    query = {"studentId": ObjectId(student_id)}
    cursor = db.quizSubmissions.find(query)

    if sort:
        cursor = cursor.sort(sort)

    return [serialize_submission(s) async for s in cursor]


async def delete_submission(_id):
    """ Delete a submission by ID """

    result = await db.quizSubmissions.delete_one({"_id": ObjectId(_id)})

    # Return True only if 1 document was deleted
    return result.deleted_count > 0