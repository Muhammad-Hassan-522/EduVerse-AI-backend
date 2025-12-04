from app.db.database import db
from app.schemas.teachers import TeacherCreate
from passlib.context import CryptContext
from bson import ObjectId
from datetime import datetime

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ------------------ Helper Functions ------------------

def serialize_teacher(t):
    return {
        "id": str(t["_id"]),
        "fullName": t["fullName"],
        "email": t["email"],
        "profileImageURL": t.get("profileImageURL", ""),
        "assignedCourses": [str(c) for c in t.get("assignedCourses", [])],
        "contactNo": t.get("contactNo"),
        "country": t.get("country"),
        "status": t.get("status", "active"),
        "role": t.get("role", "teacher"),
        "createdAt": t.get("createdAt"),
        "updatedAt": t.get("updatedAt"),
        "lastLogin": t.get("lastLogin"),
        "qualifications": t.get("qualifications", []),
        "subjects": t.get("subjects", []),
        "tenantId": str(t["tenantId"]),
    }

def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)

def clean_update_data(data: dict):
    """Remove None/empty values and add updatedAt"""
    cleaned = {k: v for k, v in data.items() if v not in [None, "", [], {}]}
    if cleaned:
        cleaned["updatedAt"] = datetime.utcnow()
    return cleaned

# ------------------ CRUD ------------------

async def create_teacher(data: TeacherCreate):
    d = data.dict()
    d.update({
        "password": hash_password(d["password"]),
        "assignedCourses": [ObjectId(c) for c in d.get("assignedCourses", [])],
        "tenantId": ObjectId(d["tenantId"]),
        "createdAt": datetime.utcnow(),
        "updatedAt": datetime.utcnow(),
        "lastLogin": None
    })
    result = await db.teachers.insert_one(d)
    new_teacher = await db.teachers.find_one({"_id": result.inserted_id})
    return serialize_teacher(new_teacher)

async def get_all_teachers():
    cursor = db.teachers.find().sort("createdAt", -1)
    return [serialize_teacher(t) async for t in cursor]

async def get_teacher(id: str):
    t = await db.teachers.find_one({"_id": ObjectId(id)})
    return serialize_teacher(t) if t else None

async def update_teacher(id: str, updates: dict):
    t = await db.teachers.find_one({"_id": ObjectId(id)})
    if not t:
        return None
    cleaned = clean_update_data(updates)
    if cleaned:
        await db.teachers.update_one({"_id": ObjectId(id)}, {"$set": cleaned})
    new_t = await db.teachers.find_one({"_id": ObjectId(id)})
    return serialize_teacher(new_t)

async def delete_teacher(id: str):
    t = await db.teachers.find_one({"_id": ObjectId(id)})
    if not t:
        return None
    await db.teachers.delete_one({"_id": ObjectId(id)})
    return True

async def change_password(id: str, old_password: str, new_password: str):
    t = await db.teachers.find_one({"_id": ObjectId(id)})
    if not t:
        return None
    if not verify_password(old_password, t["password"]):
        return "INCORRECT"
    await db.teachers.update_one(
        {"_id": ObjectId(id)},
        {"$set": {"password": hash_password(new_password), "updatedAt": datetime.utcnow()}}
    )
    return True

# ------------------ Teacher Dashboard & Students ------------------

async def get_teacher_students(id: str):
    students_cursor = db.students.find({"assignedTeacherId": ObjectId(id)})
    students = []
    async for s in students_cursor:
        avatar = "".join([x[0].upper() for x in s.get("fullName", "").split()][:2])
        students.append({
            "id": str(s["_id"]),
            "name": s.get("fullName", ""),
            "email": s.get("email", ""),
            "class": s.get("className"),
            "rollNo": s.get("rollNo"),
            "status": s.get("status", "Inactive"),
            "avatar": avatar,
        })
    return students

async def get_teacher_dashboard(id: str):
    students_count = await db.students.count_documents({"assignedTeacherId": ObjectId(id)})
    courses_count = await db.courses.count_documents({"teacherId": ObjectId(id)})
    return {
        "totalStudents": students_count,
        "totalCourses": courses_count,
        "totalAssignments": 0,
        "totalQuizzes": 0
    }
