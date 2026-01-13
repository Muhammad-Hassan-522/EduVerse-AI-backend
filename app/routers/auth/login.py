from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from app.auth.auth_service import login_user
from app.schemas.users import UserLogin

router = APIRouter(tags=["Generate Token / Login"])


@router.post("/auth/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """OAuth2 compatible token login, for use with swagger or standard clients."""
    result = await login_user(form_data.username, form_data.password)
    return result


@router.post("/login")
async def json_login(payload: UserLogin):
    """JSON based login, primarily for use by our custom frontend."""
    result = await login_user(payload.email, payload.password)
    return result
