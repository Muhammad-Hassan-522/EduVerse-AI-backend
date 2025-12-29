from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from app.auth.auth_service import login_user
from app.schemas.users import UserCreate
from app.crud import admins, students, users, teachers

router = APIRouter(prefix="/auth/teacher", tags=["Teacher Authentication"])


@router.post("/signup")
async def signup_teacher(payload: UserCreate):

    if payload.role != "teacher":
        raise HTTPException(403, "This endpoint is only for teacher signup")

    user = await users.create_user(payload.dict())

    if payload.role == "teacher":
        await teachers.create_teacher(user["id"])

    return {"message": "Teacher created successfully", "user": user}

