from fastapi import Depends
from app.auth.router import oauth2_scheme
from app.db.database import db
from app.utils.security import decode_token
from bson import ObjectId
from fastapi import HTTPException


async def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = decode_token(token)

    # Allow multiple valid statuses (active for teachers/admins, studying for students)
    user = await db.users.find_one(
        {"_id": ObjectId(payload["user_id"]), "status": {"$in": ["active", "studying"]}}
    )

    if not user:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    # tenantId is stored in the role-specific collection (teachers, students, admins)
    # not in the users collection, so we need to fetch it based on user role
    tenant_id = user.get("tenantId")  # Check users collection first

    if not tenant_id:
        user_id = user["_id"]
        role = user["role"]

        # Fetch tenantId from the role-specific collection
        if role == "teacher":
            role_doc = await db.teachers.find_one({"userId": user_id})
            if role_doc:
                tenant_id = role_doc.get("tenantId")
        elif role == "student":
            role_doc = await db.students.find_one({"userId": user_id})
            if role_doc:
                tenant_id = role_doc.get("tenantId")
        elif role == "admin":
            role_doc = await db.admins.find_one({"userId": user_id})
            if role_doc:
                tenant_id = role_doc.get("tenantId")

    return {
        "user_id": str(user["_id"]),
        "role": user["role"],
        "tenant_id": str(tenant_id) if tenant_id else None,
    }


def require_role(*allowed_roles: str):
    def role_checker(current_user=Depends(get_current_user)):
        if current_user["role"] not in allowed_roles:
            raise HTTPException(status_code=403, detail="Forbidden: Insufficient Role")
        return current_user

    return role_checker


def require_tenant(current_user=Depends(get_current_user)):
    if not current_user.get("tenant_id"):
        raise HTTPException(
            status_code=403, detail="Tenant context required for this operation"
        )
    return current_user
