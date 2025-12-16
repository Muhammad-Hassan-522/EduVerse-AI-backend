from bson import ObjectId
from datetime import datetime
from app.db.database import student_performance_collection
from app.utils.mongo import fix_object_ids


class StudentPerformanceCRUD:

    # -----------------------------------------------------------
    # CREATE PERFORMANCE DOCUMENT WHEN STUDENT IS CREATED
    # -----------------------------------------------------------
    @staticmethod
    async def create_performance_record(student_id: str, student_name: str, tenant_id: str):

        doc = {
            "studentId": ObjectId(student_id),
            "studentName": student_name,
            "tenantId": ObjectId(tenant_id),

            # core points
            "totalPoints": 0,
            "pointsThisWeek": 0,

            # XP system
            "xp": 0,
            "level": 1,
            "xpToNextLevel": 300,

            # breakdowns
            "badges": [],
            "certificates": [],
            "weeklyStudyTime": [],
            "courseStats": [],

            "createdAt": datetime.utcnow()
        }

        await student_performance_collection.insert_one(doc)
        return True

    # -----------------------------------------------------------
    # XP + LEVEL SYSTEM
    # -----------------------------------------------------------
    @staticmethod
    def _update_level_system(data: dict):

        xp = data.get("xp", 0)
        level = data.get("level", 1)

        def xp_needed_for(level):
            raw = 300 * (1.5 ** (level - 1))
            return int(round(raw / 50) * 50)

        xp_required = xp_needed_for(level)

        while xp >= xp_required:
            xp -= xp_required
            level += 1
            xp_required = xp_needed_for(level)

        data["xp"] = xp
        data["level"] = level
        data["xpToNextLevel"] = xp_required
        return data

    # -----------------------------------------------------------
    # GET PERFORMANCE BY STUDENT + TENANT
    # -----------------------------------------------------------
    @staticmethod
    async def get_student_performance(student_id: str, tenant_id: str):

        doc = await student_performance_collection.find_one({
            "studentId": ObjectId(student_id),
            "tenantId": ObjectId(tenant_id)
        })

        if not doc:
            return None

        doc = fix_object_ids(doc)
        doc["id"] = doc.get("_id")
        return doc

    # -----------------------------------------------------------
    # ADD POINTS
    # -----------------------------------------------------------
    @staticmethod
    async def add_points(student_id: str, tenant_id: str, points: int):

        await student_performance_collection.update_one(
            {"studentId": ObjectId(student_id), "tenantId": ObjectId(tenant_id)},
            {"$inc": {"totalPoints": points, "pointsThisWeek": points, "xp": points}}
        )

        updated = await StudentPerformanceCRUD.get_student_performance(student_id, tenant_id)
        updated = StudentPerformanceCRUD._update_level_system(updated)

        await student_performance_collection.update_one(
            {"studentId": ObjectId(student_id), "tenantId": ObjectId(tenant_id)},
            {"$set": {
                "xp": updated["xp"],
                "level": updated["level"],
                "xpToNextLevel": updated["xpToNextLevel"]
            }}
        )

        return updated

    # -----------------------------------------------------------
    # BADGES
    # -----------------------------------------------------------
    @staticmethod
    async def add_badge(student_id: str, tenant_id: str, badge: dict):

        badge["date"] = datetime.utcnow()

        await student_performance_collection.update_one(
            {"studentId": ObjectId(student_id), "tenantId": ObjectId(tenant_id)},
            {"$push": {"badges": badge}}
        )

        return await StudentPerformanceCRUD.get_student_performance(student_id, tenant_id)

    @staticmethod
    async def view_badges(student_id: str, tenant_id: str):

        doc = await student_performance_collection.find_one(
            {"studentId": ObjectId(student_id), "tenantId": ObjectId(tenant_id)},
            {"badges": 1, "_id": 0}
        )

        return fix_object_ids(doc.get("badges", [])) if doc else []

    # -----------------------------------------------------------
    # CERTIFICATES
    # -----------------------------------------------------------
    @staticmethod
    async def add_certificate(student_id: str, tenant_id: str, cert: dict):

        cert["date"] = datetime.utcnow()

        await student_performance_collection.update_one(
            {"studentId": ObjectId(student_id), "tenantId": ObjectId(tenant_id)},
            {"$push": {"certificates": cert}}
        )

        return await StudentPerformanceCRUD.get_student_performance(student_id, tenant_id)

    @staticmethod
    async def view_certificates(student_id: str, tenant_id: str):

        doc = await student_performance_collection.find_one(
            {"studentId": ObjectId(student_id), "tenantId": ObjectId(tenant_id)},
            {"certificates": 1, "_id": 0}
        )

        return fix_object_ids(doc.get("certificates", [])) if doc else []

    # -----------------------------------------------------------
    # COURSE STATS
    # -----------------------------------------------------------
    @staticmethod
    async def get_course_stats(student_id: str, tenant_id: str):

        doc = await student_performance_collection.find_one(
            {"studentId": ObjectId(student_id), "tenantId": ObjectId(tenant_id)},
            {"courseStats": 1, "_id": 0}
        )

        return fix_object_ids(doc.get("courseStats", [])) if doc else []

    # -----------------------------------------------------------
    # PROGRESS UPDATE + BADGE
    # -----------------------------------------------------------
    @staticmethod
    async def update_course_progress(student_id: str, tenant_id: str, course_id: str, completion: int, last_active: str):

        # update OR insert
        update_result = await student_performance_collection.update_one(
            {"studentId": ObjectId(student_id), "tenantId": ObjectId(tenant_id), "courseStats.courseId": course_id},
            {"$set": {
                "courseStats.$.completionPercentage": completion,
                "courseStats.$.lastActive": last_active
            }}
        )

        if update_result.modified_count == 0:
            await student_performance_collection.update_one(
                {"studentId": ObjectId(student_id), "tenantId": ObjectId(tenant_id)},
                {"$push": {
                    "courseStats": {
                        "courseId": course_id,
                        "completionPercentage": completion,
                        "lastActive": last_active
                    }
                }}
            )

        # Award completion badge (only if 100%)
        if completion == 100:
            exists = await student_performance_collection.find_one({
                "studentId": ObjectId(student_id),
                "tenantId": ObjectId(tenant_id),
                "badges.courseId": course_id
            })

            if not exists:
                await StudentPerformanceCRUD.add_badge(student_id, tenant_id, {
                    "courseId": course_id,
                    "name": "Course Completer",
                    "icon": "completion.png"
                })

        return await StudentPerformanceCRUD.get_student_performance(student_id, tenant_id)

    # -----------------------------------------------------------
    # WEEKLY TIME
    # -----------------------------------------------------------
    @staticmethod
    async def add_weekly_time(student_id: str, tenant_id: str, week_start: str, minutes: int):

        await student_performance_collection.update_one(
            {"studentId": ObjectId(student_id), "tenantId": ObjectId(tenant_id)},
            {"$push": {
                "weeklyStudyTime": {
                    "weekStart": week_start,
                    "minutes": minutes
                }
            }}
        )

        return await StudentPerformanceCRUD.get_student_performance(student_id, tenant_id)

    # -----------------------------------------------------------
    # CLEAN TENANT TOP 5 (rank, name, points)
    # -----------------------------------------------------------
    @staticmethod
    async def tenant_top5(tenant_id: str):

        cursor = student_performance_collection.find({
            "tenantId": ObjectId(tenant_id)
        })

        docs = await cursor.to_list(length=None)

        leaderboard = [{
            "studentName": d.get("studentName"),
            "points": d.get("totalPoints", 0)
        } for d in docs]

        leaderboard.sort(key=lambda x: -x["points"])

        top5 = leaderboard[:5]

        for idx, item in enumerate(top5, start=1):
            item["rank"] = idx

        return top5

    # -----------------------------------------------------------
    # CLEAN TENANT FULL LEADERBOARD
    # -----------------------------------------------------------
    @staticmethod
    async def tenant_full(tenant_id: str):

        cursor = student_performance_collection.find({
            "tenantId": ObjectId(tenant_id)
        })

        docs = await cursor.to_list(length=None)

        leaderboard = [{
            "studentName": d.get("studentName"),
            "points": d.get("totalPoints", 0)
        } for d in docs]

        leaderboard.sort(key=lambda x: -x["points"])

        for idx, item in enumerate(leaderboard, start=1):
            item["rank"] = idx

        return leaderboard

    # -----------------------------------------------------------
    # CLEAN GLOBAL TOP 5
    # -----------------------------------------------------------
    @staticmethod
    async def global_top5():

        cursor = student_performance_collection.find({})
        docs = await cursor.to_list(length=None)

        leaderboard = [{
            "studentName": d.get("studentName"),
            "points": d.get("totalPoints", 0)
        } for d in docs]

        leaderboard.sort(key=lambda x: -x["points"])

        top5 = leaderboard[:5]

        for idx, item in enumerate(top5, start=1):
            item["rank"] = idx

        return top5

    # -----------------------------------------------------------
    # CLEAN GLOBAL FULL LEADERBOARD
    # -----------------------------------------------------------
    @staticmethod
    async def global_full():

        cursor = student_performance_collection.find({})
        docs = await cursor.to_list(length=None)

        leaderboard = [{
            "studentName": d.get("studentName"),
            "points": d.get("totalPoints", 0)
        } for d in docs]

        leaderboard.sort(key=lambda x: -x["points"])

        for idx, item in enumerate(leaderboard, start=1):
            item["rank"] = idx

        return leaderboard
