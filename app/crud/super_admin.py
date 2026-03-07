from bson import ObjectId
from datetime import datetime
from app.db.database import db
from app.crud.users import serialize_user


def serialize_superadmin(user_doc):
    return {
        "id": str(user_doc["_id"]),
        "userId": str(user_doc["_id"]),
        "user": serialize_user(user_doc),  # attach user details
        "createdAt": user_doc["createdAt"],
        "updatedAt": user_doc["updatedAt"],
    }


async def get_superadmin_by_user(user_id: str):
    user = await db.users.find_one({"_id": ObjectId(user_id), "role": "super-admin"})
    if not user:
        return None
    return serialize_superadmin(user)


ROLE_NAME = "super-admin"


async def update_superadmin(user_id: str, updates: dict):
    ROLE_NAME = "super-admin"  # consistent

    allowed_fields = ["fullName", "profileImageURL", "contactNo", "country", "status"]
    user_fields = {k: v for k, v in updates.items() if k in allowed_fields}

    if user_fields:
        user_fields["updatedAt"] = datetime.utcnow()
        result = await db.users.update_one(
            {"_id": ObjectId(user_id), "role": ROLE_NAME}, {"$set": user_fields}
        )
        # Optional: check matched_count
        if result.matched_count == 0:
            return None

    # Fetch the updated document
    user = await db.users.find_one({"_id": ObjectId(user_id), "role": ROLE_NAME})
    if not user:
        return None

    return serialize_superadmin(user)
