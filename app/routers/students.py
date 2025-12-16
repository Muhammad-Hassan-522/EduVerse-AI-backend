from fastapi import APIRouter, HTTPException
from app.schemas.student import (
    StudentCreate,
    StudentLogin,
    StudentUpdate,
    StudentResponse,
)
from app.crud import students as crud_student

router = APIRouter(prefix="/students", tags=["Students"])

# -----------------------------------------------------
# LOGIN STUDENT (POST /students/login)
# -----------------------------------------------------
@router.post("/login", response_model=StudentResponse)
async def login_student(payload: StudentLogin):

    db_student = await crud_student.get_student_by_email(payload.email)

    if not db_student or payload.password != db_student["password"]:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    db_student["id"] = db_student["_id"]
    del db_student["_id"]

    return StudentResponse(**db_student)

# -----------------------------------------------------
# CREATE STUDENT  (POST /students/{tenantId})
# -----------------------------------------------------
@router.post("/{tenantId}", response_model=StudentResponse)
async def create_student(tenantId: str, student: StudentCreate):

    new_student = await crud_student.create_student(student, tenantId)

    new_student["id"] = new_student["_id"]
    del new_student["_id"]

    return StudentResponse(**new_student)






# -----------------------------------------------------
# LIST STUDENTS FOR TENANT
# -----------------------------------------------------
@router.get("/{tenantId}", response_model=list[StudentResponse])
async def list_students(tenantId: str):

    students = await crud_student.list_students(tenantId)

    result = []
    for s in students:
        s["id"] = s["_id"]
        del s["_id"]
        result.append(StudentResponse(**s))

    return result



# -----------------------------------------------------
# GET SINGLE STUDENT
# -----------------------------------------------------
@router.get("/{tenantId}/{studentId}", response_model=StudentResponse)
async def get_student(tenantId: str, studentId: str):

    student = await crud_student.get_student_by_id(studentId, tenantId)

    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    student["id"] = student["_id"]
    del student["_id"]

    return StudentResponse(**student)



# -----------------------------------------------------
# UPDATE STUDENT
# -----------------------------------------------------
@router.patch("/{tenantId}/{studentId}", response_model=StudentResponse)
async def update_student(tenantId: str, studentId: str, update: StudentUpdate):

    updated = await crud_student.update_student(studentId, tenantId, update)

    if not updated:
        raise HTTPException(status_code=404, detail="Student not found")

    updated["id"] = updated["_id"]
    del updated["_id"]

    return StudentResponse(**updated)



# -----------------------------------------------------
# DELETE STUDENT
# -----------------------------------------------------
@router.delete("/{tenantId}/{studentId}")
async def delete_student(tenantId: str, studentId: str):

    success = await crud_student.delete_student(studentId, tenantId)

    if not success:
        raise HTTPException(status_code=404, detail="Student not found")

    return {"status": "success", "message": "Student deleted"}
