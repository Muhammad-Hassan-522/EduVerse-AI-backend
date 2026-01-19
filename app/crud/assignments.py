# from fastapi import HTTPException
# from app.db.database import db
# from datetime import datetime
# from bson import ObjectId
# from bson.errors import InvalidId


# def serialize_assignment(a: dict) -> dict:

#     def fix_date(value):
#         if not value:
#             return None
#         if isinstance(value, datetime):
#             return value
#         if hasattr(value, "as_datetime"):
#             return value.as_datetime()
#         try:
#             return datetime.fromisoformat(value)
#         except Exception:
#             return value

#     return {
#         "id": str(a["_id"]),
#         "courseId": str(a["courseId"]),
#         "teacherId": str(a["teacherId"]),
#         "tenantId": str(a["tenantId"]),
#         "title": a["title"],
#         "description": a.get("description"),
#         "dueDate": fix_date(a.get("dueDate")),
#         "dueTime": fix_date(a.get("dueTime")),
#         "uploadedAt": fix_date(a.get("uploadedAt")),
#         "updatedAt": fix_date(a.get("updatedAt")),
#         "totalMarks": a.get("totalMarks"),
#         "passingMarks": a.get("passingMarks"),
#         "status": a.get("status"),
#         "fileUrl": a.get("fileUrl"),
#         "allowedFormats": a.get("allowedFormats", []),
#     }


# def to_oid(id_str: str, field: str) -> ObjectId:
#     """Validate and convert string to Mongo ObjectId."""
#     try:
#         return ObjectId(id_str)
#     except InvalidId:
#         raise HTTPException(400, f"Invalid {field}")


# # async def create_assignment(data) -> dict:
# #     d = data.dict()
# #     d.update({
# #         "courseId": to_oid(d["courseId"], "courseId"),
# #         "teacherId": to_oid(d["teacherId"], "teacherId"),
# #         "tenantId": to_oid(d["tenantId"], "tenantId"),
# #         "uploadedAt": datetime.utcnow(),
# #         "updatedAt": datetime.utcnow()
# #     })

# #     result = await db.assignments.insert_one(d)
# #     new_assignment = await db.assignments.find_one({"_id": result.inserted_id})
# #     return serialize_assignment(new_assignment)


# async def create_assignment(data, teacher_id: str, tenant_id: str):
#     assignment = {
#         "courseId": to_oid(data.courseId),
#         "teacherId": to_oid(teacher_id),
#         "tenantId": to_oid(tenant_id),
#         "title": data.title,
#         "description": data.description,
#         "dueDate": data.dueDate,
#         "dueTime": data.dueTime,
#         "totalMarks": data.totalMarks,
#         "passingMarks": data.passingMarks,
#         "status": data.status,
#         "fileUrl": data.fileUrl,
#         "allowedFormats": data.allowedFormats,
#         "uploadedAt": datetime.utcnow(),
#         "updatedAt": datetime.utcnow(),
#     }

#     result = await db.assignments.insert_one(assignment)
#     doc = await db.assignments.find_one({"_id": result.inserted_id})
#     return serialize_assignment(doc)


# async def get_all_assignments(
#     search: str = None,
#     tenant_id: str = None,
#     teacher_id: str = None,
#     course_id: str = None,
#     status: str = None,
#     from_date: datetime = None,
#     to_date: datetime = None,
#     sort_by: str = "uploadedAt",
#     order: int = -1,
#     page: int = 1,
#     limit: int = 10,
# ):
#     query = {}

#     # Search filter
#     if search:
#         query["$or"] = [
#             {"title": {"$regex": search, "$options": "i"}},
#             {"description": {"$regex": search, "$options": "i"}},
#             {"status": {"$regex": search, "$options": "i"}},
#         ]

#     # Standard filters
#     if tenant_id:
#         query["tenantId"] = to_oid(tenant_id, "tenantId")
#     if teacher_id:
#         query["teacherId"] = to_oid(teacher_id, "teacherId")
#     if course_id:
#         query["courseId"] = to_oid(course_id, "courseId")
#     if status:
#         query["status"] = status

#     # Date range
#     if from_date or to_date:
#         query["uploadedAt"] = {}
#         if from_date:
#             query["uploadedAt"]["$gte"] = from_date
#         if to_date:
#             query["uploadedAt"]["$lte"] = to_date

#     # Pagination
#     skip = (page - 1) * limit
#     cursor = db.assignments.find(query).sort(sort_by, order).skip(skip).limit(limit)

#     results = [serialize_assignment(a) async for a in cursor]
#     total = await db.assignments.count_documents(query)

#     return {
#         "page": page,
#         "limit": limit,
#         "total": total,
#         "totalPages": (total + limit - 1) // limit,
#         "results": results,
#     }


# # async def get_assignment(id: str):
# #     assignment = await db.assignments.find_one({"_id": to_oid(id, "assignmentId")})
# #     return serialize_assignment(assignment) if assignment else None


# async def get_assignment(id: str, tenant_id: str):
#     query = {
#         "_id": to_oid(id, "assignmentId"),
#         "tenantId": to_oid(tenant_id, "tenantId"),
#     }
#     assignment = await db.assignments.find_one(query)
#     return serialize_assignment(assignment) if assignment else None


# # async def get_all_assignments_by_tenant(tenant_id: str):
# #     tenant_oid = to_oid(tenant_id, "tenantId")
# #     cursor = db.assignments.find({"tenantId": tenant_oid})
# #     return [serialize_assignment(a) async for a in cursor]


# # async def get_assignments_by_teacher(teacher_id: str):
# #     teacher_oid = to_oid(teacher_id, "teacherId")
# #     cursor = db.assignments.find({
# #         "$or": [
# #             {"teacherId": teacher_oid},
# #             {"teacherId": teacher_id}
# #         ]
# #     })
# #     return [serialize_assignment(a) async for a in cursor]


# # async def get_assignments_by_course(course_id: str):
# #     course_oid = to_oid(course_id, "courseId")
# #     cursor = db.assignments.find({"courseId": course_oid})
# #     return [serialize_assignment(a) async for a in cursor]
# async def update_assignment(id: str, teacher_id: str, tenant_id: str, updates: dict):
#     assignment = await db.assignments.find_one(
#         {"_id": to_oid(id, "assignmentId"), "tenantId": to_oid(tenant_id, "tenantId")}
#     )
#     if not assignment:
#         return None
#     if str(assignment["teacherId"]) != teacher_id:
#         return "UNAUTHORIZED"
#     updates_to_set = {k: v for k, v in updates.items() if v is not None}
#     updates_to_set["updatedAt"] = datetime.utcnow()
#     await db.assignments.update_one({"_id": ObjectId(id)}, {"$set": updates_to_set})
#     updated_assignment = await db.assignments.find_one({"_id": ObjectId(id)})
#     return serialize_assignment(updated_assignment)


# async def delete_assignment(id: str, teacher_id: str, tenant_id: str):
#     assignment = await db.assignments.find_one(
#         {"_id": to_oid(id, "assignmentId"), "tenantId": to_oid(tenant_id, "tenantId")}
#     )
#     if not assignment:
#         return None
#     if str(assignment["teacherId"]) != teacher_id:
#         return "UNAUTHORIZED"
#     await db.assignments.delete_one({"_id": ObjectId(id)})
#     return True


from datetime import datetime
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException
from app.db.database import db


# ---------------------------
# UTILITY FUNCTIONS
# ---------------------------
def to_oid(id_str: str, field: str = "id") -> ObjectId:
    """Convert string to ObjectId and validate."""
    try:
        return ObjectId(id_str)
    except (InvalidId, TypeError):
        raise HTTPException(status_code=400, detail=f"Invalid {field}")


def serialize_assignment(a: dict) -> dict:
    """Serialize assignment document for API response."""

    def fix_date(value):
        if not value:
            return None
        if isinstance(value, datetime):
            return value
        if hasattr(value, "as_datetime"):
            return value.as_datetime()
        try:
            return datetime.fromisoformat(value)
        except Exception:
            return value

    return {
        "id": str(a["_id"]),
        "courseId": str(a["courseId"]),
        "teacherId": str(a["teacherId"]),
        "tenantId": str(a["tenantId"]),
        "title": a["title"],
        "description": a.get("description"),
        "dueDate": fix_date(a.get("dueDate")),
        "dueTime": fix_date(a.get("dueTime")),
        "uploadedAt": fix_date(a.get("uploadedAt")),
        "updatedAt": fix_date(a.get("updatedAt")),
        "totalMarks": a.get("totalMarks"),
        "passingMarks": a.get("passingMarks"),
        "status": a.get("status"),
        "fileUrl": a.get("fileUrl"),
        "allowedFormats": a.get("allowedFormats", []),
    }


# ---------------------------
# CREATE ASSIGNMENT
# ---------------------------
async def create_assignment(data, teacher_id: str, tenant_id: str) -> dict:
    # Validate required IDs
    course_oid = to_oid(data.courseId, "courseId")
    teacher_oid = to_oid(teacher_id, "teacherId")
    tenant_oid = to_oid(tenant_id, "tenantId")

    assignment = {
        "courseId": course_oid,
        "teacherId": teacher_oid,
        "tenantId": tenant_oid,
        "title": data.title,
        "description": data.description,
        "dueDate": data.dueDate,
        "dueTime": data.dueTime,
        "totalMarks": data.totalMarks,
        "passingMarks": data.passingMarks,
        "status": data.status or "active",
        "fileUrl": data.fileUrl,
        "allowedFormats": data.allowedFormats or [],
        "uploadedAt": datetime.utcnow(),
        "updatedAt": datetime.utcnow(),
    }

    result = await db.assignments.insert_one(assignment)
    doc = await db.assignments.find_one({"_id": result.inserted_id})
    return serialize_assignment(doc)


# ---------------------------
# GET ALL ASSIGNMENTS
# ---------------------------
async def get_all_assignments(
    search: str = None,
    tenant_id: str = None,
    teacher_id: str = None,
    course_id: str = None,
    status: str = None,
    from_date: datetime = None,
    to_date: datetime = None,
    sort_by: str = "uploadedAt",
    order: int = -1,
    page: int = 1,
    limit: int = 10,
) -> dict:
    query = {}

    # Search filter
    if search:
        query["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}},
            {"status": {"$regex": search, "$options": "i"}},
        ]

    # Tenant, teacher, course, status filters
    if tenant_id:
        query["tenantId"] = to_oid(tenant_id, "tenantId")
    if teacher_id:
        query["teacherId"] = to_oid(teacher_id, "teacherId")
    if course_id:
        query["courseId"] = to_oid(course_id, "courseId")
    if status:
        query["status"] = status

    # Date range
    if from_date or to_date:
        query["uploadedAt"] = {}
        if from_date:
            query["uploadedAt"]["$gte"] = from_date
        if to_date:
            query["uploadedAt"]["$lte"] = to_date

    # Pagination
    skip = max(page - 1, 0) * limit
    cursor = db.assignments.find(query).sort(sort_by, order).skip(skip).limit(limit)
    results = [serialize_assignment(a) async for a in cursor]
    total = await db.assignments.count_documents(query)

    return {
        "page": page,
        "limit": limit,
        "total": total,
        "totalPages": (total + limit - 1) // limit,
        "results": results,
    }


# ---------------------------
# GET SINGLE ASSIGNMENT
# ---------------------------
async def get_assignment(id: str, tenant_id: str) -> dict | None:
    query = {
        "_id": to_oid(id, "assignmentId"),
        "tenantId": to_oid(tenant_id, "tenantId"),
    }
    assignment = await db.assignments.find_one(query)
    return serialize_assignment(assignment) if assignment else None


# ---------------------------
# UPDATE ASSIGNMENT
# ---------------------------
async def update_assignment(
    assignment_id: str, teacher_id: str, tenant_id: str, updates: dict
):
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")

    # Ensure IDs
    assignment = await db.assignments.find_one(
        {
            "_id": to_oid(assignment_id, "assignmentId"),
            "tenantId": to_oid(tenant_id, "tenantId"),
        }
    )
    if not assignment:
        return None

    if str(assignment["teacherId"]) != teacher_id:
        return "UNAUTHORIZED"

    updates_to_set = {k: v for k, v in updates.items() if v is not None}
    updates_to_set["updatedAt"] = datetime.utcnow()

    await db.assignments.update_one(
        {"_id": to_oid(assignment_id, "assignmentId")}, {"$set": updates_to_set}
    )
    updated_assignment = await db.assignments.find_one(
        {"_id": to_oid(assignment_id, "assignmentId")}
    )
    return serialize_assignment(updated_assignment)


# ---------------------------
# DELETE ASSIGNMENT
# ---------------------------
async def delete_assignment(assignment_id: str, teacher_id: str, tenant_id: str):
    assignment = await db.assignments.find_one(
        {
            "_id": to_oid(assignment_id, "assignmentId"),
            "tenantId": to_oid(tenant_id, "tenantId"),
        }
    )
    if not assignment:
        return None
    if str(assignment["teacherId"]) != teacher_id:
        return "UNAUTHORIZED"

    await db.assignments.delete_one({"_id": to_oid(assignment_id, "assignmentId")})
    return True
