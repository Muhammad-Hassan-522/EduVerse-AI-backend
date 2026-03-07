
import asyncio
from app.db.database import db
from bson import ObjectId

async def test():
    cursor = db.courses.find()
    async for course in cursor:
        print(f"--- Course: {course.get('title')} ({course.get('_id')}) ---")
        modules = course.get("modules", [])
        print(f"Modules: {len(modules)}")
        
        total_lessons = 0
        for i, m in enumerate(modules):
            lessons = m.get("lessons", [])
            total_lessons += len(lessons)
            for j, l in enumerate(lessons):
                 # print(f"    Lesson {j}: id={l.get('id')}, title={l.get('title')}")
                 pass
                
        print(f"Total lessons: {total_lessons}")

if __name__ == "__main__":
    asyncio.run(test())
