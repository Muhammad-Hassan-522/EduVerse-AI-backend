# app/routers/subscription.py
from fastapi import APIRouter, HTTPException
from typing import List
from app.schemas.subscription import Subscription
from app.crud.subscription import (
    fetch_subscriptions,
    fetch_subscription_by_tenant,
    create_subscription as crud_create_sub,
    update_subscription as crud_update_sub,
    delete_subscription as crud_delete_sub
)

from fastapi import APIRouter, HTTPException, Depends
from app.auth.dependencies import require_role

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"], dependencies=[Depends(require_role("admin", "super_admin"))])

# Get all subscriptions
@router.get("/", response_model=List[Subscription])
async def get_subscriptions():
    return await fetch_subscriptions()

# Get subscription by tenant_id
@router.get("/{tenant_id}", response_model=Subscription)
async def get_subscription(tenant_id: str):
    sub = await fetch_subscription_by_tenant(tenant_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return sub

# Create a new subscription
@router.post("/", response_model=Subscription)
async def create_subscription(sub: Subscription):
    return await crud_create_sub(sub)

# Update subscription by tenantId
@router.put("/{tenant_id}", response_model=Subscription)
async def update_subscription(tenant_id: str, sub: Subscription):
    updated_sub = await crud_update_sub(tenant_id, sub)
    if not updated_sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return updated_sub

# Delete subscription by tenantId
@router.delete("/{tenant_id}")
async def delete_subscription(tenant_id: str):
    success = await crud_delete_sub(tenant_id)
    if not success:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return {"detail": "Subscription deleted successfully"}
