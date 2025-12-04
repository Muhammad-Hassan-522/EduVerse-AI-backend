from app.db.database import db
from app.schemas.admins import AdminCreate, AdminUpdateProfile
from passlib.context import CryptContext
from bson import ObjectId
from datetime import datetime

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
        "createdAt": admin.get("createdAt"),
        "updatedAt": admin.get("updatedAt")
    }

def serialize_teacher(teacher: dict) -> dict:
    return {
        "id": str(teacher["_id"]),
        "name": teacher.get("fullName", ""),
        "email": teacher.get("email", ""),
        "assignedCourses": teacher.get("assignedCourses", []),
        "totalStudents": teacher.get("totalStudents", 0),
        "role": teacher.get("role", "Teacher"),
        "status": "Active" if str(teacher.get("status", "")).lower() == "active" else "Inactive",
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
        "status": course.get("status", "Inactive")
    }

def clean_update_data(data: dict) -> dict:
    """Remove None values from dict and add updatedAt"""
    update_data = {k: v for k, v in data.items() if v is not None}
    if update_data:
        update_data["updatedAt"] = datetime.utcnow()
    return update_data

# ------------------ Admin Functions ------------------

async def get_admin_by_email(email: str):
    return await db.admins.find_one({"email": email})

async def create_admin(admin: AdminCreate):
    existing = await get_admin_by_email(admin.email)
    if existing:
        raise ValueError("Email already registered")
    if admin.password != admin.confirmPassword:
        raise ValueError("Passwords do not match")

    hashed_password = pwd_context.hash(admin.password)
    full_name = f"{admin.firstName} {admin.lastName}"

    admin_doc = {
        "fullName": full_name,
        "email": admin.email,
        "password": hashed_password,
        "country": admin.country,
        "contactNo": admin.phone,
        "profileImageURL": "",
        "status": "active",
        "createdAt": datetime.utcnow(),
        "updatedAt": datetime.utcnow(),
        "role": "admin",
    }
    result = await db.admins.insert_one(admin_doc)
    admin_doc["_id"] = result.inserted_id
    return serialize_admin(admin_doc)

async def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

async def update_admin_profile(admin_id: str, data: AdminUpdateProfile):
    update_data = clean_update_data(data.dict())
    if not update_data:
        return None
    await db.admins.update_one({"_id": ObjectId(admin_id)}, {"$set": update_data})
    admin = await db.admins.find_one({"_id": ObjectId(admin_id)})
    return serialize_admin(admin)

async def update_admin_password(admin_id: str, old_password: str, new_password: str):
    admin = await db.admins.find_one({"_id": ObjectId(admin_id)})
    if not admin:
        raise ValueError("Admin not found")
    if not pwd_context.verify(old_password, admin["password"]):
        raise ValueError("Old password is incorrect")
    hashed_password = pwd_context.hash(new_password)
    await db.admins.update_one(
        {"_id": ObjectId(admin_id)},
        {"$set": {"password": hashed_password, "updatedAt": datetime.utcnow()}}
    )
    admin = await db.admins.find_one({"_id": ObjectId(admin_id)})
    return serialize_admin(admin)

# ------------------ Dashboard Functions ------------------

async def get_all_teachers():
    teachers_cursor = db.teachers.find({})
    teachers = []
    async for teacher in teachers_cursor:
        teachers.append(serialize_teacher(teacher))
    return teachers

async def get_all_students():
    students_cursor = db.students.find({})
    students = []
    async for student in students_cursor:
        students.append(serialize_student(student))
    return students

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
