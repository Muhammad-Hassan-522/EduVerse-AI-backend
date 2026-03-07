from typing import Optional, Any

from bson import ObjectId
from datetime import datetime

from fastapi import HTTPException, status
from app.db.database import db

def _ensure_objectid(_id: str, name: str = "id"):
    if not ObjectId.is_valid(_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid ObjectId for {name}"
        )
    return ObjectId(_id)

def serialize_quiz(quiz: dict) -> dict:
    """
    Convert MongoDB quiz document into a JSON serializable dictionary.
    - Converts ObjectId fields to strings.
    - Ensures default values exist (status, aiGenerated).
    """
    return {
        "id": str(quiz["_id"]),
        "courseId": str(quiz["courseId"]),
        "courseName": str(quiz["courseName"]),
        "teacherId": str(quiz["teacherId"]),
        "tenantId": str(quiz["tenantId"]),
        "quizNumber": quiz["quizNumber"],
        "description": quiz.get("description"),
        "dueDate": quiz["dueDate"],    # Already a datetime object
        "questions": quiz["questions"], # Stored as list of dicts
        "timeLimitMinutes": quiz.get("timeLimitMinutes"),
        "totalMarks": quiz["totalMarks"],
        "aiGenerated": quiz.get("aiGenerated", False),
        "status": quiz.get("status", "active"),
        "createdAt": quiz["createdAt"],
        "updatedAt": quiz.get("updatedAt"),
    }


async def create_quiz(request):
    """Insert a new quiz into MongoDB."""

    # Convert Pydantic model → Python dict
    data = request.dict()

    # Convert IDs
    data["courseId"] = _ensure_objectid(data["courseId"], "courseId")
    data["teacherId"] = _ensure_objectid(data["teacherId"], "teacherId")
    data["tenantId"] = _ensure_objectid(data["tenantId"], "tenantId")
    
    # Convert string IDs to ObjectId & add metadata
    data.update({
        "status": "active",
        "createdAt": datetime.utcnow(),
        "updatedAt": None,
        # "courseId": ObjectId(data["courseId"]),
        # "teacherId": ObjectId(data["teacherId"]),
        # "tenantId": ObjectId(data["tenantId"]),
        "isDeleted": False,
        "deletedAt": None
    })

    # Insert into MongoDB
    res = await db.quizzes.insert_one(data)

    # Fetch inserted document
    new_quiz = await db.quizzes.find_one({"_id": res.inserted_id})

    return serialize_quiz(new_quiz)


async def get_quiz(_id: str):
    """Fetch a single quiz using its ObjectId."""

    _id = _ensure_objectid(_id, "quizId")

    quiz = await db.quizzes.find_one({"_id": _id, "isDeleted": False})
    return serialize_quiz(quiz) if quiz else None


async def get_quizzes_filtered(
    tenantId: Optional[str] = None,
    teacherId: Optional[str] = None,
    courseId: Optional[str] = None,
    search: Optional[str] = None,
    sort: Optional[str] = "createdAt",
    page: int = 1,
    limit: int = 10
):
    """
    Fetch quizzes with:
    - Filtering by tenant / teacher / course
    - Text search on description
    - Sorting (ASC / DESC)
    - Pagination
    """

    query: dict[str, Any] = {"isDeleted": False}

    # Add filtering conditions if provided
    if tenantId:
        query["tenantId"] = ObjectId(tenantId)

    if teacherId:
        query["teacherId"] = ObjectId(teacherId)

    if courseId:
        query["courseId"] = ObjectId(courseId)

    # Enables text search in description field
    if search:
        query["description"] = {"$regex": search, "$options": "i"}

    # Determine sorting direction
    sort_dir = -1 if sort.startswith("-") else 1
    sort_field = sort.lstrip("-")

    # Apply filtering, sorting, pagination
    cursor = (
        db.quizzes.find(query)
        .sort(sort_field, sort_dir)
        .skip((page - 1) * limit)
        .limit(limit)
    )

    # Convert to list of serialized quizzes
    return [serialize_quiz(q) async for q in cursor]

async def update_quiz(_id: str, teacherId: str, updates: dict):
    """
    Update a quiz only if the teacher is the owner.
    
    IMPORTANT: If students have already submitted answers for this quiz,
    question modifications (questions, totalMarks) are NOT allowed to prevent
    score inconsistencies (e.g., student scored 2/3 but teacher removes a question).
    Only metadata updates (description, dueDate, status, timeLimitMinutes) are permitted.
    """

    _ensure_objectid(_id, "quizId")
    teacherId = str(teacherId)

    quiz = await db.quizzes.find_one({"_id": ObjectId(_id), "isDeleted": False})
    if not quiz:
        return None

    # Permission check
    if str(quiz["teacherId"]) != teacherId:
        return "Unauthorized"

    # Check if any student submissions exist for this quiz
    submission_count = await db.quizSubmissions.count_documents({"quizId": ObjectId(_id)})
    has_submissions = submission_count > 0

    # filter only meaningful values
    safe_updates = {}
    # Fields that can ALWAYS be updated (metadata only)
    allowed_always = {"description", "dueDate", "status", "timeLimitMinutes", "aiGenerated"}
    # Fields that can ONLY be updated if NO submissions exist
    restricted_fields = {"questions", "totalMarks", "quizNumber"}

    for k, val in updates.items():
        if val is None:
            continue
        if val == "":
            continue
        
        # If submissions exist, block restricted field updates
        if has_submissions and k in restricted_fields:
            continue  # Skip this update silently, or you could raise an error
        
        safe_updates[k] = val

    # Update timestamp
    safe_updates["updatedAt"] = datetime.utcnow()

    # apply only safe values
    await db.quizzes.update_one({"_id": ObjectId(_id)}, {"$set": safe_updates})

    # Fetch updated quiz
    updated_quiz = await db.quizzes.find_one({"_id": ObjectId(_id)})

    return serialize_quiz(updated_quiz)


async def delete_quiz(_id, teacherId):
    """ Delete quiz only if teacher owns it. """

    quiz = await db.quizzes.find_one({"_id": ObjectId(_id), "isDeleted": False})

    if not quiz:
        return None

    # Permission check
    if str(quiz["teacherId"]) != str(teacherId):
        return "Unauthorized"

    # Soft delete
    await db.quizzes.update_one(
        {"_id": ObjectId(_id)},
        {
            "$set": {
                "isDeleted": True,
                "deletedAt": datetime.utcnow(),
                "updatedAt": datetime.utcnow()
            }
        }
    )


    return True


async def has_quiz_submissions(quiz_id: str) -> bool:
    """
    Check if a quiz has any student submissions.
    Returns True if at least one submission exists.
    """
    _ensure_objectid(quiz_id, "quizId")
    count = await db.quizSubmissions.count_documents({"quizId": ObjectId(quiz_id)})
    return count > 0


async def get_student_quizzes(user_id: str, tenant_id: str):
    """
    Fetch quizzes for courses the student is enrolled in.
    """
    # 1. Find Student Profile by User ID
    # We need to access the students collection directly or import logic
    # To avoid circular imports, simpler to just access db.students
    user_oid = _ensure_objectid(user_id, "userId")
    tenant_oid = _ensure_objectid(tenant_id, "tenantId")

    student = await db.students.find_one({"userId": user_oid, "tenantId": tenant_oid})
    if not student:
        return [] # Or raise error

    enrolled_courses = student.get("enrolledCourses", [])
    # Ensure they are ObjectIds
    course_ids = [ObjectId(c) for c in enrolled_courses if ObjectId.is_valid(c)]

    if not course_ids:
        return []

    # 2. Query Quizzes in those courses
    cursor = db.quizzes.find({
        "courseId": {"$in": course_ids},
        "tenantId": tenant_oid,
        "isDeleted": False,
        "status": "active" # Students should only see active quizzes? Usually yes.
    }).sort("createdAt", -1)

    return [serialize_quiz(q) async for q in cursor]
