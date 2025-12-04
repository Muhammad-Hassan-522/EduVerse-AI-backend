from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from bson import ObjectId
from datetime import datetime
import os
from dotenv import load_dotenv

from app.schemas.admins import (
    AdminCreate,
    AdminLogin,
    AdminResponse,
    AdminUpdateProfile,
    AdminUpdatePassword
)
from app.crud import admins as crud_admin

load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY", "secret123")

router = APIRouter(prefix="/admin", tags=["Admin"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="admin/login")

# ------------------ Auth ------------------

@router.post("/signup", response_model=AdminResponse)
async def signup(admin: AdminCreate):
    try:
        new_admin = await crud_admin.create_admin(admin)
        return AdminResponse(**new_admin)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/login")
async def login(admin: AdminLogin):
    db_admin = await crud_admin.get_admin_by_email(admin.email)
    if not db_admin:
        raise HTTPException(status_code=404, detail="Admin not found")
    if not await crud_admin.verify_password(admin.password, db_admin["password"]):
        raise HTTPException(status_code=400, detail="Invalid password")

    token = jwt.encode({"admin_id": str(db_admin["_id"])}, SECRET_KEY)
    return {
        "token": token,
        "admin": {
            "id": str(db_admin["_id"]),
            "fullName": db_admin["fullName"],
            "email": db_admin["email"]
        }
    }

# ------------------ Profile ------------------

@router.get("/profile", response_model=AdminResponse)
async def get_profile(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY)
        admin_id = payload.get("admin_id")
    except:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    admin = await crud_admin.db.admins.find_one({"_id": ObjectId(admin_id)})
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")
    return AdminResponse(**crud_admin.serialize_admin(admin))

@router.patch("/update-profile", response_model=AdminResponse)
async def update_profile(data: AdminUpdateProfile, token: str = Depends(oauth2_scheme)):
    payload = jwt.decode(token, SECRET_KEY)
    admin_id = payload.get("admin_id")
    updated_admin = await crud_admin.update_admin_profile(admin_id, data)
    if not updated_admin:
        raise HTTPException(status_code=400, detail="Nothing to update")
    return AdminResponse(**updated_admin)

@router.patch("/update-password")
async def update_password(data: AdminUpdatePassword, token: str = Depends(oauth2_scheme)):
    payload = jwt.decode(token, SECRET_KEY)
    admin_id = payload.get("admin_id")
    try:
        await crud_admin.update_admin_password(admin_id, data.oldPassword, data.newPassword)
        return {"message": "Password updated successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# ------------------ Dashboard ------------------

@router.get("/teachers")
async def list_teachers():
    teachers = await crud_admin.get_all_teachers()
    return {"total": len(teachers), "teachers": teachers}

@router.get("/students")
async def list_students():
    students = await crud_admin.get_all_students()
    return {"total": len(students), "students": students}

@router.get("/courses")
async def list_courses():
    courses = await crud_admin.get_all_courses()
    return {"total": len(courses), "courses": courses}

# ------------------ Students Endpoints ------------------

@router.patch("/students/{student_id}")
async def update_student(student_id: str, data: dict):
    student = await crud_admin.db.students.find_one({"_id": ObjectId(student_id)})
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    update_data = {k: v for k, v in data.items() if v is not None}
    if update_data:
        update_data["updatedAt"] = datetime.utcnow()
        await crud_admin.db.students.update_one({"_id": ObjectId(student_id)}, {"$set": update_data})

    updated_student = await crud_admin.db.students.find_one({"_id": ObjectId(student_id)})

    return {
        "id": str(updated_student["_id"]),
        "name": updated_student.get("fullName", ""),
        "email": updated_student.get("email", ""),
        "class": updated_student.get("className", "N/A"),
        "rollNo": updated_student.get("rollNo", "N/A"),
        "status": updated_student.get("status", "Enrolled")
    }

@router.delete("/students/{student_id}")
async def delete_student(student_id: str):
    result = await crud_admin.db.students.delete_one({"_id": ObjectId(student_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Student not found")
    return {"message": "Student deleted successfully"}

# ------------------ Teachers Endpoints ------------------

@router.patch("/teachers/{teacher_id}")
async def update_teacher(teacher_id: str, data: dict):
    teacher = await crud_admin.db.teachers.find_one({"_id": ObjectId(teacher_id)})
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")

    update_data = {k: v for k, v in data.items() if v is not None}
    if update_data:
        update_data["updatedAt"] = datetime.utcnow()
        await crud_admin.db.teachers.update_one({"_id": ObjectId(teacher_id)}, {"$set": update_data})

    updated_teacher = await crud_admin.db.teachers.find_one({"_id": ObjectId(teacher_id)})

    return {
        "id": str(updated_teacher["_id"]),
        "name": updated_teacher.get("fullName", ""),
        "email": updated_teacher.get("email", ""),
        "assignedCourses": updated_teacher.get("assignedCourses", []),
        "totalStudents": updated_teacher.get("totalStudents", 0),
        "role": updated_teacher.get("role", "Teacher"),
        "status": updated_teacher.get("status", "Inactive")
    }

@router.delete("/teachers/{teacher_id}")
async def delete_teacher(teacher_id: str):
    result = await crud_admin.db.teachers.delete_one({"_id": ObjectId(teacher_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Teacher not found")
    return {"id": teacher_id, "message": "Teacher deleted successfully"}

# ------------------ Courses Endpoints ------------------

@router.patch("/courses/{course_id}")
async def update_course(course_id: str, data: dict):
    course = await crud_admin.db.courses.find_one({"_id": ObjectId(course_id)})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    update_data = {k: v for k, v in data.items() if v is not None}
    if update_data:
        update_data["updatedAt"] = datetime.utcnow()
        await crud_admin.db.courses.update_one({"_id": ObjectId(course_id)}, {"$set": update_data})

    updated_course = await crud_admin.db.courses.find_one({"_id": ObjectId(course_id)})

    return {
        "id": str(updated_course["_id"]),
        "title": updated_course.get("title", ""),
        "code": updated_course.get("courseCode", ""),
        "instructor": updated_course.get("instructor", "N/A"),
        "status": updated_course.get("status", "Active")
    }

@router.delete("/courses/{course_id}")
async def delete_course(course_id: str):
    result = await crud_admin.db.courses.delete_one({"_id": ObjectId(course_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Course not found")
    return {"message": "Course deleted successfully"}
