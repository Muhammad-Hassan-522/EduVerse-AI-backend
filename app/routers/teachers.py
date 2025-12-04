from fastapi import APIRouter, HTTPException
from bson import ObjectId
from app.schemas.teachers import TeacherCreate, TeacherUpdate, TeacherResponse, ChangePassword
from app.crud.teachers import (
    create_teacher, get_all_teachers, get_teacher, update_teacher,
    delete_teacher, change_password, get_teacher_students, get_teacher_dashboard
)

router = APIRouter(prefix="/teachers", tags=["Teachers"])

def validate_object_id(id: str, name="id"):
    if not ObjectId.is_valid(id):
        raise HTTPException(400, f"Invalid ObjectId for {name}")

# ------------------ CRUD ------------------

@router.post("/", response_model=TeacherResponse)
async def create_teacher_route(data: TeacherCreate):
    return await create_teacher(data)

@router.get("/", response_model=list[TeacherResponse])
async def get_all_teachers_route():
    return await get_all_teachers()

@router.get("/{id}", response_model=TeacherResponse)
async def get_teacher_route(id: str):
    validate_object_id(id)
    t = await get_teacher(id)
    if not t:
        raise HTTPException(404, "Teacher not found")
    return t

@router.put("/{id}", response_model=TeacherResponse)
async def update_teacher_route(id: str, updates: TeacherUpdate):
    validate_object_id(id)
    updated = await update_teacher(id, updates.dict(exclude_unset=True))
    if not updated:
        raise HTTPException(404, "Teacher not found")
    return updated

@router.put("/{id}/password")
async def change_teacher_password_route(id: str, data: ChangePassword):
    validate_object_id(id)
    result = await change_password(id, data.oldPassword, data.newPassword)
    if result == "INCORRECT":
        raise HTTPException(403, "Old password incorrect")
    if not result:
        raise HTTPException(404, "Teacher not found")
    return {"message": "Password updated successfully"}

@router.delete("/{id}")
async def delete_teacher_route(id: str):
    validate_object_id(id)
    result = await delete_teacher(id)
    if not result:
        raise HTTPException(404, "Teacher not found")
    return {"message": "Teacher deleted successfully"}

# ------------------ Dashboard & Students ------------------

@router.get("/{id}/students")
async def teacher_students_route(id: str):
    validate_object_id(id)
    students = await get_teacher_students(id)
    return {"total": len(students), "students": students}

@router.get("/{id}/dashboard")
async def teacher_dashboard_route(id: str):
    validate_object_id(id)
    stats = await get_teacher_dashboard(id)
    return stats

# ------------------ Placeholder Integration ------------------

@router.get("/{id}/assignments")
async def teacher_assignments(id: str):
    return {"message": f"Fetch assignments for teacher {id}"}

@router.get("/{id}/courses")
async def teacher_courses(id: str):
    return {"message": f"Fetch courses for teacher {id}"}

@router.get("/{id}/quizzes")
async def teacher_quizzes(id: str):
    return {"message": f"Fetch quizzes for teacher {id}"}
