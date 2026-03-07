from fastapi import HTTPException
from app.crud.users import create_user, verify_user
from app.crud.users import update_last_login
from app.utils.security import create_access_token


async def register_user(data):
    user = await create_user(data)
    return user


async def login_user(email: str, password: str):
    user = await verify_user(email, password)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid email or password")

    await update_last_login(user["id"])

    token = create_access_token(
        {
            "user_id": user["id"],
            "role": user["role"],
            "tenant_id": user["tenantId"],
            "student_id": user.get("studentId"),
            "teacher_id": user.get("teacherId"),
            "admin_id": user.get("adminId"),
            "full_name": user.get("fullName"),
        }
    )

    return {"access_token": token, "token_type": "bearer", "user": user}
