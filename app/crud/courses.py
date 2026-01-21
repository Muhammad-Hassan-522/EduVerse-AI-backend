
from bson import ObjectId
from datetime import datetime
from typing import List, Optional, Dict, Any
from app.db.database import get_courses_collection, get_students_collection, db, users_collection
from app.schemas.courses import CourseCreate, CourseUpdate

class CourseCRUD:
   
    def __init__(self):
        self.collection = get_courses_collection()
        self.students_collection = get_students_collection()
        self.users_collection = users_collection

    def clean_update_data(self, update_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Cleans the update dictionary by removing nulls, default 'string' placeholders, 
        and empty values that shouldn't be overridden.
        
        Args:
            update_dict: The raw dictionary containing potential updates.
            
        Returns:
            A sanitized dictionary ready for the database $set operation.
        """
        cleaned = {}
        
        for key, value in update_dict.items():
            # Skip null values to avoid unintentional field deletion
            if value is None:
                continue
            
            # Skip Swagger/OpenAPI default 'string' placeholders
            if isinstance(value, str) and value.strip().lower() == "string":
                continue
            
            # Skip empty strings except for thumbnailUrl which can be cleared
            if isinstance(value, str) and value.strip() == "" and key != "thumbnailUrl":
                continue
            
            # Specialized list cleaning (e.g., for modules)
            if isinstance(value, list):
                if len(value) > 0 and all(
                    isinstance(item, dict) and 
                    item.get('title', '').strip().lower() == 'string'
                    for item in value
                ):
                    continue
                
                # Keep empty module lists if explicitly provided
                if len(value) == 0 and key != "modules":
                    continue
            
            cleaned[key] = value
        
        return cleaned

    async def create_course(self, course_data: CourseCreate) -> dict:
        """
         UPDATED: Create a new course with validation
        
        Changes made:
        1. Validates that tenant exists in database
        2. Validates that teacher exists and belongs to same tenant
        3. Converts teacherId to ObjectId (was string before)
        4. Updates teacher's assignedCourses array automatically
        
        Raises:
            ValueError: If tenant/teacher not found or validation fails
        """
        course_dict = course_data.dict()
        
        # Validate tenantId format
        if not course_dict.get("tenantId") or not ObjectId.is_valid(course_dict["tenantId"]):
            raise ValueError(f"Invalid or missing tenant ID: {course_dict.get('tenantId', 'Not provided')}")
        
        #  Validate teacherId format
        if not course_dict.get("teacherId") or not ObjectId.is_valid(course_dict["teacherId"]):
            raise ValueError(f"Please select an instructor. Invalid teacher ID: {course_dict.get('teacherId', 'Not provided')}")
        
        tenant_id = ObjectId(course_dict["tenantId"])
        teacher_id = ObjectId(course_dict["teacherId"])
        
        # Check if tenant exists in database
        tenant = await db.tenants.find_one({"_id": tenant_id})
        if not tenant:
            raise ValueError(f"Tenant not found with ID: {course_dict['tenantId']}")
        
        #  Check if teacher exists and belongs to the same tenant
        teacher = await db.teachers.find_one({
            "_id": teacher_id,
            "tenantId": tenant_id
        })
        
        if not teacher:
            # Check if teacher exists in a different tenant
            teacher_exists = await db.teachers.find_one({"_id": teacher_id})
            if teacher_exists:
                raise ValueError("Teacher found but belongs to different tenant")
            raise ValueError(f"Teacher not found with ID: {course_dict['teacherId']}")
        
        #  Store both IDs as ObjectId (teacherId was string before)
        course_dict["tenantId"] = tenant_id
        course_dict["teacherId"] = teacher_id
        
        # Add timestamps
        course_dict["createdAt"] = datetime.utcnow()
        course_dict["updatedAt"] = datetime.utcnow()
        course_dict["enrolledStudents"] = 0
        
        # Insert into MongoDB
        result = await self.collection.insert_one(course_dict)
        course_id = result.inserted_id
        
        #  Update teacher's assignedCourses array
        await db.teachers.update_one(
            {"_id": teacher_id},
            {
                "$addToSet": {"assignedCourses": course_id},
                "$set": {"updatedAt": datetime.utcnow()}
            }
        )
        
        # Convert ObjectIds to strings for response
        course_dict["_id"] = str(course_id)
        course_dict["tenantId"] = str(tenant_id)
        course_dict["teacherId"] = str(teacher_id)
        
        return course_dict

    def _get_enriched_courses_pipeline(self, query: Dict[str, Any], skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Creates a centralized aggregation pipeline for enriching course data with 
        instructor names from the users collection.
        """
        return [
            {"$match": query},
            {"$addFields": {
                "teacherId": {"$toObjectId": "$teacherId"}
            }},
            {"$skip": skip},
            {"$limit": limit},
            {
                "$lookup": {
                    "from": "teachers",
                    "localField": "teacherId",
                    "foreignField": "_id",
                    "as": "teacher_info"
                }
            },
            {"$unwind": {"path": "$teacher_info", "preserveNullAndEmptyArrays": True}},
            {
                "$lookup": {
                    "from": "users",
                    "localField": "teacher_info.userId",
                    "foreignField": "_id",
                    "as": "user_info"
                }
            },
            {"$unwind": {"path": "$user_info", "preserveNullAndEmptyArrays": True}},
            {
                "$addFields": {
                    "instructorName": {"$ifNull": ["$user_info.fullName", "Instructor"]}
                }
            },
            {"$project": {"teacher_info": 0, "user_info": 0}}
        ]

    def _serialize_course(self, course: Dict[str, Any]) -> Dict[str, Any]:
        """Ensures common serialization logic for course documents."""
        course["_id"] = str(course["_id"])
        course["tenantId"] = str(course["tenantId"])
        
        if "teacherId" in course and isinstance(course["teacherId"], ObjectId):
            course["teacherId"] = str(course["teacherId"])
            
        # Ensure thumbnailUrl is None if empty string to allow frontend fallback
        if not course.get("thumbnailUrl"):
            course["thumbnailUrl"] = None
            
        return course

    async def get_course_by_id(self, course_id: str, tenantId: str) -> dict:
        """
        Retrieves a single course by its ID and tenant ID.
        Ensures strict tenant isolation.
        """
        if not ObjectId.is_valid(course_id) or not ObjectId.is_valid(tenantId):
            return {"success": False, "message": "Invalid ID format", "course": None}
            
        query = {"_id": ObjectId(course_id), "tenantId": ObjectId(tenantId)}
        pipeline = self._get_enriched_courses_pipeline(query, 0, 1)
        
        results = await self.collection.aggregate(pipeline).to_list(length=1)
        if not results:
            return {"success": False, "message": "Course not found", "course": None}
            
        course = self._serialize_course(results[0])
        return {"success": True, "message": "Course found", "course": course}

    async def get_all_courses(
        self, 
        tenantId: str,
        teacher_id: Optional[str] = None,
        status: Optional[str] = None,
        category: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> dict:
        """
        Retrieves a list of courses filtered by tenant, teacher, status, etc.
        Supports regex search on title, description, category, and course code.
        
        Returns:
            A dictionary with results, total count, and metadata.
        """
        
        if not ObjectId.is_valid(tenantId):
            return {
                "success": False,
                "message": f"Invalid tenant ID format: {tenantId}",
                "courses": [],
                "total": 0
            }
        
        # Enforce tenant isolation in base query
        query = {"tenantId": ObjectId(tenantId)}
        
        # Add teacher filter if provided
        if teacher_id:
            if ObjectId.is_valid(teacher_id):
                query["teacherId"] = ObjectId(teacher_id)
            else:
                return {
                    "success": False,
                    "message": f"Invalid teacher ID format: {teacher_id}",
                    "courses": [],
                    "total": 0
                }
        
        # Add status filter (case-insensitive regex)
        if status:
            status = status.strip()
            query["status"] = {"$regex": f"^{status}$", "$options": "i"}
        
        # Add category filter (case-insensitive regex)
        if category:
            category = category.strip()
            query["category"] = {"$regex": f"^{category}$", "$options": "i"}
        
        # Add broad text search across multiple fields
        if search:
            search = search.strip()
            query["$or"] = [
                {"title": {"$regex": search, "$options": "i"}},
                {"description": {"$regex": search, "$options": "i"}},
                {"category": {"$regex": search, "$options": "i"}},
                {"courseCode": {"$regex": search, "$options": "i"}}
            ]
        
        try:
            # Pipeline for aggregation with lookups
            pipeline = self._get_enriched_courses_pipeline(query, skip, limit)

            # Execute query
            total = await self.collection.count_documents(query)
            courses = await self.collection.aggregate(pipeline).to_list(length=limit)
            
            # Serialize for response
            courses = [self._serialize_course(c) for c in courses]
            
            return {
                "success": True,
                "message": f"Found {len(courses)} courses (total: {total})",
                "courses": courses,
                "total": total,
                "skip": skip,
                "limit": limit
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Error fetching courses: {str(e)}",
                "courses": [],
                "total": 0
            }

    async def update_course(
        self, 
        course_id: str, 
        tenantId: str, 
        course_update: CourseUpdate
    ) -> Optional[dict]:
        """
        Updates an existing course with new information.
        Only fields explicitly provided in the update request are modified.
        
        Args:
            course_id: ID of the course to update.
            tenantId: ID of the tenant (for isolation).
            course_update: Pydantic model containing update fields.
            
        Returns:
            The updated course document or None if not found.
        """
        
        if not ObjectId.is_valid(course_id):
            return None
        
        if not ObjectId.is_valid(tenantId):
            return None
        
        # Get existing course to identify the teacher before update
        existing_course = await self.collection.find_one({"_id": ObjectId(course_id), "tenantId": ObjectId(tenantId)})
        if not existing_course:
            return None
        old_teacher_id = existing_course.get("teacherId")

        # Convert schema to dict and remove unset fields
        update_data = course_update.dict(exclude_unset=True)
        cleaned_data = self.clean_update_data(update_data)
        
        # If no valid updates after cleaning, just return current state
        if not cleaned_data:
            return {
                "_id": str(existing_course["_id"]),
                "tenantId": str(existing_course["tenantId"]),
                "teacherId": str(existing_course["teacherId"]),
                **{k: v for k, v in existing_course.items() if k not in ["_id", "tenantId", "teacherId"]}
            }
        
        cleaned_data["updatedAt"] = datetime.utcnow()
        
        # Ensure IDs are stored as ObjectIds to avoid disappearing from UI lists
        if "tenantId" in cleaned_data and isinstance(cleaned_data["tenantId"], str):
            cleaned_data["tenantId"] = ObjectId(cleaned_data["tenantId"])
        if "teacherId" in cleaned_data and isinstance(cleaned_data["teacherId"], str):
            cleaned_data["teacherId"] = ObjectId(cleaned_data["teacherId"])
        
        from pymongo import ReturnDocument
        
        # Perform atomic update
        result = await self.collection.find_one_and_update(
            {"_id": ObjectId(course_id), "tenantId": ObjectId(tenantId)},
            {"$set": cleaned_data},
            return_document=ReturnDocument.AFTER
        )
        
        if result:
            # Synchronize teacher assignments if instructor changed
            new_teacher_id = cleaned_data.get("teacherId")
            if new_teacher_id and str(old_teacher_id) != str(new_teacher_id):
                # Remove from old
                if old_teacher_id:
                    await db.teachers.update_one(
                        {"_id": old_teacher_id},
                        {"$pull": {"assignedCourses": ObjectId(course_id)}}
                    )
                # Add to new
                await db.teachers.update_one(
                    {"_id": new_teacher_id},
                    {"$addToSet": {"assignedCourses": ObjectId(course_id)}}
                )

            result["_id"] = str(result["_id"])
            result["tenantId"] = str(result["tenantId"])
            
            if "teacherId" in result and isinstance(result["teacherId"], ObjectId):
                result["teacherId"] = str(result["teacherId"])
            
        return result

    

    async def delete_course(self, course_id: str, tenantId: str) -> dict:
     """
    Delete a course and clean up all references
    
    This method:
    1. Validates IDs
    2. Gets the course to find teacher and enrolled students
    3. Deletes the course
    4. Removes from teacher's assignedCourses
    5. Removes from all students' enrolledCourses
    """
    
     if not ObjectId.is_valid(course_id):
        return {
            "success": False, 
            "message": f"Invalid course ID format: {course_id}"
        }
    
     if not ObjectId.is_valid(tenantId):
        return {
            "success": False, 
            "message": f"Invalid tenant ID format: {tenantId}"
        }
    
     course_obj_id = ObjectId(course_id)
     tenant_obj_id = ObjectId(tenantId)
    
    # Get the course first to access teacher ID
     course = await self.collection.find_one({
        "_id": course_obj_id,
        "tenantId": tenant_obj_id
    })
    
     if not course:
        # Check if course exists in different tenant
        course_exists = await self.collection.find_one({"_id": course_obj_id})
        if course_exists:
            return {
                "success": False,
                "message": "Course found but belongs to different tenant"
            }
        return {
            "success": False,
            "message": f"Course not found with ID: {course_id}"
        }
    
    # Get teacher ID before deleting
     teacher_id = course.get("teacherId")
    
    # Delete the course
     delete_result = await self.collection.delete_one({
        "_id": course_obj_id,
        "tenantId": tenant_obj_id
    })
    
     if delete_result.deleted_count > 0:
        #  Remove course from teacher's assignedCourses array
        if teacher_id:
            # Ensure teacher_id is ObjectId
            if isinstance(teacher_id, str):
                teacher_id = ObjectId(teacher_id)
            
            teacher_update_result = await db.teachers.update_one(
                {"_id": teacher_id},
                {
                    "$pull": {"assignedCourses": course_obj_id},
                    "$set": {"updatedAt": datetime.utcnow()}
                }
            )
            

        
        #  Remove course from all enrolled students' enrolledCourses
        students_update_result = await self.students_collection.update_many(
            {"enrolledCourses": course_id},  # Course ID stored as string in students
            {
                "$pull": {"enrolledCourses": course_id},
                "$set": {"updatedAt": datetime.utcnow()}
            }
        )
        

        
        return {
            "success": True,
            "message": f"Course deleted successfully. Updated {teacher_update_result.modified_count if teacher_id else 0} teacher and {students_update_result.modified_count} students."
        }
    
    # This shouldn't happen, but handle it just in case
     return {
        "success": False,
        "message": "Failed to delete course"
    }

    async def enroll_student(self, course_id: str, student_id: str, tenantId: str) -> dict:
        """
        Enrolls a student in a course.
        Atomic operation that updates:
        1. Student's enrolledCourses list.
        2. Course's enrolledStudents counter (+1).
        
        Returns:
            Success status and message.
        """
        
        if not ObjectId.is_valid(course_id):
            return {"success": False, "message": f"Invalid course ID format: {course_id}"}
        
        if not ObjectId.is_valid(student_id):
            return {"success": False, "message": f"Invalid student ID format: {student_id}"}
        
        if not ObjectId.is_valid(tenantId):
            return {"success": False, "message": f"Invalid tenant ID format: {tenantId}"}
        
        tenant_object_id = ObjectId(tenantId)
        
        # Verify course exists and belongs to tenant
        course = await self.collection.find_one({
            "_id": ObjectId(course_id),
            "tenantId": tenant_object_id
        })
        
        if not course:
            course_exists = await self.collection.find_one({"_id": ObjectId(course_id)})
            if course_exists:
                return {"success": False, "message": "Course found but belongs to different tenant"}
            return {"success": False, "message": f"Course not found with ID: {course_id}"}
        
        # Verify student exists and belongs to tenant
        student = await self.students_collection.find_one({
            "_id": ObjectId(student_id),
            "tenantId": tenant_object_id
        })
        
        if not student:
            student_exists = await self.students_collection.find_one({"_id": ObjectId(student_id)})
            if student_exists:
                return {"success": False, "message": "Student found but belongs to different tenant"}
            return {"success": False, "message": f"Student not found with ID: {student_id}"}
        
        # Prevention: Already enrolled check
        enrolled_courses = student.get("enrolledCourses", [])
        if course_id in enrolled_courses:
            return {"success": False, "message": "Student is already enrolled in this course"}
        
        # Update 1: Student document
        await self.students_collection.update_one(
            {"_id": ObjectId(student_id), "tenantId": tenant_object_id},
            {
                "$addToSet": {"enrolledCourses": course_id},
                "$set": {"updatedAt": datetime.utcnow()}
            }
        )
        
        # Update 2: Course counter
        await self.collection.update_one(
            {"_id": ObjectId(course_id), "tenantId": tenant_object_id},
            {
                "$inc": {"enrolledStudents": 1},
                "$set": {"updatedAt": datetime.utcnow()}
            }
        )
        
        return {"success": True, "message": "Successfully enrolled in course"}

    async def unenroll_student(self, course_id: str, student_id: str, tenantId: str) -> dict:
        """
        Unenroll a student from a course
        
        This function:
        1. Validates that both course and student exist
        2. Checks if student is actually enrolled
        3. Removes course from student's enrolledCourses array
        4. Decrements the course's enrolledStudents count
        """
        # Validate course ID format
        if not ObjectId.is_valid(course_id):
            return {"success": False, "message": f"Invalid course ID format: {course_id}"}
        
        # Validate student ID format
        if not ObjectId.is_valid(student_id):
            return {"success": False, "message": f"Invalid student ID format: {student_id}"}
        
        # Validate tenant ID format
        if not ObjectId.is_valid(tenantId):
            return {"success": False, "message": f"Invalid tenant ID format: {tenantId}"}
        
        # Convert tenantId to ObjectId
        tenant_object_id = ObjectId(tenantId)
        
        # Check if course exists (with tenant isolation)
        course = await self.collection.find_one({
            "_id": ObjectId(course_id),
            "tenantId": tenant_object_id
        })
        
        if not course:
            # Check if course exists in a different tenant
            course_exists = await self.collection.find_one({"_id": ObjectId(course_id)})
            if course_exists:
                return {"success": False, "message": "Course found but belongs to different tenant"}
            return {"success": False, "message": f"Course not found with ID: {course_id}"}
        
        # Check if student exists (with tenant isolation)
        student = await self.students_collection.find_one({
            "_id": ObjectId(student_id),
            "tenantId": tenant_object_id
        })
        
        if not student:
            # Check if student exists in a different tenant
            student_exists = await self.students_collection.find_one({"_id": ObjectId(student_id)})
            if student_exists:
                return {"success": False, "message": "Student found but belongs to different tenant"}
            return {"success": False, "message": f"Student not found with ID: {student_id}"}
        
        # Check if student is actually enrolled in this course
        enrolled_courses = student.get("enrolledCourses", [])
        if course_id not in enrolled_courses:
            return {"success": False, "message": "Student is not enrolled in this course"}
        
        # Remove course from student's enrolledCourses array
        await self.students_collection.update_one(
            {"_id": ObjectId(student_id), "tenantId": tenant_object_id},
            {
                "$pull": {"enrolledCourses": course_id},
                "$set": {"updatedAt": datetime.utcnow()}
            }
        )
        
        # Decrement the course's enrolled student count by 1
        await self.collection.update_one(
            {"_id": ObjectId(course_id), "tenantId": tenant_object_id},
            {
                "$inc": {"enrolledStudents": -1},
                "$set": {"updatedAt": datetime.utcnow()}
            }
        )
        
        return {"success": True, "message": "Successfully unenrolled from course"}

    async def get_student_courses(self, student_id: str, tenantId: str) -> dict:
        """
        Retrieves all courses a specific student is enrolled in.
        Supports multi-tenant isolation.
        
        Returns:
            A dictionary containing the list of enriched course objects.
        """
        
        if not ObjectId.is_valid(student_id):
            return {
                "success": False,
                "message": f"Invalid student ID format: {student_id}",
                "courses": []
            }
        
        if not ObjectId.is_valid(tenantId):
            return {
                "success": False,
                "message": f"Invalid tenant ID format: {tenantId}",
                "courses": []
            }
        
        # Step 1: Find student to get enrollment list
        student = await self.students_collection.find_one({
            "_id": ObjectId(student_id),
            "tenantId": ObjectId(tenantId)
        })
        
        if not student:
            # Check for cross-tenant enrollment attempts
            student_exists = await self.students_collection.find_one({
                "_id": ObjectId(student_id)
            })
            
            if student_exists:
                return {
                    "success": False,
                    "message": "Student found but belongs to different tenant",
                    "courses": []
                }
            else:
                return {
                    "success": False,
                    "message": f"Student not found with ID: {student_id}",
                    "courses": []
                }
        
        enrolled_courses = student.get("enrolledCourses", [])
        
        if not enrolled_courses or len(enrolled_courses) == 0:
            return {
                "success": True,
                "message": "Student is not enrolled in any courses",
                "courses": []
            }
        
        # Step 2: Fetch full course details for all enrolled IDs with enrichment
        course_ids = [ObjectId(cid) for cid in enrolled_courses if ObjectId.is_valid(cid)]
        
        if not course_ids:
            return {
                "success": True,
                "message": "Student has invalid course enrollments",
                "courses": []
            }
        
        query = {"_id": {"$in": course_ids}}
        pipeline = self._get_enriched_courses_pipeline(query, 0, 100)
        
        courses = await self.collection.aggregate(pipeline).to_list(length=100)
        
        # Serialize for JSON
        courses = [self._serialize_course(c) for c in courses]
        
        return {
            "success": True,
            "message": f"Found {len(courses)} enrolled courses",
            "courses": courses
        }

    async def reorder_lessons(self, course_id: str, tenant_id: str, module_id: str, lesson_ids: List[str]) -> dict:
        """
        Reorder lessons within a specific module.
        
        Args:
            course_id: The course ID
            tenant_id: The tenant ID for validation
            module_id: The module ID containing the lessons
            lesson_ids: Ordered list of lesson IDs representing the new order
            
        Returns:
            dict with success status and updated course or error message
        """
        # Validate IDs
        if not ObjectId.is_valid(course_id):
            return {"success": False, "message": f"Invalid course ID format: {course_id}"}
        if not ObjectId.is_valid(tenant_id):
            return {"success": False, "message": f"Invalid tenant ID format: {tenant_id}"}
        
        # Find the course
        course = await self.collection.find_one({
            "_id": ObjectId(course_id),
            "tenantId": ObjectId(tenant_id)
        })
        
        if not course:
            return {"success": False, "message": "Course not found or belongs to different tenant"}
        
        # Find the module and reorder its lessons
        modules = course.get("modules", [])
        module_found = False
        
        for module in modules:
            if module.get("id") == module_id:
                module_found = True
                lessons = module.get("lessons", [])
                
                # Create a map of lesson_id -> lesson
                lesson_map = {lesson.get("id"): lesson for lesson in lessons}
                
                # Reorder lessons based on the provided order
                reordered_lessons = []
                for idx, lesson_id in enumerate(lesson_ids):
                    if lesson_id in lesson_map:
                        lesson = lesson_map[lesson_id]
                        lesson["order"] = idx
                        reordered_lessons.append(lesson)
                
                # Add any lessons not in the reorder list at the end
                for lesson in lessons:
                    if lesson.get("id") not in lesson_ids:
                        lesson["order"] = len(reordered_lessons)
                        reordered_lessons.append(lesson)
                
                module["lessons"] = reordered_lessons
                break
        
        if not module_found:
            return {"success": False, "message": f"Module not found with ID: {module_id}"}
        
        # Update the course
        update_result = await self.collection.update_one(
            {"_id": ObjectId(course_id)},
            {
                "$set": {
                    "modules": modules,
                    "updatedAt": datetime.now()
                }
            }
        )
        
        if update_result.modified_count == 0:
            return {"success": False, "message": "Failed to update course"}
        
        # Return updated course
        updated_course = await self.collection.find_one({"_id": ObjectId(course_id)})
        return {
            "success": True,
            "message": "Lessons reordered successfully",
            "course": self._serialize_course(updated_course)
        }

    async def reorder_modules(self, course_id: str, tenant_id: str, module_ids: List[str]) -> dict:
        """
        Reorder modules within a course.
        
        Args:
            course_id: The course ID
            tenant_id: The tenant ID for validation
            module_ids: Ordered list of module IDs representing the new order
            
        Returns:
            dict with success status and updated course or error message
        """
        # Validate IDs
        if not ObjectId.is_valid(course_id):
            return {"success": False, "message": f"Invalid course ID format: {course_id}"}
        if not ObjectId.is_valid(tenant_id):
            return {"success": False, "message": f"Invalid tenant ID format: {tenant_id}"}
        
        # Find the course
        course = await self.collection.find_one({
            "_id": ObjectId(course_id),
            "tenantId": ObjectId(tenant_id)
        })
        
        if not course:
            return {"success": False, "message": "Course not found or belongs to different tenant"}
        
        # Reorder modules
        modules = course.get("modules", [])
        module_map = {module.get("id"): module for module in modules}
        
        reordered_modules = []
        for idx, module_id in enumerate(module_ids):
            if module_id in module_map:
                module = module_map[module_id]
                module["order"] = idx
                reordered_modules.append(module)
        
        # Add any modules not in the reorder list at the end
        for module in modules:
            if module.get("id") not in module_ids:
                module["order"] = len(reordered_modules)
                reordered_modules.append(module)
        
        # Update the course
        update_result = await self.collection.update_one(
            {"_id": ObjectId(course_id)},
            {
                "$set": {
                    "modules": reordered_modules,
                    "updatedAt": datetime.now()
                }
            }
        )
        
        if update_result.modified_count == 0:
            return {"success": False, "message": "Failed to update course"}
        
        # Return updated course
        updated_course = await self.collection.find_one({"_id": ObjectId(course_id)})
        return {
            "success": True,
            "message": "Modules reordered successfully",
            "course": self._serialize_course(updated_course)
        }

    async def publish_course(self, course_id: str, tenant_id: str, publish: bool = True) -> dict:
        """
        Publish or unpublish a course.
        
        Args:
            course_id: The course ID
            tenant_id: The tenant ID for validation
            publish: True to publish, False to unpublish (set to draft)
            
        Returns:
            dict with success status and updated course or error message
        """
        # Validate IDs
        if not ObjectId.is_valid(course_id):
            return {"success": False, "message": f"Invalid course ID format: {course_id}"}
        if not ObjectId.is_valid(tenant_id):
            return {"success": False, "message": f"Invalid tenant ID format: {tenant_id}"}
        
        # Find the course
        course = await self.collection.find_one({
            "_id": ObjectId(course_id),
            "tenantId": ObjectId(tenant_id)
        })
        
        if not course:
            return {"success": False, "message": "Course not found or belongs to different tenant"}
        
        # Determine new status
        new_status = "published" if publish else "draft"
        current_status = course.get("status", "draft")
        
        if current_status == new_status:
            return {
                "success": True,
                "message": f"Course is already {new_status}",
                "course": self._serialize_course(course)
            }
        
        # Update the course status
        update_result = await self.collection.update_one(
            {"_id": ObjectId(course_id)},
            {
                "$set": {
                    "status": new_status,
                    "updatedAt": datetime.now(),
                    "publishedAt": datetime.now() if publish else None
                }
            }
        )
        
        if update_result.modified_count == 0:
            return {"success": False, "message": "Failed to update course status"}
        
        # Return updated course
        updated_course = await self.collection.find_one({"_id": ObjectId(course_id)})
        return {
            "success": True,
            "message": f"Course {'published' if publish else 'unpublished'} successfully",
            "course": self._serialize_course(updated_course)
        }

    async def get_enrolled_students(self, course_id: str, tenantId: str) -> dict:
        """
        Get all students enrolled in a specific course.
        
        Returns student details including enrollment info.
        """
        # Validate IDs
        if not ObjectId.is_valid(course_id):
            return {"success": False, "message": "Invalid course ID format"}
        if not ObjectId.is_valid(tenantId):
            return {"success": False, "message": "Invalid tenant ID format"}
        
        tenant_object_id = ObjectId(tenantId)
        
        # Verify course exists and belongs to tenant
        course = await self.collection.find_one({
            "_id": ObjectId(course_id),
            "tenantId": tenant_object_id
        })
        
        if not course:
            return {"success": False, "message": "Course not found or belongs to different tenant"}
        
        # Find all students who have this course in their enrolledCourses array
        cursor = self.students_collection.find({
            "tenantId": tenant_object_id,
            "enrolledCourses": course_id  # Course ID stored as string
        })
        
        students = []
        async for student in cursor:
            # Get user details for email and fullName
            user = await self.users_collection.find_one({"_id": student.get("userId")})
            
            students.append({
                "_id": str(student["_id"]),
                "id": str(student["_id"]),
                "fullName": user.get("fullName", "") if user else student.get("fullName", "Unknown"),
                "email": user.get("email", "") if user else student.get("email", ""),
                "enrolledAt": student.get("createdAt", datetime.utcnow()).isoformat() if isinstance(student.get("createdAt"), datetime) else str(student.get("createdAt", "")),
                "progress": student.get("progress", {}).get(course_id, 0) if isinstance(student.get("progress"), dict) else 0,
                "lessonsCompleted": student.get("lessonsCompleted", {}).get(course_id, 0) if isinstance(student.get("lessonsCompleted"), dict) else 0,
                "lastAccessed": student.get("lastAccessed", {}).get(course_id) if isinstance(student.get("lastAccessed"), dict) else None,
            })
        
        return {
            "success": True,
            "students": students,
            "count": len(students)
        }

# Create a single instance
course_crud = CourseCRUD()