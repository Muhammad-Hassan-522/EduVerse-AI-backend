from fastapi import APIRouter, HTTPException
from typing import List
from bson import ObjectId
from app.schemas.assignmentSubmissions import AssignmentSubmissionCreate, AssignmentSubmissionResponse
from app.crud.assignment_submissions import (
    create_submission,
    get_all_submissions,
    get_submissions_by_student,
    get_submissions_by_assignment,
    grade_submission,
    delete_submission
)

router = APIRouter(
    prefix="/assignment-submissions",
    tags=["Assignment Submissions"]
)

# Utility to validate ObjectId
def validate_object_id(id: str):
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid ObjectId format")

@router.post("/", response_model=AssignmentSubmissionResponse)
async def create_submission_route(data: AssignmentSubmissionCreate):
    # Validate IDs coming from client
    validate_object_id(data.studentId)
    validate_object_id(data.assignmentId)
    validate_object_id(data.courseId)
    validate_object_id(data.tenantId)

    submission = await create_submission(data)

    if not submission:
        raise HTTPException(status_code=500, detail="Failed to create submission")

    return submission


@router.get("/", response_model=List[AssignmentSubmissionResponse])
async def get_all_submissions_route():
    submissions = await get_all_submissions()
    return submissions


@router.get("/student/{student_id}", response_model=List[AssignmentSubmissionResponse])
async def get_by_student(student_id: str):
    validate_object_id(student_id)

    submissions = await get_submissions_by_student(student_id)

    if submissions is None:
        raise HTTPException(status_code=404, detail="No submissions found for this student")

    return submissions


@router.get("/assignment/{assignment_id}", response_model=List[AssignmentSubmissionResponse])
async def get_by_assignment(assignment_id: str):
    validate_object_id(assignment_id)

    submissions = await get_submissions_by_assignment(assignment_id)

    if submissions is None:
        raise HTTPException(status_code=404, detail="No submissions found for this assignment")

    return submissions


@router.put("/{submission_id}", response_model=AssignmentSubmissionResponse)
async def grade_submission_route(submission_id: str, marks: int = None, feedback: str = None):
    validate_object_id(submission_id)

    graded = await grade_submission(submission_id, marks, feedback)
    if not graded:
        raise HTTPException(status_code=404, detail="Submission not found")

    return graded


@router.delete("/{submission_id}")
async def delete_submission_route(submission_id: str):
    validate_object_id(submission_id)

    success = await delete_submission(submission_id)
    if not success:
        raise HTTPException(status_code=404, detail="Submission not found")

    return {"message": "Submission deleted successfully"}
