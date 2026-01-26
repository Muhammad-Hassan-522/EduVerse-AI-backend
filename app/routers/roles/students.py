from fastapi import APIRouter, HTTPException, Depends
from app.schemas.students import (
    StudentCreate,
    StudentLogin,
    StudentUpdate,
    StudentResponse,
)
from app.crud import students as crud_student
from app.auth.dependencies import get_current_user, require_role
from app.schemas.teachers import ChangePassword


router = APIRouter(
    prefix="/students",
    tags=["Student – Self"],
    dependencies=[Depends(require_role("student"))],
)

# PROFILE (ME)


@router.get("/me", response_model=StudentResponse)
async def me(current_user=Depends(get_current_user)):
    return await crud_student.get_student_me(current_user)


@router.patch("/me", response_model=StudentResponse)
async def update_me(
    payload: StudentUpdate,
    current_user=Depends(get_current_user),
):
    return await crud_student.update_student_me(current_user, payload)


@router.put("/me/password")
async def change_password(
    payload: ChangePassword,
    current_user=Depends(get_current_user),
):
    await crud_student.change_student_me_password(
        current_user, payload.oldPassword, payload.newPassword
    )


# -----------------------------------------------------
# PROFILE (ME)
# -----------------------------------------------------
# @router.get(
#     "/me", response_model=StudentResponse, dependencies=[Depends(get_current_user)]
# )
# async def get_my_profile(current_user=Depends(get_current_user)):
#     uid = (
#         current_user.get("user_id")
#         if isinstance(current_user, dict)
#         else current_user.id
#     )

#     # We need to ensure crud_student has get_student_by_user logic
#     student = await crud_student.get_student_by_user(uid)
#     if not student:
#         raise HTTPException(status_code=404, detail="Student profile not found")

#     student["id"] = student["_id"]
#     del student["_id"]
#     return StudentResponse(**student)


# # -----------------------------------------------------
# # LOGIN STUDENT (POST /students/login)
# # -----------------------------------------------------
# @router.post("/login", response_model=StudentResponse)
# async def login_student(payload: StudentLogin):
#     # Public endpoint
#     db_student = await crud_student.get_student_by_email(payload.email)

#     if not db_student or payload.password != db_student["password"]:
#         raise HTTPException(status_code=401, detail="Invalid credentials")

#     db_student["id"] = db_student["_id"]
#     del db_student["_id"]

#     return StudentResponse(**db_student)


# -----------------------------------------------------
# CREATE STUDENT  (POST /students/{tenantId})
# -----------------------------------------------------
@router.post(
    "/{tenantId}",
    response_model=StudentResponse,
    dependencies=[Depends(get_current_user)],
)
async def create_student(tenantId: str, student: StudentCreate):

    new_student = await crud_student.create_student(student, tenantId)

    new_student["id"] = new_student["_id"]
    del new_student["_id"]

    return StudentResponse(**new_student)


# -----------------------------------------------------
# LIST STUDENTS FOR TENANT
# -----------------------------------------------------
@router.get(
    "/{tenantId}",
    response_model=list[StudentResponse],
    dependencies=[Depends(get_current_user)],
)
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
@router.get(
    "/{tenantId}/{studentId}",
    response_model=StudentResponse,
    dependencies=[Depends(get_current_user)],
)
async def get_student(tenantId: str, studentId: str):

    student = await crud_student.get_student_by_id(studentId, tenantId)

    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    student["id"] = student["_id"]
    del student["_id"]

    return StudentResponse(**student)


# # -----------------------------------------------------
# # UPDATE STUDENT
# # -----------------------------------------------------
# @router.patch(
#     "/{tenantId}/{studentId}",
#     response_model=StudentResponse,
#     dependencies=[Depends(get_current_user)],
# )
# async def update_student(tenantId: str, studentId: str, update: StudentUpdate):

#     updated = await crud_student.update_student(studentId, tenantId, update)

#     if not updated:
#         raise HTTPException(status_code=404, detail="Student not found")

#     updated["id"] = updated["_id"]
#     del updated["_id"]

#     return StudentResponse(**updated)


# -----------------------------------------------------
# DELETE STUDENT
# -----------------------------------------------------
@router.delete("/{tenantId}/{studentId}", dependencies=[Depends(get_current_user)])
async def delete_student(tenantId: str, studentId: str):

    success = await crud_student.delete_student(studentId, tenantId)

    if not success:
        raise HTTPException(status_code=404, detail="Student not found")

    return {"status": "success", "message": "Student deleted"}
