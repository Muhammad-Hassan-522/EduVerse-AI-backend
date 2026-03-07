from datetime import datetime
from bson import ObjectId
from fastapi import HTTPException
from app.schemas.students import StudentCreate, StudentUpdate
from app.utils.mongo import fix_object_ids
from app.utils.security import hash_password
from app.db.database import students_collection as COLLECTION
from app.db.database import courses_collection, users_collection, db
from app.db.database import student_performance_collection


# ------------------ Helper: Merge User & Student Data ------------------ #
def merge_user_data(student_doc, user_doc):
    if not student_doc:
        return None

    # Base student data
    merged = {**student_doc}

    if user_doc:
        # Merge fields from User
        merged["fullName"] = user_doc.get("fullName", "")
        merged["email"] = user_doc.get("email", "")
        merged["password"] = user_doc.get("password")
        merged["role"] = user_doc.get("role", "student")
        merged["status"] = user_doc.get("status", "active")
        merged["createdAt"] = user_doc.get("createdAt")
        merged["updatedAt"] = user_doc.get("updatedAt")
        merged["lastLogin"] = user_doc.get("lastLogin")
        merged["profileImageURL"] = user_doc.get("profileImageURL", "")

    merged = fix_object_ids(merged)

    # Convert MongoDB _id → id
    if "_id" in merged:
        merged["id"] = str(merged["_id"])
        del merged["_id"]

    return merged


# ---------------------------------------------------------------------------
# Create Student (Multi-Tenant)
# ---------------------------------------------------------------------------
async def create_student(student: StudentCreate, tenant_id: str):
    data = student.dict()

    # Check if user exists
    existing_user = await users_collection.find_one({"email": data["email"]})
    if existing_user:
        raise HTTPException(
            status_code=400, detail="User with this email already exists"
        )

    # 0. Check if tenant exists
    tenant = await db.tenants.find_one({"_id": ObjectId(tenant_id)})
    if not tenant:
        raise HTTPException(
            status_code=404, detail=f"Tenant not found with ID: {tenant_id}"
        )

    # 1. Create USER document
    user_doc = {
        "fullName": data["fullName"],
        "email": data["email"].lower(),
        "password": hash_password(data["password"]),
        "role": "student",
        "status": data.get("status", "active"),
        "profileImageURL": data.get("profileImageURL", ""),
        "contactNo": data.get("contactNo"),
        "country": data.get("country"),
        "tenantId": ObjectId(data.get("tenantId") or tenant_id),
        "createdAt": datetime.utcnow(),
        "updatedAt": datetime.utcnow(),
        "lastLogin": None,
    }

    user_result = await users_collection.insert_one(user_doc)
    user_id = user_result.inserted_id

    # 2. Create STUDENT document (Profile)
    student_doc = {
        "userId": user_id,
        "tenantId": ObjectId(tenant_id),
        "enrolledCourses": [],
        "completedCourses": [],
        "createdAt": datetime.utcnow(),
        "updatedAt": datetime.utcnow(),
    }

    result = await COLLECTION.insert_one(student_doc)

    performance_doc = {
        "tenantId": ObjectId(tenant_id),
        "studentId": result.inserted_id,
        "userId": user_id,
        "studentName": data["fullName"],
        "totalPoints": 0,
        "pointsThisWeek": 0,
        "xp": 0,
        "level": 1,
        "xpToNextLevel": 300,
        "badges": [],
        "certificates": [],
        "weeklyStudyTime": [],
        "courseStats": [],
        "createdAt": datetime.utcnow(),
        "updatedAt": datetime.utcnow(),
    }

    await student_performance_collection.insert_one(performance_doc)

    new_student_combined = {
        "_id": result.inserted_id,
        "tenantId": ObjectId(tenant_id),
        "fullName": user_doc["fullName"],
        "email": user_doc["email"],
        "password": user_doc["password"],
        "profileImageURL": user_doc["profileImageURL"],
        "contactNo": user_doc["contactNo"],
        "country": user_doc["country"],
        "status": user_doc["status"],
        "role": user_doc["role"],
        "enrolledCourses": student_doc["enrolledCourses"],
        "completedCourses": student_doc["completedCourses"],
        "createdAt": user_doc["createdAt"],
        "updatedAt": user_doc["updatedAt"],
        "lastLogin": user_doc["lastLogin"],
    }

    return fix_object_ids(new_student_combined)


# ---------------------------------------------------------------------------
# Login (Email only — tenant irrelevant)
# ---------------------------------------------------------------------------
async def get_student_by_email(email: str):
    # Now we must find in USERS first
    user = await users_collection.find_one({"email": email, "role": "student"})
    if not user:
        return None

    # Then find the corresponding STUDENT profile
    student = await COLLECTION.find_one({"userId": user["_id"]})
    if not student:
        return None

    return merge_user_data(student, user)


# ---------------------------------------------------------------------------
# Get Student by ID + Tenant
# ---------------------------------------------------------------------------
async def get_student_by_id(student_id: str, tenantId: str):
    # student_id here is the ID in STUDENTS collection
    student = await COLLECTION.find_one(
        {"_id": ObjectId(student_id), "tenantId": ObjectId(tenantId)}
    )

    if not student:
        return None

    user = await users_collection.find_one({"_id": student.get("userId")})
    return merge_user_data(student, user)


# ---------------------------------------------------------------------------
# List All Students (Optional Tenant)
# ---------------------------------------------------------------------------
async def list_students(tenantId: str = None):
    # Use aggregation to join
    pipeline = []

    if tenantId:
        pipeline.append({"$match": {"tenantId": ObjectId(tenantId)}})

    pipeline.extend(
        [
            {
                "$lookup": {
                    "from": "users",
                    "localField": "userId",
                    "foreignField": "_id",
                    "as": "userDetails",
                }
            },
            {"$unwind": {"path": "$userDetails", "preserveNullAndEmptyArrays": True}},
        ]
    )

    students_cursor = COLLECTION.aggregate(pipeline)
    results = []
    async for doc in students_cursor:
        user_info = doc.pop("userDetails", {}) or {}
        # Merge
        merged = {**doc, **user_info}

        # Explicit mapping:
        merged_obj = {
            "_id": doc["_id"],
            "tenantId": doc.get("tenantId"),
            "fullName": user_info.get("fullName", ""),
            "email": user_info.get("email", ""),
            "role": user_info.get("role", "student"),
            "status": user_info.get("status", "active"),
            "profileImageURL": user_info.get("profileImageURL", ""),
            "contactNo": user_info.get("contactNo"),
            "country": user_info.get("country"),
            "enrolledCourses": doc.get("enrolledCourses", []),
            "completedCourses": doc.get("completedCourses", []),
            "createdAt": user_info.get("createdAt"),  # Use User's createdAt
            "updatedAt": user_info.get("updatedAt"),
            "lastLogin": user_info.get("lastLogin"),
        }
        results.append(fix_object_ids(merged_obj))

    return results


# ---------------------------------------------------------------------------
# Delete Student
# ---------------------------------------------------------------------------
async def delete_student(student_id: str, tenant_id: str):

    # STEP 1 — Fetch student before deleting
    student = await COLLECTION.find_one(
        {"_id": ObjectId(student_id), "tenantId": ObjectId(tenant_id)}
    )

    if not student:
        return False

    # STEP 2 — Decrease enrolledStudents count for each course
    enrolled_courses = student.get("enrolledCourses", [])

    for course_id in enrolled_courses:
        if ObjectId.is_valid(course_id):
            await courses_collection.update_one(
                {"_id": ObjectId(course_id)}, {"$inc": {"enrolledStudents": -1}}
            )

    # STEP 3 — Delete the student from the STUDENTS collection
    result = await COLLECTION.delete_one(
        {"_id": ObjectId(student_id), "tenantId": ObjectId(tenant_id)}
    )

    # If student was not deleted → stop
    if result.deleted_count == 0:
        return False

    # STEP 3.5 — Delete User (Cascading Delete for Students)
    if student.get("userId"):
        user_id = student["userId"]
        await users_collection.delete_one(
            {"_id": ObjectId(user_id) if not isinstance(user_id, ObjectId) else user_id}
        )

    # STEP 4 — Delete student performance document for this student + tenant
    await student_performance_collection.delete_one(
        {"studentId": ObjectId(student_id), "tenantId": ObjectId(tenant_id)}
    )

    return True


# ---------------------------------------------------------------------------
# Get Student by User ID (Helper)
# ---------------------------------------------------------------------------
async def get_student_by_user(user_id: str):
    if isinstance(user_id, str):
        user_id = ObjectId(user_id)

    student = await COLLECTION.find_one({"userId": user_id})
    if not student:
        return None

    user = await users_collection.find_one({"_id": user_id})
    return merge_user_data(student, user)


from app.utils.exceptions import not_found, bad_request
from app.utils.security import hash_password, verify_password

# ---------------------------------------PROFILE FUnctions------------------------------------


async def get_student_me(current_user: dict):
    student = await COLLECTION.find_one({"userId": ObjectId(current_user["user_id"])})
    if not student:
        not_found("Student profile")

    user = await users_collection.find_one({"_id": student["userId"]})
    return merge_user_data(student, user)


async def update_student_me(current_user: dict, data: StudentUpdate):
    student = await COLLECTION.find_one({"userId": ObjectId(current_user["user_id"])})
    if not student:
        not_found("Student profile")

    return await update_student(
        student_id=str(student["_id"]), tenantId=str(student["tenantId"]), update=data
    )


async def update_student(student_id: str, tenantId: str, update: StudentUpdate):
    # 1. Find student
    if not ObjectId.is_valid(student_id) or not ObjectId.is_valid(tenantId):
        return None

    student = await COLLECTION.find_one(
        {"_id": ObjectId(student_id), "tenantId": ObjectId(tenantId)}
    )

    if not student:
        return None

    user_id = student.get("userId")
    if not user_id:
        return None

    # Exclude unset fields (don't overwrite with nulls)
    update_dict = update.dict(exclude_unset=True)

    # 2. Clean data: Filter out empty strings for optional fields to avoid overwriting with empty
    # except for profileImageURL which might be cleared intentionally
    update_data = {}
    for k, v in update_dict.items():
        if v is None:
            continue
        if isinstance(v, str) and v.strip() == "" and k != "profileImageURL":
            continue
        update_data[k] = v

    if not update_data:
        return await get_student_by_id(student_id, tenantId)

    # Normalize data
    if "email" in update_data:
        update_data["email"] = update_data["email"].lower()

    update_data["updatedAt"] = datetime.utcnow()

    #  Update USERS collection
    await db.users.update_one({"_id": user_id}, {"$set": update_data})

    #  Update STUDENT collection timestamp
    await COLLECTION.update_one(
        {"_id": ObjectId(student_id)}, {"$set": {"updatedAt": datetime.utcnow()}}
    )

    #  ALSO update STUDENT PERFORMANCE if name changes
    if "fullName" in update_data:
        await student_performance_collection.update_one(
            {"studentId": ObjectId(student_id), "tenantId": ObjectId(tenantId)},
            {
                "$set": {
                    "studentName": update_data["fullName"],
                    "updatedAt": datetime.utcnow(),
                }
            },
        )

    return await get_student_by_id(student_id, tenantId)


async def change_student_me_password(
    current_user: dict,
    old_password: str,
    new_password: str,
):
    # 1. Fetch user document (students use users directly)
    user = await users_collection.find_one({"_id": ObjectId(current_user["user_id"])})
    if not user:
        not_found("User")

    # 2. Verify old password (same logic as login)
    if not verify_password(old_password, user["password"]):
        bad_request("Old password is incorrect")

    # 3. Prevent password reuse
    if verify_password(new_password, user["password"]):
        bad_request("New password must be different from old password")

    # 4. Update password
    await users_collection.update_one(
        {"_id": user["_id"]},
        {
            "$set": {
                "password": hash_password(new_password),
                "updatedAt": datetime.utcnow(),
            }
        },
    )

    return {
        "message": "Password updated successfully",
        "updatedAt": datetime.utcnow(),
    }
