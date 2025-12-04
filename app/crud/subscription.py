# app/routes/subscription.py
from fastapi import APIRouter, HTTPException
from typing import List
from app.db.database import db  # your motor/mongodb client
from app.schemas.subscription import Subscription
from bson import ObjectId

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])

# Get all subscriptions
@router.get("/", response_model=List[Subscription])
async def get_subscriptions():
    subscriptions = await db.subscriptions.find().to_list(100)
    return subscriptions

# Get subscription by tenantId
@router.get("/{tenant_id}", response_model=Subscription)
async def get_subscription(tenant_id: str):
    subscription = await db.subscriptions.find_one({"tenantId": tenant_id})
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return subscription

# Create a new subscription
@router.post("/", response_model=Subscription)
async def create_subscription(sub: Subscription):
    sub_dict = sub.dict()
    result = await db.subscriptions.insert_one(sub_dict)
    sub_dict["_id"] = str(result.inserted_id)
    return sub_dict

# Update subscription by tenantId
@router.put("/{tenant_id}", response_model=Subscription)
async def update_subscription(tenant_id: str, sub: Subscription):
    result = await db.subscriptions.update_one(
        {"tenantId": tenant_id},
        {"$set": sub.dict()}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Subscription not found")
    updated_sub = await db.subscriptions.find_one({"tenantId": tenant_id})
    return updated_sub

# Delete subscription by tenantId
@router.delete("/{tenant_id}")
async def delete_subscription(tenant_id: str):
    result = await db.subscriptions.delete_one({"tenantId": tenant_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return {"detail": "Subscription deleted successfully"}

