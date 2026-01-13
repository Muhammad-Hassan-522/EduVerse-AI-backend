from bson import ObjectId
from datetime import datetime
from app.db.database import student_performance_collection
from app.utils.mongo import fix_object_ids

class StudentPerformanceCRUD:

    # -----------------------------------------------------------
    # CREATE PERFORMANCE DOCUMENT WHEN STUDENT IS CREATED
    # -----------------------------------------------------------
    @staticmethod
    async def create_performance_record(student_id: str, student_name: str, tenant_id: str, user_id: str = None):

        doc = {
            "studentId": ObjectId(student_id),
            "studentName": student_name,
            "tenantId": ObjectId(tenant_id),
            "userId": ObjectId(user_id) if user_id else None,

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
    # HELPER: Process Leaderboard with Lookup
    # -----------------------------------------------------------
    @staticmethod
    async def _get_leaderboard(pipeline: list):
        # Add lookup to pipeline
        pipeline.extend([
            {"$lookup": {
                "from": "users",
                "localField": "userId",
                "foreignField": "_id",
                "as": "user"
            }},
            {"$unwind": {"path": "$user", "preserveNullAndEmptyArrays": True}},
            {"$sort": {"totalPoints": -1}}
        ])
        
        cursor = student_performance_collection.aggregate(pipeline)
        docs = await cursor.to_list(length=None)
        
        leaderboard = []
        for d in docs:
            user = d.get("user", {})
            name = user.get("fullName") if user else d.get("studentName")
            leaderboard.append({
                "studentName": name,
                "points": d.get("totalPoints", 0)
            })
            
        leaderboard.sort(key=lambda x: -x["points"])
        
        # Limit to top 5 if needed? The functions will slice.
        return leaderboard

    # -----------------------------------------------------------
    # CLEAN TENANT TOP 5 (rank, name, points)
    # -----------------------------------------------------------
    @staticmethod
    async def tenant_top5(tenant_id: str):
        pipeline = [{"$match": {"tenantId": ObjectId(tenant_id)}}]
        leaderboard = await StudentPerformanceCRUD._get_leaderboard(pipeline)
        
        top5 = leaderboard[:5]
        for idx, item in enumerate(top5, start=1):
            item["rank"] = idx
        return top5

    # -----------------------------------------------------------
    # CLEAN TENANT FULL LEADERBOARD
    # -----------------------------------------------------------
    @staticmethod
    async def tenant_full(tenant_id: str):
        pipeline = [{"$match": {"tenantId": ObjectId(tenant_id)}}]
        leaderboard = await StudentPerformanceCRUD._get_leaderboard(pipeline)
        
        for idx, item in enumerate(leaderboard, start=1):
            item["rank"] = idx
        return leaderboard

    # -----------------------------------------------------------
    # CLEAN GLOBAL TOP 5
    # -----------------------------------------------------------
    @staticmethod
    async def global_top5():
        pipeline = []
        leaderboard = await StudentPerformanceCRUD._get_leaderboard(pipeline)
        
        top5 = leaderboard[:5]
        for idx, item in enumerate(top5, start=1):
            item["rank"] = idx
        return top5

    # -----------------------------------------------------------
    # CLEAN GLOBAL FULL LEADERBOARD
    # -----------------------------------------------------------
    @staticmethod
    async def global_full():
        pipeline = []
        leaderboard = await StudentPerformanceCRUD._get_leaderboard(pipeline)
        
        for idx, item in enumerate(leaderboard, start=1):
            item["rank"] = idx
        return leaderboard

    # -----------------------------------------------------------
    # GET PERFORMANCE FOR TEACHER'S STUDENTS
    # -----------------------------------------------------------
    @staticmethod
    async def get_teacher_performances(teacher_id: str, tenant_id: str):
        from app.db.database import courses_collection, students_collection
        
        try:
            # 1. Get all course IDs for this teacher - Handle both string and ObjectId formats
            teacher_query = {
                "tenantId": ObjectId(tenant_id),
                "$or": [
                    {"teacherId": teacher_id},
                    {"teacherId": ObjectId(teacher_id) if ObjectId.is_valid(teacher_id) else None}
                ]
            }
            
            teacher_courses = await courses_collection.find(teacher_query).to_list(length=None)
            course_ids = [str(c["_id"]) for c in teacher_courses]
            
            if not course_ids:
                return []
                
            # 2. Aggregate from Students collection
            pipeline = [
                # Match students in this tenant who are enrolled in ANY of the teacher's courses
                {"$match": {
                    "tenantId": ObjectId(tenant_id),
                    "enrolledCourses": {"$in": course_ids}
                }},
                
                {"$unwind": "$enrolledCourses"},
                {"$match": {"enrolledCourses": {"$in": course_ids}}},
                
                {"$lookup": {
                    "from": "users",
                    "localField": "userId",
                    "foreignField": "_id",
                    "as": "user"
                }},
                {"$unwind": {"path": "$user", "preserveNullAndEmptyArrays": True}},
                
                {"$addFields": {"course_oid": {"$toObjectId": "$enrolledCourses"}}},
                {"$lookup": {
                    "from": "courses",
                    "localField": "course_oid",
                    "foreignField": "_id",
                    "as": "course"
                }},
                {"$unwind": {"path": "$course", "preserveNullAndEmptyArrays": True}},
                
                {"$lookup": {
                    "from": "studentPerformance", # Fixed collection name (camelCase)
                    "localField": "_id",
                    "foreignField": "studentId",
                    "as": "performance"
                }},
                {"$unwind": {"path": "$performance", "preserveNullAndEmptyArrays": True}},
                
                {"$project": {
                    "_id": {"$ifNull": [{"$toString": "$performance._id"}, ""]},
                    "studentId": {"$toString": "$_id"},
                    "courseId": "$enrolledCourses",
                    "tenantId": {"$toString": "$tenantId"},
                    "studentName": {"$ifNull": ["$user.fullName", "$studentName", "Unknown Student"]},
                    "courseName": {"$ifNull": ["$course.title", "Unknown Course"]},
                    "progress": {
                        "$let": {
                            "vars": {
                                "matched": {
                                    "$filter": {
                                        "input": {"$ifNull": ["$performance.courseStats", []]},
                                        "as": "stat",
                                        "cond": {"$eq": ["$$stat.courseId", "$enrolledCourses"]}
                                    }
                                }
                            },
                            "in": {"$ifNull": [{"$arrayElemAt": ["$$matched.completionPercentage", 0]}, 0]}
                        }
                    },
                    "lastUpdated": {
                        "$let": {
                            "vars": {
                                "matched": {
                                    "$filter": {
                                        "input": {"$ifNull": ["$performance.courseStats", []]},
                                        "as": "stat",
                                        "cond": {"$eq": ["$$stat.courseId", "$enrolledCourses"]}
                                    }
                                }
                            },
                            "in": {"$ifNull": [{"$arrayElemAt": ["$$matched.lastActive", 0]}, "Never"]}
                        }
                    },
                    "marks": {"$literal": 0},
                    "totalMarks": {"$literal": 0},
                    "grade": {"$literal": "N/A"},
                    "attendance": {"$literal": 100}
                }}
            ]
            
            cursor = students_collection.aggregate(pipeline)
            performances = await cursor.to_list(length=None)
            return performances
            
        except Exception as e:
            pass
            # Return empty list on error instead of crashing, to avoid CORS issues
            return []
