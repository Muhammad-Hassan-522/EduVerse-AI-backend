from bson import ObjectId
from datetime import datetime

from fastapi import HTTPException
from app.db.database import db
from app.crud.users import serialize_user


def serialize_student(s, user):
    tenant_id = s.get("tenantId")
    # Convert ObjectIds in course arrays to strings
    enrolled_courses = [str(c) if isinstance(c, ObjectId) else c for c in s.get("enrolledCourses", [])]
    completed_courses = [str(c) if isinstance(c, ObjectId) else c for c in s.get("completedCourses", [])]
    return {
        "id": str(s["_id"]),
        "userId": str(s["userId"]),
        "tenantId": str(tenant_id) if tenant_id else None,
        "user": serialize_user(user),  #  attach user
        "enrolledCourses": enrolled_courses,
        "completedCourses": completed_courses,
        "status": s.get("status"),
        "createdAt": s.get("createdAt"),
        "updatedAt": s.get("updatedAt"),
    }


async def get_student_by_user(user_id: str):
    student = await db.students.find_one({"userId": ObjectId(user_id)})
    if not student:
        return None

    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        return None

    return serialize_student(student, user)


async def create_student(user_id: str):
    data = {
        "userId": ObjectId(user_id),
        "enrolledCourses": [],
        "completedCourses": [],
        "status": "active",
        "createdAt": datetime.utcnow(),
        "updatedAt": datetime.utcnow(),
    }

    result = await db.students.insert_one(data)
    student = await db.students.find_one({"_id": result.inserted_id})

    # Fetch the user document
    user = await db.users.find_one({"_id": ObjectId(user_id)})

    return serialize_student(student, user)


async def update_student_profile(user_id: str, updates: dict):
    student_fields = {}
    user_fields = {}

    # ---- student fields ----
    for field in ["status", "enrolledCourses", "completedCourses"]:
        if field in updates:
            student_fields[field] = updates[field]

    # ---- user fields ----
    for field in ["fullName", "profileImageURL", "contactNo", "country"]:
        if field in updates:
            user_fields[field] = updates[field]

    if student_fields:
        student_fields["updatedAt"] = datetime.utcnow()
        await db.students.update_one(
            {"userId": ObjectId(user_id)}, {"$set": student_fields}
        )

    if user_fields:
        user_fields["updatedAt"] = datetime.utcnow()
        await db.users.update_one({"_id": ObjectId(user_id)}, {"$set": user_fields})

    # ---- fetch updated documents ----
    student = await db.students.find_one({"userId": ObjectId(user_id)})
    user = await db.users.find_one({"_id": ObjectId(user_id)})

    if not student or not user:
        return None

    return serialize_student(student, user)


async def assign_student_to_tenant(student_id: str, tenant_id: str):
    if not ObjectId.is_valid(student_id):
        raise HTTPException(status_code=400, detail="Invalid student ID")
    if not ObjectId.is_valid(tenant_id):
        raise HTTPException(status_code=400, detail="Invalid tenant ID")

    # check tenant exists
    tenant = await db.tenants.find_one({"_id": ObjectId(tenant_id), "isDeleted": False})
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # update student
    result = await db.students.update_one(
        {"_id": ObjectId(student_id)},
        {"$set": {"tenantId": ObjectId(tenant_id), "updatedAt": datetime.utcnow()}},
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Student not found")

    # fetch updated student
    student = await db.students.find_one({"_id": ObjectId(student_id)})
    user = await db.users.find_one({"_id": ObjectId(student["userId"])})

    from app.crud.students import serialize_student

    return serialize_student(student, user)


# in app/crud/students.py
async def enroll_student_in_course(student_id: str, course_id: str):
    from app.db.database import db

    # Validate IDs
    if not ObjectId.is_valid(student_id) or not ObjectId.is_valid(course_id):
        raise HTTPException(status_code=400, detail="Invalid ID")

    # Get course
    course = await db.courses.find_one({"_id": ObjectId(course_id)})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # Get student
    student = await db.students.find_one({"_id": ObjectId(student_id)})
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Update tenantId if not set
    if "tenantId" not in student or not student.get("tenantId"):
        await db.students.update_one(
            {"_id": ObjectId(student_id)},
            {"$set": {"tenantId": course["tenantId"], "updatedAt": datetime.utcnow()}},
        )

    # Enroll student in course
    enrolled = student.get("enrolledCourses", [])
    if str(course["_id"]) not in enrolled:
        enrolled.append(str(course["_id"]))
        await db.students.update_one(
            {"_id": ObjectId(student_id)},
            {"$set": {"enrolledCourses": enrolled, "updatedAt": datetime.utcnow()}},
        )

    # Fetch updated student
    student = await db.students.find_one({"_id": ObjectId(student_id)})
    user = await db.users.find_one({"_id": ObjectId(student["userId"])})

    return serialize_student(student, user)
