# from app.db.database import db
# from datetime import datetime
# from bson import ObjectId
# from typing import List, Optional


# def serialize_submission(sub):
#     return {
#         "id": str(sub["_id"]),
#         "studentId": str(sub["studentId"]),
#         "assignmentId": str(sub["assignmentId"]),
#         "submittedAt": sub["submittedAt"],
#         "fileUrl": sub["fileUrl"],
#         "obtainedMarks": sub.get("obtainedMarks"),
#         "feedback": sub.get("feedback"),
#         "courseId": str(sub["courseId"]),
#         "tenantId": str(sub["tenantId"]),
#         "gradedAt": sub.get("gradedAt"),
#     }


# async def create_submission(data, student_id: str, tenant_id: str):
#     submission = {
#         "studentId": ObjectId(student_id),
#         "assignmentId": ObjectId(data.assignmentId),
#         "courseId": ObjectId(data.courseId),
#         "tenantId": ObjectId(tenant_id),
#         "fileUrl": data.fileUrl,
#         "submittedAt": datetime.utcnow(),
#         "obtainedMarks": None,
#         "feedback": None,
#         "gradedAt": None,
#     }

#     result = await db.assignmentSubmissions.insert_one(submission)
#     doc = await db.assignmentSubmissions.find_one({"_id": result.inserted_id})
#     return serialize_submission(doc)


# async def get_all_submissions(tenant_id: str) -> List[dict]:
#     cursor = db.assignmentSubmissions.find({"tenantId": ObjectId(tenant_id)}).sort(
#         "submittedAt", -1
#     )
#     return [serialize_submission(s) async for s in cursor]


# async def get_submissions_by_student(student_id: str, tenant_id: str):
#     cursor = db.assignmentSubmissions.find(
#         {
#             "studentId": ObjectId(student_id),
#             "tenantId": ObjectId(tenant_id),
#         }
#     )
#     return [serialize_submission(s) async for s in cursor]


# async def get_submissions_by_assignment(assignment_id: str, tenant_id: str):
#     cursor = db.assignmentSubmissions.find(
#         {
#             "assignmentId": ObjectId(assignment_id),
#             "tenantId": ObjectId(tenant_id),
#         }
#     )
#     return [serialize_submission(s) async for s in cursor]


# async def grade_submission(
#     submission_id: str,
#     tenant_id: str,
#     marks: Optional[int],
#     feedback: Optional[str],
# ):
#     updates = {"gradedAt": datetime.utcnow()}
#     if marks is not None:
#         updates["obtainedMarks"] = marks
#     if feedback is not None:
#         updates["feedback"] = feedback

#     await db.assignmentSubmissions.update_one(
#         {
#             "_id": ObjectId(submission_id),
#             "tenantId": ObjectId(tenant_id),
#         },
#         {"$set": updates},
#     )

#     doc = await db.assignmentSubmissions.find_one(
#         {
#             "_id": ObjectId(submission_id),
#             "tenantId": ObjectId(tenant_id),
#         }
#     )
#     return serialize_submission(doc)


# async def delete_submission(submission_id: str, tenant_id: str):
#     result = await db.assignmentSubmissions.delete_one(
#         {
#             "_id": ObjectId(submission_id),
#             "tenantId": ObjectId(tenant_id),
#         }
#     )
#     return result.deleted_count > 0


from app.db.database import db
from datetime import datetime
from bson import ObjectId
from bson.errors import InvalidId
from typing import List, Optional
from fastapi import HTTPException


# ---------------------------
# UTILITY FUNCTIONS
# ---------------------------
def to_oid(id_str: str, field: str = "id") -> ObjectId:
    """Convert string to ObjectId and validate."""
    try:
        return ObjectId(id_str)
    except (InvalidId, TypeError):
        raise HTTPException(status_code=400, detail=f"Invalid {field}")


def serialize_submission(sub: dict) -> dict:
    """Serialize a submission document for API response."""

    def fix_date(value):
        if not value:
            return None
        if isinstance(value, datetime):
            return value
        try:
            return datetime.fromisoformat(value)
        except Exception:
            return value

    return {
        "id": str(sub["_id"]),
        "studentId": str(sub["studentId"]),
        "assignmentId": str(sub["assignmentId"]),
        "courseId": str(sub["courseId"]),
        "tenantId": str(sub["tenantId"]),
        "fileUrl": sub.get("fileUrl"),
        "submittedAt": fix_date(sub.get("submittedAt")),
        "obtainedMarks": sub.get("obtainedMarks"),
        "feedback": sub.get("feedback"),
        "gradedAt": fix_date(sub.get("gradedAt")),
    }


def clean_updates(data: dict) -> dict:
    """Remove empty strings or null-like values from updates."""
    return {k: v for k, v in data.items() if v not in [None, "", [], {}]}


# ---------------------------
# CREATE SUBMISSION
# ---------------------------
async def create_submission(data, student_id: str, tenant_id: str) -> dict:
    # Validate required IDs
    if not data.assignmentId or not data.courseId or not data.fileUrl:
        raise HTTPException(
            status_code=400, detail="assignmentId, courseId, and fileUrl are required"
        )

    submission = {
        "studentId": to_oid(student_id, "studentId"),
        "assignmentId": to_oid(data.assignmentId, "assignmentId"),
        "courseId": to_oid(data.courseId, "courseId"),
        "tenantId": to_oid(tenant_id, "tenantId"),
        "fileUrl": data.fileUrl,
        "submittedAt": datetime.utcnow(),
        "obtainedMarks": None,
        "feedback": None,
        "gradedAt": None,
    }

    result = await db.assignmentSubmissions.insert_one(submission)
    doc = await db.assignmentSubmissions.find_one({"_id": result.inserted_id})
    if not doc:
        raise HTTPException(status_code=500, detail="Failed to create submission")
    return serialize_submission(doc)


# ---------------------------
# GET ALL SUBMISSIONS (Admin / Teacher)
# ---------------------------
async def get_all_submissions(tenant_id: str) -> List[dict]:
    cursor = db.assignmentSubmissions.find(
        {"tenantId": to_oid(tenant_id, "tenantId")}
    ).sort("submittedAt", -1)
    return [serialize_submission(s) async for s in cursor]


# ---------------------------
# GET SUBMISSIONS BY STUDENT
# ---------------------------
async def get_submissions_by_student(student_id: str, tenant_id: str) -> List[dict]:
    cursor = db.assignmentSubmissions.find(
        {
            "studentId": to_oid(student_id, "studentId"),
            "tenantId": to_oid(tenant_id, "tenantId"),
        }
    ).sort("submittedAt", -1)
    return [serialize_submission(s) async for s in cursor]


# ---------------------------
# GET SUBMISSIONS BY ASSIGNMENT
# ---------------------------
async def get_submissions_by_assignment(
    assignment_id: str, tenant_id: str
) -> List[dict]:
    cursor = db.assignmentSubmissions.find(
        {
            "assignmentId": to_oid(assignment_id, "assignmentId"),
            "tenantId": to_oid(tenant_id, "tenantId"),
        }
    ).sort("submittedAt", -1)
    return [serialize_submission(s) async for s in cursor]


# ---------------------------
# GRADE SUBMISSION
# ---------------------------
async def grade_submission(
    submission_id: str,
    tenant_id: str,
    marks: Optional[int] = None,
    feedback: Optional[str] = None,
) -> dict:
    if marks is None and feedback is None:
        raise HTTPException(status_code=400, detail="Nothing to update")

    updates = {"gradedAt": datetime.utcnow()}
    if marks is not None:
        updates["obtainedMarks"] = marks
    if feedback is not None:
        updates["feedback"] = feedback

    result = await db.assignmentSubmissions.update_one(
        {
            "_id": to_oid(submission_id, "submissionId"),
            "tenantId": to_oid(tenant_id, "tenantId"),
        },
        {"$set": updates},
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Submission not found")

    doc = await db.assignmentSubmissions.find_one(
        {
            "_id": to_oid(submission_id, "submissionId"),
            "tenantId": to_oid(tenant_id, "tenantId"),
        }
    )
    return serialize_submission(doc)


# ---------------------------
# DELETE SUBMISSION (Admin Only)
# ---------------------------
async def delete_submission(submission_id: str, tenant_id: str) -> bool:
    result = await db.assignmentSubmissions.delete_one(
        {
            "_id": to_oid(submission_id, "submissionId"),
            "tenantId": to_oid(tenant_id, "tenantId"),
        }
    )
    return result.deleted_count > 0
