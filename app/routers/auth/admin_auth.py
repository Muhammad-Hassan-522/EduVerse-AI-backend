from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from app.auth.auth_service import login_user
from app.schemas.tenants import TenantCreate
from app.schemas.users import AdminSignupRequest
from app.crud import users, admins
from app.crud.tenants import create_tenant

router = APIRouter(prefix="/auth/admin", tags=["Admin Authentication"])


@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup_admin(payload: AdminSignupRequest):

    # Create Tenant using tenant CRUD
    tenant_data = {
        "tenantName": payload.tenantName,
        "tenantLogoUrl": payload.tenantLogoUrl,
        "adminEmail": payload.email,
        # "subscriptionId": payload.subscriptionId | None,
    }
    tenant = await create_tenant(TenantCreate(**tenant_data))

    if payload.role != "admin":
        raise HTTPException(403, "This endpoint is only for admin signup")

    user_data = payload.model_dump()
    user_data["role"] = "admin"  # assign role internally
    user_data["tenantId"] = tenant["id"]  # assign created tenant
    user = await users.create_user(user_data)

    # Create admin profile
    await admins.create_admin_profile(user["id"], tenant["id"])

    return {
        "message": "Admin and tenant created successfully",
        "user": user,
        "tenant": tenant,
    }
