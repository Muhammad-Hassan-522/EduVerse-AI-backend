from bson import ObjectId
from app.db.database import courses_collection
from app.utils.mongo import fix_object_ids
from app.core.settings import TENANT_ID


async def get_all_active_courses():
    cursor = courses_collection.find(
        {
            "status": "Active",
            "tenantId": TENANT_ID, 
        }
    )
    courses = await cursor.to_list(length=None)
    return fix_object_ids(courses)


async def get_course_by_id(course_id: str):
    course = await courses_collection.find_one(
        {"_id": ObjectId(course_id), "tenantId": TENANT_ID}
    )
    if not course:
        return None
    return fix_object_ids(course)
