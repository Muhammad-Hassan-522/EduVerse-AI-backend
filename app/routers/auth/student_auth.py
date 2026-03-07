from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from app.auth.auth_service import login_user
from app.schemas.users import UserCreate
from app.crud import users, students

router = APIRouter(prefix="/auth/student", tags=["Student Authentication"])


@router.post("/signup")
async def signup_student(payload: UserCreate):

    if payload.role != "student":
        raise HTTPException(403, "This endpoint is only for student signup")

    user = await users.create_user(payload.dict())

    if payload.role == "student":
        await students.create_student(user["id"])

    return {"message": "Student created successfully", "user": user}

