from typing import Optional
from fastapi import APIRouter, HTTPException, status, Query
from bson import ObjectId
from app.schemas.quiz_submissions import QuizSubmissionCreate, QuizSubmissionResponse
from app.crud.quiz_submissions import submit_and_grade_submission, get_by_quiz, get_by_student, delete_submission, get_quiz_summary, get_student_analytics, get_teacher_dashboard

router = APIRouter(
    prefix="/quiz-submissions",
    tags=["Quiz Submissions"]
)

# Validate any ObjectId received from user input
def validate(_id: str):
    if not ObjectId.is_valid(_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid ObjectId"
        )


# ---------- Submit & Auto-Grade (student) ----------
@router.post("/", response_model=QuizSubmissionResponse, summary="Submit answers and auto-grade")
async def submit_and_grade_route(data: QuizSubmissionCreate):

    # Validate all IDs before DB operations
    validate(data.studentId)
    validate(data.quizId)
    validate(data.courseId)
    validate(data.tenantId)

    # Call CRUD layer to insert
    result = await submit_and_grade_submission(data)

    # If duplicate submission was detected
    if result == "AlreadySubmitted":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Student already submitted this quiz."
        )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process submission."
        )

    return result
# --------------------------------------------------------


# ------------------ GET SUBMISSIONS BY QUIZ ------------------
@router.get("/quiz/{quiz_id}", response_model=list[QuizSubmissionResponse], summary="Get quiz submissions")
async def get_quiz_submissions(
        quiz_id: str,
        sort: Optional[str] = Query(None, description="Sort field: submittedAt or -submittedAt, prefix '-' for desc")
):
    validate(quiz_id)

    # Convert sort string into MongoDB sorting tuple
    sort_option = None
    if sort:
        # convert to tuple accepted by pymongo sort: (field, direction)
        # Example:
        # "submittedAt" -> ("submittedAt", 1)
        # "-submittedAt" -> ("submittedAt", -1)
        sort_option = (sort.lstrip("-"), -1 if sort.startswith("-") else 1)

    return await get_by_quiz(quiz_id, sort_option)
# ---------------------------------------------------------------


# ------------------ GET SUBMISSIONS BY STUDENT ------------------
@router.get("/student/{student_id}", response_model=list[QuizSubmissionResponse], summary="Get student's submissions")
async def get_student_submissions(
        student_id: str,
        sort: Optional[str] = Query(None)
):
    validate(student_id)

    sort_option = None
    if sort:
        sort_option = (sort.lstrip("-"), -1 if sort.startswith("-") else 1)

    return await get_by_student(student_id, sort_option)
# ----------------------------------------------------------------


# ------------------ DELETE SUBMISSION ------------------
@router.delete("/{_id}", summary="Delete a submission")
async def delete_quiz(_id: str):

    validate(_id)

    # Try deleting record
    deleted = await delete_submission(_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found"
        )

    return {"message": "Submission deleted successfully"}
# --------------------------------------------------------


# ---------- Quiz Results Summary (teacher/dashboard) ----------
@router.get("/summary/quiz/{quiz_id}", summary="Get aggregated quiz summary")
async def quiz_summary(quiz_id: str, top_n: int = Query(5, ge=1, le=50)):
    validate(quiz_id)
    return await get_quiz_summary(quiz_id, top_n=top_n)


# ---------- Student Analytics ----------
@router.get("/analytics/student/{student_id}", summary="Get student analytics")
async def student_analytics(student_id: str, recent: int = Query(5, ge=1, le=50)):
    validate(student_id)
    return await get_student_analytics(student_id, recent=recent)


# ---------- Teacher Dashboard ----------
@router.get("/dashboard/teacher/{teacher_id}", summary="Get teacher dashboard")
async def teacher_dashboard(teacher_id: str, course_id: Optional[str] = None):
    validate(teacher_id)
    if course_id:
        validate(course_id)
    return await get_teacher_dashboard(teacher_id, course_id)
