from bson import ObjectId
from datetime import datetime
from app.db.database import db
from app.utils.security import hash_password, verify_password


def serialize_user(u: dict):
    return {
        "id": str(u["_id"]),
        "fullName": u["fullName"],
        "email": u["email"],
        "profileImageURL": u.get("profileImageURL"),
        "contactNo": u.get("contactNo"),
        "country": u.get("country"),
        "role": u["role"],
        "status": u["status"],
        "tenantId": str(u["tenantId"]) if u.get("tenantId") else None,
        "studentId": u.get("studentId"),
        "teacherId": u.get("teacherId"),
        "adminId": u.get("adminId"),
        "createdAt": u.get("createdAt"),
        "updatedAt": u["updatedAt"],
        "lastLogin": u.get("lastLogin"),
    }


async def get_user_by_email(email: str):
    return await db.users.find_one({"email": email.lower()})


async def create_user(data: dict):
    data["email"] = data["email"].lower()
    data["password"] = hash_password(data["password"])
    data["createdAt"] = datetime.utcnow()
    data["updatedAt"] = datetime.utcnow()
    data["lastLogin"] = None

    if data.get("tenantId"):
        data["tenantId"] = ObjectId(data["tenantId"])

    result = await db.users.insert_one(data)
    new_user = await db.users.find_one({"_id": result.inserted_id})
    return serialize_user(new_user)


async def verify_user(email: str, password: str):
    u = await get_user_by_email(email)
    if not u or not verify_password(password, u["password"]):
        return None

    # After verifying, fetch the role-specific doc to get the tenant_id and role-specific ID
    user_id = u["_id"]
    role = u["role"]
    tenant_id = u.get("tenantId")  # Start with tenantId from users collection
    role_doc = None

    if role == "teacher":
        role_doc = await db.teachers.find_one({"userId": user_id})
    elif role == "student":
        role_doc = await db.students.find_one({"userId": user_id})
    elif role == "admin":
        role_doc = await db.admins.find_one({"userId": user_id})

    # If the role-specific document has a tenantId, it takes precedence
    if role_doc and role_doc.get("tenantId"):
        tenant_id = role_doc.get("tenantId")

    # Add tenantId and role-specific ID to the user object before serializing
    u["tenantId"] = tenant_id
    if role == "teacher" and role_doc:
        u["teacherId"] = str(role_doc["_id"])
    elif role == "student" and role_doc:
        u["studentId"] = str(role_doc["_id"])
    elif role == "admin" and role_doc:
        u["adminId"] = str(role_doc["_id"])

    return serialize_user(u)


async def update_last_login(user_id: str):
    await db.users.update_one(
        {"_id": ObjectId(user_id)}, {"$set": {"lastLogin": datetime.utcnow()}}
    )
