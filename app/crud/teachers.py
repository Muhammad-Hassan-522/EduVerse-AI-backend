from bson import ObjectId
from datetime import datetime
from app.db.database import db
from app.crud.users import serialize_user


def serialize_teacher(t, user):
    tenant_id = t.get("tenantId")
    # Convert ObjectIds in assignedCourses to strings
    assigned_courses = [str(c) if isinstance(c, ObjectId) else c for c in t.get("assignedCourses", [])]
    return {
        "id": str(t["_id"]),
        "userId": str(t["userId"]),
        "tenantId": str(tenant_id) if tenant_id else None,
        "user": serialize_user(user),  # attach user
        "assignedCourses": assigned_courses,
        "qualifications": t.get("qualifications", []),
        "subjects": t.get("subjects", []),
        "status": t.get("status"),
        "createdAt": t.get("createdAt"),
        "updatedAt": t.get("updatedAt"),
    }


async def get_teacher_by_user(user_id: str):
    teacher = await db.teachers.find_one({"userId": ObjectId(user_id)})
    if not teacher:
        return None

    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        return None

    return serialize_teacher(teacher, user)


async def create_teacher(user_id: str):
    data = {
        "userId": ObjectId(user_id),
        "assignedCourses": [],
        "qualifications": [],
        "subjects": [],
        "status": "active",
        "createdAt": datetime.utcnow(),
        "updatedAt": datetime.utcnow(),
    }

    result = await db.teachers.insert_one(data)
    teacher = await db.teachers.find_one({"_id": result.inserted_id})

    # Fetch the user document
    user = await db.users.find_one({"_id": ObjectId(user_id)})

    return serialize_teacher(teacher, user)


async def update_teacher_profile(user_id: str, updates: dict):
    teacher_fields = {}
    user_fields = {}

    # ---- teacher-specific fields ----
    for field in ["status", "assignedCourses", "qualifications", "subjects"]:
        if field in updates:
            teacher_fields[field] = updates[field]

    # ---- user fields ----
    for field in ["fullName", "profileImageURL", "contactNo", "country"]:
        if field in updates:
            user_fields[field] = updates[field]

    if teacher_fields:
        teacher_fields["updatedAt"] = datetime.utcnow()
        await db.teachers.update_one(
            {"userId": ObjectId(user_id)}, {"$set": teacher_fields}
        )

    if user_fields:
        user_fields["updatedAt"] = datetime.utcnow()
        await db.users.update_one({"_id": ObjectId(user_id)}, {"$set": user_fields})

    # ---- fetch updated documents ----
    teacher = await db.teachers.find_one({"userId": ObjectId(user_id)})
    user = await db.users.find_one({"_id": ObjectId(user_id)})

    if not teacher or not user:
        return None

    return serialize_teacher(teacher, user)
