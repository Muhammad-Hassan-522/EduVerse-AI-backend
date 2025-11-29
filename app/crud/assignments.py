from app.db.database import db
from datetime import datetime
from bson import ObjectId

def serialize_assignment(a):
    def fix_date(value):
        if isinstance(value, datetime):
            return value
        if hasattr(value, "as_datetime"):  # MongoDB Timestamp
            return value.as_datetime()
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
        "allowedFormats": a.get("allowedFormats", [])
    }


async def create_assignment(data):
    d = data.dict()
    d.update({
       
        "courseId": ObjectId(d["courseId"]),
        "teacherId": ObjectId(d["teacherId"]),
        "tenantId": ObjectId(d["tenantId"]),
        "uploadedAt": datetime.utcnow(),
        "updatedAt": datetime.utcnow()
    })

    result = await db.assignments.insert_one(d)
    new_assignment = await db.assignments.find_one({"_id": result.inserted_id})
    return serialize_assignment(new_assignment)


async def get_all_assignments():
    cursor = db.assignments.find().sort("uploadedAt", -1)
    return [serialize_assignment(a) async for a in cursor]


async def get_all_assignments_by_tenant(tenant_id: str):
    tenant_oid = ObjectId(tenant_id)
    cursor = db.assignments.find({"tenantId": tenant_oid})
    return [serialize_assignment(a) async for a in cursor]


async def get_assignment(id: str):
    assignment = await db.assignments.find_one({"_id": ObjectId(id)})
    return serialize_assignment(assignment) if assignment else None


async def get_assignments_by_teacher(teacher_id: str):
    teacher_oid = ObjectId(teacher_id)
    cursor = db.assignments.find({
        "$or": [
            {"teacherId": teacher_oid},
            {"teacherId": teacher_id}
        ]
    })
    return [serialize_assignment(a) async for a in cursor]


async def get_assignments_by_course(course_id: str):
    cursor = db.assignments.find({"courseId": ObjectId(course_id)})
    return [serialize_assignment(a) async for a in cursor]


# async def get_assignments_for_student(student_id: str):
#     student = await db.students.find_one({"_id": ObjectId(student_id)})
#     if not student or "enrolledCourses" not in student:
#         return []

#     enrolled = [ObjectId(cid) for cid in student["enrolledCourses"]]

#     cursor = db.assignments.find({"courseId": {"$in": enrolled}})
#     return [serialize_assignment(a) async for a in cursor]


async def update_assignment(id: str, teacher_id: str, updates: dict):
    assignment = await db.assignments.find_one({"_id": ObjectId(id)})
    if not assignment:
        return None

    if str(assignment["teacherId"]) != teacher_id:
        return "UNAUTHORIZED"

    updates["updatedAt"] = datetime.utcnow()

    await db.assignments.update_one(
        {"_id": ObjectId(id)},
        {"$set": updates}
    )

    new_data = await db.assignments.find_one({"_id": ObjectId(id)})
    return serialize_assignment(new_data)


async def delete_assignment(id: str, teacher_id: str):
    assignment = await db.assignments.find_one({"_id": ObjectId(id)})
    if not assignment:
        return None

    if str(assignment["teacherId"]) != teacher_id:
        return "UNAUTHORIZED"

    await db.assignments.delete_one({"_id": ObjectId(id)})
    return True
