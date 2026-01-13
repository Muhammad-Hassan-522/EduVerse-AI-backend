from fastapi import APIRouter, HTTPException, Depends, status
from bson import ObjectId
from datetime import datetime
from dotenv import load_dotenv
from app.schemas.teachers import TeacherUpdate
from app.crud import admins as crud_admin
from app.crud.students import delete_student as crud_delete_student
from app.crud.teachers import delete_teacher as crud_delete_teacher, update_teacher as crud_update_teacher
from app.auth.dependencies import require_role

load_dotenv()

router = APIRouter(prefix="/admin", tags=["Admin"], dependencies=[Depends(require_role("admin"))])

# ------------------ Dashboard ------------------

@router.get("/teachers")
async def list_teachers():
    teachers = await crud_admin.get_all_teachers()
    return {"total": len(teachers), "teachers": teachers}

@router.get("/students")
async def list_students():
    # Calling list_students without tenantId implies getting default or all if logic allows.
    # Note: Source logic had this call. Target crud/students.py was updated to handle optional tenantId.
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
async def delete_student(student_id: str, tenant_id: str):
    # crud_delete_student handles both student and user documents
    success = await crud_delete_student(student_id, tenant_id)
    if not success:
        raise HTTPException(status_code=404, detail="Student not found")
    return {"message": "Student deleted successfully"}

# ------------------ Teachers Endpoints ------------------

@router.put("/update-teacher/{id}")
async def admin_update_teacher(id: str, updates: TeacherUpdate):
    updated = await crud_update_teacher(id, updates.dict(exclude_unset=True))
    if not updated:
        raise HTTPException(404, "Teacher not found")
    return updated

@router.delete("/teachers/{teacher_id}")
async def delete_teacher(teacher_id: str):
    # crud_delete_teacher handles both teacher and user documents
    success = await crud_delete_teacher(teacher_id)
    if not success:
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
