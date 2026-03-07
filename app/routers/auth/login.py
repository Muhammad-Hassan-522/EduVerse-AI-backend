from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from app.auth.auth_service import login_user

router = APIRouter(prefix="/auth", tags=["Generate Token / Login"])


@router.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):

    result = await login_user(form_data.username, form_data.password)

    if not result:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return {
        "access_token": result["access_token"],
        "token_type": "bearer",
        "user": result["user"],
    }
