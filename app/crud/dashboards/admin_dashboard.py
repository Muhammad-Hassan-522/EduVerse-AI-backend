from bson import ObjectId
from app.db.database import db


async def get_all_students(tenant_id: str):
    students = []

    async for s in db.students.find({"tenantId": ObjectId(tenant_id)}):
        user = await db.users.find_one(
            {"_id": s["userId"], "tenantId": ObjectId(tenant_id)}
        )

        if not user:
            continue

        # Merge user data directly into student object
        students.append({
            "id": str(s["_id"]),
            "fullName": user.get("fullName", ""),
            "email": user.get("email", ""),
            "status": user.get("status", "active"),
            "country": user.get("country"),
            "enrolledCourses": s.get("enrolledCourses", []),
            "completedCourses": s.get("completedCourses", [])
        })

    return students


async def get_all_teachers(tenant_id: str):
    teachers = []

    async for t in db.teachers.find({"tenantId": ObjectId(tenant_id)}):
        user = await db.users.find_one(
            {"_id": t["userId"], "tenantId": ObjectId(tenant_id)}
        )

        if not user:
            continue

        # Merge user data directly into teacher object
        teachers.append({
            "id": str(t["_id"]),
            "fullName": user.get("fullName", ""),
            "email": user.get("email", ""),
            "status": user.get("status", "active"),
            "role": user.get("role", "teacher"),
            "assignedCourses": [str(c) for c in t.get("assignedCourses", [])],
            "qualifications": t.get("qualifications", []),
            "subjects": t.get("subjects", [])
        })

    return teachers


async def get_all_courses(tenant_id: str):
    courses = []

    async for c in db.courses.find({"tenantId": ObjectId(tenant_id)}):
        courses.append({
            "id": str(c["_id"]),
            "title": c.get("title", ""),
            "courseCode": c.get("courseCode", ""),
            "description": c.get("description", ""),
            "category": c.get("category", ""),
            "status": c.get("status", ""),
            "duration": c.get("duration", ""),
            "enrolledStudents": c.get("enrolledStudents", 0),
            "teacherId": str(c.get("teacherId", "")),
            "tenantId": str(c.get("tenantId", ""))
        })

    return courses
