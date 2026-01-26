from datetime import datetime
from bson import ObjectId
from fastapi import HTTPException
from app.db.database import db, users_collection
from app.schemas.teachers import TeacherCreate, TeacherUpdate, TeacherResponse
from app.schemas.assignments import AssignmentCreate
from app.schemas.quizzes import QuizCreate
from app.crud.quizzes import serialize_quiz
from app.utils.security import hash_password, verify_password
from app.utils.exceptions import not_found, bad_request

# ------------------ Helpers ------------------


def to_oid(id_str: str, field: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except Exception:
        raise HTTPException(400, f"Invalid {field}")


def serialize_teacher(t: dict) -> dict:
    """Convert Mongo teacher document -> API response format"""

    # Fix qualifications
    qualifications = []
    for q in t.get("qualifications", []):
        if isinstance(q, str):
            qualifications.append(q)
        elif isinstance(q, dict):
            qualifications.append(q.get("degree", ""))
        else:
            qualifications.append(str(q))

    # Fix subjects
    subjects = []
    for s in t.get("subjects", []):
        if isinstance(s, str):
            subjects.append(s)
        elif isinstance(s, dict):
            subjects.append(s.get("name", ""))
        else:
            subjects.append(str(s))

    # Fix assignedCourses
    assigned_courses = []
    for c in t.get("assignedCourses", []):
        assigned_courses.append(str(c))

    return {
        "id": str(t["_id"]),
        "fullName": t.get("fullName", ""),
        "email": t.get("email", ""),
        "profileImageURL": t.get("profileImageURL", ""),
        "assignedCourses": assigned_courses,
        "contactNo": t.get("contactNo"),
        "country": t.get("country"),
        "status": t.get("status", "active"),
        "role": t.get("role", "teacher"),
        "qualifications": qualifications,
        "subjects": subjects,
        "tenantId": str(t.get("tenantId", "")),
        "createdAt": t.get("createdAt"),
        "updatedAt": t.get("updatedAt"),
        "lastLogin": t.get("lastLogin"),
    }


def merge_user_data_teacher(teacher_doc, user_doc):
    if not teacher_doc:
        return None
    merged = {**teacher_doc}
    if user_doc:
        merged["fullName"] = user_doc.get("fullName", "")
        merged["email"] = user_doc.get("email", "")
        merged["profileImageURL"] = user_doc.get("profileImageURL", "")
        merged["contactNo"] = user_doc.get("contactNo")
        merged["country"] = user_doc.get("country")
        merged["status"] = user_doc.get("status", "active")
        merged["role"] = user_doc.get("role", "teacher")
        merged["createdAt"] = user_doc.get("createdAt")
        merged["lastLogin"] = user_doc.get("lastLogin")
    return serialize_teacher(merged)


async def create_teacher(data: TeacherCreate):
    d = data.dict()

    # 1. Create USER document
    user_doc = {
        "fullName": d["fullName"],
        "email": d["email"].lower(),
        "password": hash_password(d["password"]),
        "role": "teacher",
        "status": d.get("status", "active"),
        "profileImageURL": d.get("profileImageURL", ""),
        "contactNo": d.get("contactNo"),
        "country": d.get("country"),
        "tenantId": ObjectId(d["tenantId"]),
        "createdAt": datetime.utcnow(),
        "updatedAt": datetime.utcnow(),
        "lastLogin": None,
    }

    # 0. Check if tenant exists
    tenant = await db.tenants.find_one({"_id": ObjectId(d["tenantId"])})
    if not tenant:
        raise HTTPException(
            status_code=404, detail=f"Tenant not found with ID: {d['tenantId']}"
        )

    user_result = await users_collection.insert_one(user_doc)
    user_id = user_result.inserted_id

    # 2. Create TEACHER profile
    teacher_doc = {
        "userId": user_id,
        "tenantId": ObjectId(d["tenantId"]),
        "assignedCourses": [
            ObjectId(c) if ObjectId.is_valid(c) else c
            for c in d.get("assignedCourses", [])
        ],
        "qualifications": d.get("qualifications", []),
        "subjects": d.get("subjects", []),
        "createdAt": datetime.utcnow(),
        "updatedAt": datetime.utcnow(),
    }

    result = await db.teachers.insert_one(teacher_doc)

    # Return combined data
    return merge_user_data_teacher(teacher_doc, user_doc)


async def get_all_teachers():
    pipeline = [
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
    cursor = db.teachers.aggregate(pipeline)
    results = []
    async for doc in cursor:
        user_info = doc.pop("userDetails", {}) or {}
        results.append(merge_user_data_teacher(doc, user_info))
    return results


async def get_teacher(id: str):
    teacher = await db.teachers.find_one({"_id": to_oid(id, "teacherId")})
    if not teacher:
        return None
    user = await users_collection.find_one({"_id": teacher.get("userId")})
    return merge_user_data_teacher(teacher, user)


async def update_teacher(id: str, updates: dict):
    teacher = await db.teachers.find_one({"_id": to_oid(id, "teacherId")})
    if not teacher:
        return None

    user_id = teacher.get("userId")

    # 2. Clean data: Filter out empty strings for optional fields to avoid overwriting with empty
    # except for profileImageURL which might be cleared intentionally
    cleaned_updates = {}
    for k, v in updates.items():
        if v is None:
            continue
        if isinstance(v, str) and v.strip() == "" and k != "profileImageURL":
            continue
        cleaned_updates[k] = v

    if not cleaned_updates:
        return await get_teacher(id)

    cleaned_updates["updatedAt"] = datetime.utcnow()

    # Split fields between User and Teacher
    user_fields = [
        "fullName",
        "email",
        "profileImageURL",
        "contactNo",
        "country",
        "status",
    ]
    user_updates = {k: v for k, v in cleaned_updates.items() if k in user_fields}
    teacher_updates = {
        k: v
        for k, v in cleaned_updates.items()
        if k not in user_fields and k != "updatedAt"
    }

    if user_updates and user_id:
        user_updates["updatedAt"] = datetime.utcnow()
        await db.users.update_one({"_id": user_id}, {"$set": user_updates})

    if teacher_updates:
        if "tenantId" in teacher_updates:
            teacher_updates["tenantId"] = ObjectId(teacher_updates["tenantId"])
        if "assignedCourses" in teacher_updates:
            teacher_updates["assignedCourses"] = [
                ObjectId(c) if ObjectId.is_valid(c) else c
                for c in teacher_updates["assignedCourses"]
            ]

        teacher_updates["updatedAt"] = datetime.utcnow()
        await db.teachers.update_one(
            {"_id": to_oid(id, "teacherId")}, {"$set": teacher_updates}
        )

    return await get_teacher(id)


async def delete_teacher(id: str):
    teacher = await db.teachers.find_one({"_id": to_oid(id, "teacherId")})
    if not teacher:
        return False

    user_id = teacher.get("userId")

    # 1. Delete from teachers
    result = await db.teachers.delete_one({"_id": to_oid(id, "teacherId")})

    # 2. Delete from users
    if user_id:
        await users_collection.delete_one(
            {"_id": ObjectId(user_id) if not isinstance(user_id, ObjectId) else user_id}
        )

    return result.deleted_count > 0


async def change_password(id: str, old_password: str, new_password: str):
    teacher = await db.teachers.find_one({"_id": to_oid(id, "teacherId")})
    if not teacher:
        return None

    user_id = teacher.get("userId")
    if not user_id:
        return None

    user = await users_collection.find_one({"_id": user_id})
    if not user:
        return None

    from passlib.context import CryptContext

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    if not pwd_context.verify(old_password, user.get("password", "")):
        return "INCORRECT"

    hashed_new = hash_password(new_password)
    await users_collection.update_one(
        {"_id": user_id},
        {"$set": {"password": hashed_new, "updatedAt": datetime.utcnow()}},
    )
    return True


# ------------------ Assignments ------------------


async def serialize_assignment(a: dict) -> dict:
    return {
        "id": str(a["_id"]),
        "courseId": str(a["courseId"]),
        "teacherId": str(a["teacherId"]),
        "title": a.get("title", ""),
        "description": a.get("description", ""),
        "dueDate": a.get("dueDate"),
        "dueTime": a.get("dueTime"),
        "totalMarks": a.get("totalMarks"),
        "passingMarks": a.get("passingMarks"),
        "status": a.get("status", "active"),
        "fileUrl": a.get("fileUrl", ""),
        "allowedFormats": a.get("allowedFormats", []),
        "tenantId": str(a["tenantId"]),
        "uploadedAt": a.get("uploadedAt"),
        "updatedAt": a.get("updatedAt"),
    }


async def get_teacher_assignments_route(teacher_id: str):
    oid = to_oid(teacher_id, "teacherId")
    cursor = db.assignments.find({"teacherId": oid})
    return [serialize_assignment(a) async for a in cursor]


async def create_teacher_assignment_route(data: AssignmentCreate):
    d = data.dict()
    d["courseId"] = to_oid(d["courseId"], "courseId")
    d["teacherId"] = to_oid(d["teacherId"], "teacherId")
    d["tenantId"] = to_oid(d["tenantId"], "tenantId")
    d["uploadedAt"] = datetime.utcnow()
    d["updatedAt"] = datetime.utcnow()

    result = await db.assignments.insert_one(d)
    new_assignment = await db.assignments.find_one({"_id": result.inserted_id})
    return serialize_assignment(new_assignment)


# ------------------ Quizzes ------------------


async def get_teacher_quizzes_route(teacher_id: str):
    oid = to_oid(teacher_id, "teacherId")
    cursor = db.quizzes.find({"teacherId": oid})
    return [serialize_quiz(q) async for q in cursor]


async def create_teacher_quiz_route(data: QuizCreate):
    d = data.dict()
    d["courseId"] = to_oid(d["courseId"], "courseId")
    d["teacherId"] = to_oid(d["teacherId"], "teacherId")
    d["tenantId"] = to_oid(d["tenantId"], "tenantId")
    d["createdAt"] = datetime.utcnow()
    d["updatedAt"] = datetime.utcnow()

    result = await db.quizzes.insert_one(d)
    new_quiz = await db.quizzes.find_one({"_id": result.inserted_id})
    return serialize_quiz(new_quiz)


# ------------------ Dashboard / Students / Courses ------------------


async def get_teacher_dashboard(teacher_id: str):
    assignments = await get_teacher_assignments_route(teacher_id)
    quizzes = await get_teacher_quizzes_route(teacher_id)
    courses = [
        c async for c in db.courses.find({"teacherId": to_oid(teacher_id, "teacherId")})
    ]

    return {
        "totalAssignments": len(assignments),
        "totalQuizzes": len(quizzes),
        "totalCourses": len(courses),
    }


async def get_teacher_students(teacher_id: str):
    cursor = db.students.find({"teacherId": to_oid(teacher_id, "teacherId")})
    return [s async for s in cursor]


# async def get_teacher_courses(teacher_id: str):
#     cursor = db.courses.find({"teacherId": to_oid(teacher_id, "teacherId")})
#     return [c async for c in cursor]


async def get_teacher_courses(teacher_id: str):
    # Convert teacher_id to ObjectId
    teacher_oid = to_oid(teacher_id, "teacherId")

    # Query courses where teacherId matches
    cursor = db.courses.find({"teacherId": teacher_oid})

    courses = []
    async for c in cursor:
        courses.append(
            {
                "id": str(c["_id"]),
                "title": c.get("title", ""),
                "description": c.get("description", ""),
                "category": c.get("category", ""),
                "status": c.get("status", ""),
                "courseCode": c.get("courseCode", ""),
                "duration": c.get("duration", ""),
                "thumbnailUrl": c.get("thumbnailUrl", ""),
                "modules": c.get("modules", []),
                "teacherId": str(c.get("teacherId", "")),
                "tenantId": str(c.get("tenantId", "")),
                "enrolledStudents": c.get("enrolledStudents", 0),
                "createdAt": c.get("createdAt"),
                "updatedAt": c.get("updatedAt"),
            }
        )

    return courses


async def get_teacher_by_user(user_id: str):
    if isinstance(user_id, str):
        user_id = ObjectId(user_id)

    teacher = await db.teachers.find_one({"userId": user_id})
    if not teacher:
        return None

    user = await users_collection.find_one({"_id": user_id})
    return merge_user_data_teacher(teacher, user)


# ---------------------------------------PROFILE Functions-------------------------------------------------------------


async def update_teacher_profile(user_id: str, updates: dict):
    if isinstance(user_id, str):
        user_id = ObjectId(user_id)

    teacher = await db.teachers.find_one({"userId": user_id})
    if not teacher:
        return None

    # Separation logic similar to generic update
    cleaned_updates = {}
    for k, v in updates.items():
        if v is None:
            continue
        # if isinstance(v, str) and v.strip() == "" and k != "profileImageURL": continue
        cleaned_updates[k] = v

    cleaned_updates["updatedAt"] = datetime.utcnow()

    user_fields = [
        "fullName",
        "email",
        "profileImageURL",
        "contactNo",
        "country",
        "status",
    ]
    user_updates = {k: v for k, v in cleaned_updates.items() if k in user_fields}
    teacher_updates = {
        k: v
        for k, v in cleaned_updates.items()
        if k not in user_fields and k != "updatedAt"
    }

    if user_updates:
        user_updates["updatedAt"] = datetime.utcnow()
        await users_collection.update_one({"_id": user_id}, {"$set": user_updates})

    if teacher_updates:
        teacher_updates["updatedAt"] = datetime.utcnow()
        await db.teachers.update_one({"userId": user_id}, {"$set": teacher_updates})

    # Fetch fresh
    teacher = await db.teachers.find_one({"userId": user_id})
    user = await users_collection.find_one({"_id": user_id})
    return merge_user_data_teacher(teacher, user)


async def get_teacher_me(current_user: dict):
    teacher = await db.teachers.find_one({"userId": ObjectId(current_user["user_id"])})
    if not teacher:
        not_found("Teacher profile")

    user = await users_collection.find_one({"_id": teacher["userId"]})
    return merge_user_data_teacher(teacher, user)


async def update_teacher_me(current_user: dict, data: TeacherUpdate):
    return await update_teacher_profile(
        user_id=current_user["user_id"], updates=data.dict(exclude_unset=True)
    )


async def change_teacher_me_password(
    current_user: dict,
    old_password: str,
    new_password: str,
):
    # 1. Fetch teacher profile
    teacher = await db.teachers.find_one({"userId": ObjectId(current_user["user_id"])})
    if not teacher:
        not_found("Teacher")

    user_id = teacher.get("userId")
    if not user_id:
        not_found("Associated user for teacher")

    # 2. Fetch user document (SOURCE OF TRUTH)
    user = await users_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        not_found("User")

    # 3. Verify old password
    if not verify_password(old_password, user["password"]):
        bad_request("Old password is incorrect")

    # 4. Prevent password reuse
    if verify_password(new_password, user["password"]):
        bad_request("New password must be different from old password")

    # 5. Update password in users collection
    await users_collection.update_one(
        {"_id": ObjectId(user_id)},
        {
            "$set": {
                "password": hash_password(new_password),
                "updatedAt": datetime.utcnow(),
            }
        },
    )

    # 6. Touch teacher profile timestamp
    await db.teachers.update_one(
        {"_id": teacher["_id"]},
        {"$set": {"updatedAt": datetime.utcnow()}},
    )

    return {
        "message": "Password updated successfully",
        "updatedAt": datetime.utcnow(),
    }
