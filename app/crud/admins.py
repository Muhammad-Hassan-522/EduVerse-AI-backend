from app.db.database import db, users_collection
from app.schemas.admins import AdminCreate, AdminUpdateProfile
from passlib.context import CryptContext
from bson import ObjectId
from datetime import datetime

from app.utils.exceptions import not_found, forbidden, bad_request
from app.utils.security import hash_password, verify_password

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ------------------ Helper Functions ------------------


def serialize_admin(admin: dict) -> dict:
    """Return admin data in frontend-friendly format."""
    return {
        "id": str(admin["_id"]),
        "fullName": admin.get("fullName", ""),
        "email": admin.get("email", ""),
        "country": admin.get("country"),
        "contactNo": admin.get("contactNo"),
        "profileImageURL": admin.get("profileImageURL", ""),
        "status": admin.get("status", "active"),
        "role": admin.get("role", "admin"),
        "createdAt": admin.get("createdAt"),
        "updatedAt": admin.get("updatedAt"),
    }


def merge_user_data_admin(admin_doc, user_doc):
    if not admin_doc:
        return None
    merged = {**admin_doc}
    if user_doc:
        merged["fullName"] = user_doc.get("fullName", "")
        merged["email"] = user_doc.get("email", "")
        merged["profileImageURL"] = user_doc.get("profileImageURL", "")
        merged["contactNo"] = user_doc.get("contactNo")
        merged["country"] = user_doc.get("country")
        merged["status"] = user_doc.get("status", "active")
        merged["role"] = user_doc.get("role", "admin")
        merged["createdAt"] = user_doc.get("createdAt")
    return serialize_admin(merged)


# def hash_password(password: str) -> str:
#     return pwd_context.hash(password)


# def verify_password(plain_password: str, hashed_password: str) -> bool:
#     return pwd_context.verify(plain_password, hashed_password)


# def hash_password(password: str) -> str:
#     password_bytes = password.encode("utf-8")
#     if len(password_bytes) > 70:
#         password = password_bytes[:70].decode("utf-8", "ignore")
#     return pwd_context.hash(password)


def serialize_teacher(teacher: dict) -> dict:
    return {
        "id": str(teacher["_id"]),
        "fullName": teacher.get("fullName", ""),
        "email": teacher.get("email", ""),
        "profileImageURL": teacher.get("profileImageURL", ""),
        "assignedCourses": [
            str(c) for c in teacher.get("assignedCourses", [])
        ],  # FIXED HERE
        "contactNo": teacher.get("contactNo", ""),
        "country": teacher.get("country", ""),
        "status": (
            "Active"
            if str(teacher.get("status", "")).lower() == "active"
            else "Inactive"
        ),
        "role": teacher.get("role", "teacher"),
        "qualifications": teacher.get("qualifications", []),
        "subjects": teacher.get("subjects", []),
        "tenantId": teacher.get("tenantId", ""),
        "createdAt": teacher.get("createdAt"),
        "updatedAt": teacher.get("updatedAt"),
        "lastLogin": teacher.get("lastLogin", None),
    }


def serialize_student(student: dict) -> dict:
    return {
        "id": str(student["_id"]),
        "name": student.get("fullName", ""),
        "email": student.get("email", ""),
        "class": student.get("className"),
        "rollNo": student.get("rollNo"),
        "status": student.get("status", "Inactive"),
    }


def serialize_course(course: dict, teacher_name: str = "") -> dict:
    return {
        "id": str(course["_id"]),
        "title": course.get("title", ""),
        "code": course.get("courseCode", ""),
        "instructor": teacher_name,
        "status": course.get("status", "Inactive"),
    }


def clean_update_data(data: dict) -> dict:
    """Remove None values from dict and add updatedAt"""
    update_data = {k: v for k, v in data.items() if v is not None}
    if update_data:
        update_data["updatedAt"] = datetime.utcnow()
    return update_data


# ------------------ Admin Functions ------------------


async def get_admin_by_email(email: str):
    user = await users_collection.find_one({"email": email, "role": "admin"})
    if not user:
        return None
    admin = await db.admins.find_one({"userId": user["_id"]})
    return merge_user_data_admin(admin, user)


async def create_admin(admin: AdminCreate):
    existing = await users_collection.find_one({"email": admin.email})
    if existing:
        raise ValueError("Email already registered")
    if admin.password != admin.confirmPassword:
        raise ValueError("Passwords do not match")

    hashed_password = hash_password(admin.password)
    full_name = f"{admin.firstName} {admin.lastName}"

    # 1. Create USER document
    user_doc = {
        "fullName": full_name,
        "email": admin.email,
        "password": hashed_password,
        "role": "admin",
        "status": "active",
        "profileImageURL": "",
        "contactNo": admin.phone,
        "country": admin.country,
        "createdAt": datetime.utcnow(),
        "updatedAt": datetime.utcnow(),
        "lastLogin": None,
    }
    user_result = await users_collection.insert_one(user_doc)
    user_id = user_result.inserted_id

    # 2. Create ADMIN profile
    admin_doc = {
        "userId": user_id,
        "tenantId": user_doc.get("tenantId"),
        "createdAt": datetime.utcnow(),
        "updatedAt": datetime.utcnow(),
    }
    await db.admins.insert_one(admin_doc)

    return merge_user_data_admin(admin_doc, user_doc)


async def create_admin_profile(user_id: str, tenant_id: str = None):
    """Create only the admin profile for an existing user."""
    admin_doc = {
        "userId": ObjectId(user_id) if isinstance(user_id, str) else user_id,
        "tenantId": (
            ObjectId(tenant_id)
            if tenant_id and isinstance(tenant_id, str)
            else tenant_id
        ),
        "createdAt": datetime.utcnow(),
        "updatedAt": datetime.utcnow(),
    }
    await db.admins.insert_one(admin_doc)
    return admin_doc


# async def verify_password(plain_password, hashed_password):
#     return pwd_context.verify(plain_password, hashed_password)


# async def update_admin_password(admin_id: str, old_password: str, new_password: str):
#     admin = await db.admins.find_one({"_id": ObjectId(admin_id)})
#     if not admin:
#         raise ValueError("Admin not found")

#     user_id = admin.get("userId")
#     if not user_id:
#         raise ValueError("User reference not found")

#     user = await users_collection.find_one({"_id": user_id})
#     if not user:
#         raise ValueError("User not found")

#     if not pwd_context.verify(old_password, user["password"]):
#         raise ValueError("Old password is incorrect")

#     hashed_password = hash_password(new_password)
#     await users_collection.update_one(
#         {"_id": user_id},
#         {"$set": {"password": hashed_password, "updatedAt": datetime.utcnow()}},
#     )

#     await db.admins.update_one(
#         {"_id": ObjectId(admin_id)}, {"$set": {"updatedAt": datetime.utcnow()}}
#     )

#     admin = await db.admins.find_one({"_id": ObjectId(admin_id)})
#     user = await users_collection.find_one({"_id": user_id})
#     return merge_user_data_admin(admin, user)


# ------------------ Dashboard Functions (Lazy Imports & Serialization) ------------------


async def get_all_courses():
    courses_cursor = db.courses.find({})
    courses = []
    async for course in courses_cursor:
        teacher_name = ""
        teacher_id = course.get("teacherId")
        try:
            teacher_doc = await db.teachers.find_one({"_id": ObjectId(teacher_id)})
            if teacher_doc:
                teacher_name = teacher_doc.get("fullName", "")
        except:
            pass
        courses.append(serialize_course(course, teacher_name))
    return courses


async def get_all_teachers():
    from app.crud.teachers import get_all_teachers as fetch_all_teachers

    raw_teachers = await fetch_all_teachers()
    return raw_teachers  # Already serialized in teachers.py


async def get_all_students():
    from app.crud.students import list_students as fetch_all_students

    raw_students = await fetch_all_students()
    students = []
    for s in raw_students:
        students.append(
            {
                "id": str(s["_id"]),
                "name": s.get("fullName", ""),
                "email": s.get("email", ""),
                "class": s.get("className"),
                "rollNo": s.get("rollNo"),
                "status": s.get("status", "Inactive"),
            }
        )
    return students


# ------------------PROFILE Functions  ------------------


async def get_admin_me(current_user: dict):
    admin = await db.admins.find_one({"userId": ObjectId(current_user["user_id"])})
    if not admin:
        not_found("Admin profile")

    user = await users_collection.find_one({"_id": admin["userId"]})
    return merge_user_data_admin(admin, user)


async def update_admin_me(current_user: dict, data: AdminUpdateProfile):
    admin = await db.admins.find_one({"userId": ObjectId(current_user["user_id"])})
    if not admin:
        not_found("Admin profile")

    return await update_admin_profile(admin_id=str(admin["_id"]), data=data)


async def update_admin_profile(admin_id: str, data: AdminUpdateProfile):
    admin = await db.admins.find_one({"_id": ObjectId(admin_id)})
    if not admin:
        return None

    user_id = admin.get("userId")
    update_data = clean_update_data(data.dict())
    if not update_data:
        return await merge_user_data_admin(
            admin, await users_collection.find_one({"_id": user_id})
        )

    if user_id:
        await users_collection.update_one({"_id": user_id}, {"$set": update_data})

    await db.admins.update_one(
        {"_id": ObjectId(admin_id)}, {"$set": {"updatedAt": datetime.utcnow()}}
    )

    admin = await db.admins.find_one({"_id": ObjectId(admin_id)})
    user = await users_collection.find_one({"_id": user_id})
    return merge_user_data_admin(admin, user)


# async def change_admin_me_password(
#     current_user: dict,
#     old_password: str,
#     new_password: str,
# ):
#     # 1. Fetch admin profile
#     admin = await db.admins.find_one({"userId": ObjectId(current_user["user_id"])})
#     if not admin:
#         not_found("Admin profile")

#     user_id = admin.get("userId")
#     if not user_id:
#         not_found("Associated user")

#     # 2. Fetch user document (SOURCE OF TRUTH for password)
#     user = await db.users.find_one({"_id": ObjectId(user_id)})
#     if not user:
#         not_found("User")

#     # 3. Verify old password (same logic as login)
#     if not verify_password(old_password, user["password"]):
#         bad_request("Old password is incorrect")

#     # 4. Prevent reusing the same password
#     if verify_password(new_password, user["password"]):
#         bad_request("New password must be different from old password")

#     # 5. Update password
#     await db.users.update_one(
#         {"_id": ObjectId(user_id)},
#         {
#             "$set": {
#                 "password": hash_password(new_password),
#                 "updatedAt": datetime.utcnow(),
#             }
#         },
#     )

#     # 6. Touch admin profile timestamp
#     await db.admins.update_one(
#         {"_id": admin["_id"]},
#         {"$set": {"updatedAt": datetime.utcnow()}},
#     )

#     return {
#         "message": "Password updated successfully",
#         "updatedAt": datetime.utcnow(),
#     }


from datetime import datetime
from bson import ObjectId
from app.utils.exceptions import not_found, bad_request
from app.utils.security import hash_password, verify_password
from app.db.database import users_collection, db


async def change_admin_me_password(
    current_user: dict,
    old_password: str,
    new_password: str,
):
    # 1. Fetch USER document (single source of truth)
    user = await users_collection.find_one(
        {"_id": ObjectId(current_user["user_id"]), "role": "admin"}
    )
    if not user:
        not_found("User")

    # 2. Verify old password
    if not verify_password(old_password, user["password"]):
        bad_request("Old password is incorrect")

    # 3. Prevent password reuse
    if verify_password(new_password, user["password"]):
        bad_request("New password must be different from old password")

    # 4. Update password in USERS collection
    await users_collection.update_one(
        {"_id": user["_id"]},
        {
            "$set": {
                "password": hash_password(new_password),
                "updatedAt": datetime.utcnow(),
            }
        },
    )

    # 5. Touch ADMIN profile timestamp (if profile exists)
    await db.admins.update_one(
        {"userId": user["_id"]},
        {"$set": {"updatedAt": datetime.utcnow()}},
    )

    return {
        "message": "Password updated successfully",
        "updatedAt": datetime.utcnow(),
    }
