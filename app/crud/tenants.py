from fastapi import HTTPException, status
from app.db.database import db
from datetime import datetime
from bson import ObjectId
from typing import Optional, Any


def _ensure_objectid(_id: str, name: str = "id"):
    if not ObjectId.is_valid(_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid ObjectId for {name}",
        )
    return ObjectId(_id)


# -------------------------
# Convert MongoDB document → API format (Python dict)
# -------------------------
def serialize_tenant(tenant: dict) -> dict:
    return {
        "id": str(tenant["_id"]),  # convert ObjectId -> string
        "tenantName": tenant["tenantName"],
        "tenantLogoUrl": tenant.get("tenantLogoUrl"),
        "adminEmail": tenant["adminEmail"],
        "status": tenant.get("status", "active"),
        "subscriptionId": (
            str(tenant.get("subscriptionId")) if tenant.get("subscriptionId") else None
        ),
        "createdAt": tenant["createdAt"],  # datetime object
        "updatedAt": tenant.get("updatedAt"),
    }


# -------------------------
# Create a new tenant
# -------------------------
async def create_tenant(request):
    # Convert Pydantic model to dictionary
    data = request.dict()

    # duplicate check: any tenant with same name that isn't soft-deleted
    existing = await db.tenants.find_one(
        {"tenantName": data["tenantName"], "isDeleted": {"$ne": True}}
    )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Tenant name already exists"
        )

    if data.get("subscriptionId"):
        _ensure_objectid(data["subscriptionId"], "subscriptionId")
        data["subscriptionId"] = ObjectId(data["subscriptionId"])
    else:
        data.pop("subscriptionId", None)

    # # validate subscriptionId
    # _ensure_objectid(data["subscriptionId"], "subscriptionId")

    # Convert HttpUrl to string if present
    if "tenantLogoUrl" in data and data["tenantLogoUrl"]:
        data["tenantLogoUrl"] = str(data["tenantLogoUrl"])

    data.update(
        {
            # "subscriptionId": ObjectId(data["subscriptionId"]),  # convert to ObjectId
            "createdAt": datetime.utcnow(),  # timestamp
            "status": "active",  # default status
            "updatedAt": None,
            "isDeleted": False,
        }
    )

    # Insert into MongoDB
    result = await db.tenants.insert_one(data)

    # Fetch the created tenant
    new_tenant = await db.tenants.find_one({"_id": result.inserted_id})

    return serialize_tenant(new_tenant)


# -------------------------
# Get all tenants (filter, search, sort, pagination)
# -------------------------
async def get_all_tenants(
    skip: int = 0,
    limit: int = 10,
    status: Optional[str] = None,
    search: Optional[str] = None,
    sort: Optional[str] = None,
):

    query: dict[str, Any] = {"isDeleted": False}

    # Filter by status
    if status:
        query["status"] = status

    # Case-insensitive search on tenantName & adminEmail
    if search:
        query["$or"] = [
            {"tenantName": {"$regex": search, "$options": "i"}},
            {"adminEmail": {"$regex": search, "$options": "i"}},
        ]

    cursor = db.tenants.find(query)

    # Sorting logic
    if sort:
        direction = -1 if sort.startswith("-") else 1
        field = sort.lstrip("-")
        cursor = cursor.sort(field, direction)

    # Pagination
    tenants = await cursor.skip(skip).limit(limit).to_list(length=limit)

    return [serialize_tenant(t) for t in tenants]


# -------------------------
# Get a single tenant by id
# -------------------------
async def get_tenant(_id: str):
    _ensure_objectid(_id, "tenantId")
    tenant = await db.tenants.find_one({"_id": ObjectId(_id), "isDeleted": False})
    return serialize_tenant(tenant) if tenant else None


# -------------------------
# Update tenant by id
# -------------------------
async def update_tenant(_id: str, updates: dict):

    if not updates:
        return None

    # only include fields with meaningful values
    safe_updates = {}

    for key, val in updates.items():
        if val is None:  # skip empty / null / ""
            continue

        if val == "":  # skip empty strings
            continue

        safe_updates[key] = val

    # if tenantLogoUrl present, convert HttpUrl to string
    if "tenantLogoUrl" in safe_updates:
        safe_updates["tenantLogoUrl"] = str(safe_updates["tenantLogoUrl"])

    # validate and convert subscriptionId if present
    if "subscriptionId" in safe_updates:
        _ensure_objectid(safe_updates["subscriptionId"], "subscriptionId")
        safe_updates["subscriptionId"] = ObjectId(safe_updates["subscriptionId"])

    safe_updates["updatedAt"] = datetime.utcnow()

    await db.tenants.update_one(
        {"_id": ObjectId(_id), "isDeleted": False}, {"$set": safe_updates}
    )

    tenant = await db.tenants.find_one({"_id": ObjectId(_id), "isDeleted": False})
    return serialize_tenant(tenant) if tenant else None


# -------------------------
# Delete tenant by id
# -------------------------
async def delete_tenant(_id):
    # soft delete
    result = await db.tenants.update_one(
        {"_id": ObjectId(_id)},
        {"$set": {"isDeleted": True, "updatedAt": datetime.utcnow()}},
    )
    return result.modified_count > 0
