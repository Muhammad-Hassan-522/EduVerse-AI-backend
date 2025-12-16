from datetime import datetime
from bson import ObjectId
from app.schemas.student import StudentCreate, StudentUpdate
from app.utils.mongo import fix_object_ids
from app.db.database import students_collection as COLLECTION
from app.db.database import courses_collection
from app.db.database import student_performance_collection
# ---------------------------------------------------------------------------
# Create Student (Multi-Tenant)
# ---------------------------------------------------------------------------
async def create_student(student: StudentCreate, tenant_id: str):
    data = student.dict()

    data.update({
        "tenantId": ObjectId(tenant_id),
        "password": data["password"],
        "enrolledCourses": [],
        "completedCourses": [],
        "role": "student",
        "status": "active",
        "createdAt": datetime.utcnow(),
        "updatedAt": datetime.utcnow(),
        "lastLogin": None,
    })

    result = await COLLECTION.insert_one(data)
    new_student = await COLLECTION.find_one({"_id": result.inserted_id})

    # -----------------------------------------------------------
    # AUTOMATICALLY CREATE STUDENT PERFORMANCE DOCUMENT
    # -----------------------------------------------------------
    performance_doc = {
        "tenantId": ObjectId(tenant_id),
        "studentId": result.inserted_id,
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
        "updatedAt": datetime.utcnow()
    }

    await student_performance_collection.insert_one(performance_doc)

    # -----------------------------------------------------------
    return fix_object_ids(new_student)
# ---------------------------------------------------------------------------
# Create Student (Multi-Tenant)
# ---------------------------------------------------------------------------
async def create_student(student: StudentCreate, tenant_id: str):
    data = student.dict()

    data.update({
        "tenantId": ObjectId(tenant_id),
        "password": data["password"],
        "enrolledCourses": [],
        "completedCourses": [],
        "role": "student",
        "status": "active",
        "createdAt": datetime.utcnow(),
        "updatedAt": datetime.utcnow(),
        "lastLogin": None,
    })

    result = await COLLECTION.insert_one(data)
    new_student = await COLLECTION.find_one({"_id": result.inserted_id})

    # -----------------------------------------------------------
    # AUTOMATICALLY CREATE STUDENT PERFORMANCE DOCUMENT
    # -----------------------------------------------------------
    performance_doc = {
        "tenantId": ObjectId(tenant_id),
        "studentId": result.inserted_id,
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
        "updatedAt": datetime.utcnow()
    }

    await student_performance_collection.insert_one(performance_doc)

    # -----------------------------------------------------------
    return fix_object_ids(new_student)



# ---------------------------------------------------------------------------
# Create Student (Multi-Tenant)
# ---------------------------------------------------------------------------
async def create_student(student: StudentCreate, tenant_id: str):
    data = student.dict()

    data.update({
        "tenantId": ObjectId(tenant_id),
        "password": data["password"],
        "enrolledCourses": [],
        "completedCourses": [],
        "role": "student",
        "status": "active",
        "createdAt": datetime.utcnow(),
        "updatedAt": datetime.utcnow(),
        "lastLogin": None,
    })

    result = await COLLECTION.insert_one(data)
    new_student = await COLLECTION.find_one({"_id": result.inserted_id})

    # -----------------------------------------------------------
    # AUTOMATICALLY CREATE STUDENT PERFORMANCE DOCUMENT
    # -----------------------------------------------------------
    performance_doc = {
        "tenantId": ObjectId(tenant_id),
        "studentId": result.inserted_id,
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
        "updatedAt": datetime.utcnow()
    }

    await student_performance_collection.insert_one(performance_doc)

    # -----------------------------------------------------------
    return fix_object_ids(new_student)

# ---------------------------------------------------------------------------
# Login (Email only — tenant irrelevant)
# ---------------------------------------------------------------------------
async def get_student_by_email(email: str):
    student = await COLLECTION.find_one({"email": email})
    return fix_object_ids(student) if student else None



# ---------------------------------------------------------------------------
# Get Student by ID + Tenant
# ---------------------------------------------------------------------------
async def get_student_by_id(student_id: str, tenantId: str):
    student = await COLLECTION.find_one({
        "_id": ObjectId(student_id),
        "tenantId": ObjectId(tenantId)
    })
    return fix_object_ids(student) if student else None



# ---------------------------------------------------------------------------
# List All Students in a Tenant
# ---------------------------------------------------------------------------
async def list_students(tenantId: str):
    cursor = COLLECTION.find({"tenantId": ObjectId(tenantId)})
    return fix_object_ids(await cursor.to_list(length=None))



# ---------------------------------------------------------------------------
# Update Student
# ---------------------------------------------------------------------------
async def update_student(student_id: str, tenantId: str, update: StudentUpdate):

    update_data = {k: v for k, v in update.dict().items() if v is not None}
    update_data["updatedAt"] = datetime.utcnow()

    result = await COLLECTION.update_one(
        {"_id": ObjectId(student_id), "tenantId": ObjectId(tenantId)},
        {"$set": update_data}
    )

    if result.modified_count == 0:
        return None

    updated = await COLLECTION.find_one({
        "_id": ObjectId(student_id),
        "tenantId": ObjectId(tenantId)
    })
    return fix_object_ids(updated)

# ---------------------------------------------------------------------------
# Delete Student
# ---------------------------------------------------------------------------
#async def delete_student(student_id: str, tenantId: str):

#    result = await COLLECTION.delete_one({
#       "_id": ObjectId(student_id),
 #       "tenantId": ObjectId(tenantId)
  #  })

   # return result.deleted_count == 1

async def delete_student(student_id: str, tenant_id: str):

    # STEP 1 — Fetch student before deleting
    student = await COLLECTION.find_one({
        "_id": ObjectId(student_id),
        "tenantId": ObjectId(tenant_id)
    })

    if not student:
        return False

    # STEP 2 — Decrease enrolledStudents count for each course
    enrolled_courses = student.get("enrolledCourses", [])

    for course_id in enrolled_courses:
        await courses_collection.update_one(
            {"_id": ObjectId(course_id)},
            {"$inc": {"enrolledStudents": -1}}
        )

    # STEP 3 — Delete the student from the STUDENTS collection
    result = await COLLECTION.delete_one({
        "_id": ObjectId(student_id),
        "tenantId": ObjectId(tenant_id)
    })

    # If student was not deleted → stop
    if result.deleted_count == 0:
        return False

    # STEP 4 — Delete student performance document for this student + tenant
    await student_performance_collection.delete_one({
        "studentId": ObjectId(student_id),
        "tenantId": ObjectId(tenant_id)
    })

    return True


