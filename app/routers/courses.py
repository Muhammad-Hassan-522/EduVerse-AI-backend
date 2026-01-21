

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional
from app.schemas.courses import (
    CourseCreate, 
    CourseUpdate, 
    CourseResponse, 
    CourseEnrollment,
    ReorderLessonsRequest,
    ReorderModulesRequest,
    PublishCourseRequest
)
from app.crud.courses import course_crud

from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/courses", tags=["courses"], dependencies=[Depends(get_current_user)])


@router.post("/", response_model=CourseResponse, status_code=201)
async def create_course(course: CourseCreate):
    """
    Create a new course.
    
      Now validates teacher and tenant exist in database
      Automatically updates teacher's assignedCourses array
    
    Both teacherId and tenantId must be provided in the request body.
    
    Returns:
    - 400: Invalid IDs, teacher/tenant not found, or belongs to different tenant
    - 201: Course created successfully
    """
    try:
        created_course = await course_crud.create_course(course)
        return created_course
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=List[CourseResponse])
async def get_courses(
    tenantId: str = Query(..., description="Tenant ID (required)"),  
    teacher_id: Optional[str] = Query(None, description="Filter by teacher ID"),
    status: Optional[str] = Query(None, description="Filter by status (case-insensitive)"),
    category: Optional[str] = Query(None, description="Filter by category (case-insensitive)"),
    search: Optional[str] = Query(None, description="Search in title/description/category/courseCode"),
    skip: int = Query(0, ge=0, description="Number of courses to skip (pagination)"),
    limit: int = Query(100, ge=1, le=100, description="Maximum courses to return")
):
    """
    Get all courses with optional filters.
    
    tenantId is required as a query parameter.
    All text filters are case-insensitive.
    
    Returns:
    - 400: Invalid tenant ID or teacher ID format
    - 200: List of courses (can be empty)
    """
    result = await course_crud.get_all_courses(
        tenantId=tenantId,
        teacher_id=teacher_id,
        status=status,
        category=category,
        search=search,
        skip=skip,
        limit=limit
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    return result["courses"]


@router.get("/{course_id}", response_model=CourseResponse)
async def get_course(
    course_id: str,
    tenantId: str = Query(..., description="Tenant ID (required)") 
):
    """
    Get a single course by its ID.
    
    tenantId is required as a query parameter.
    
    Returns:
    - 400: Invalid course ID or tenant ID format
    - 403: Course belongs to different tenant
    - 404: Course not found
    - 200: Course details
    """
    result = await course_crud.get_course_by_id(course_id, tenantId)
    
    if not result["success"]:
        message = result["message"]
        
        if "Invalid" in message and "format" in message:
            raise HTTPException(status_code=400, detail=message)
        elif "different tenant" in message:
            raise HTTPException(status_code=403, detail=message)
        elif "not found" in message:
            raise HTTPException(status_code=404, detail=message)
        else:
            raise HTTPException(status_code=400, detail=message)
    
    return result["course"]


@router.put("/{course_id}", response_model=CourseResponse)
async def update_course(
    course_id: str,
    course_update: CourseUpdate,
    tenantId: str = Query(..., description="Tenant ID (required)") 
):
    """
    Update a course's information.
    
    tenantId is required as a query parameter.
    Only provided fields will be updated.
    
    Returns:
    - 400: Invalid course ID or tenant ID format
    - 404: Course not found or belongs to different tenant
    - 200: Updated course
    """
    updated_course = await course_crud.update_course(course_id, tenantId, course_update)
    
    if not updated_course:
        raise HTTPException(
            status_code=404, 
            detail="Course not found or belongs to different tenant"
        )
    
    return updated_course


@router.delete("/{course_id}", status_code=204)
async def delete_course(
    course_id: str,
    tenantId: str = Query(..., description="Tenant ID (required)")  
):
    """
    Delete a course permanently.
    
     UPDATED: Now automatically:
    - Removes course from teacher's assignedCourses array
    - Removes course from all enrolled students' enrolledCourses arrays
    
    tenantId is required as a query parameter.
    
    Returns:
    - 400: Invalid course ID or tenant ID format
    - 404: Course not found or belongs to different tenant
    - 204: Successfully deleted (No Content)
    """
    result = await course_crud.delete_course(course_id, tenantId)
    
    if not result["success"]:
        message = result["message"]
        
        if "Invalid" in message and "format" in message:
            raise HTTPException(status_code=400, detail=message)
        elif "not found" in message or "different tenant" in message:
            raise HTTPException(status_code=404, detail=message)
        else:
            raise HTTPException(status_code=400, detail=message)
    
    return None


# Enrollment Endpoints

@router.post("/enroll", status_code=200)
async def enroll_in_course(enrollment: CourseEnrollment):
    """
    Enroll a student in a course.
    
    Requires studentId, courseId, and tenantId in request body.
    Validates that both student and course exist and belong to the same tenant.
    
    Returns:
    - 400: Invalid IDs, already enrolled, or validation error
    - 200: Successfully enrolled
    """
    result = await course_crud.enroll_student(
        enrollment.courseId, 
        enrollment.studentId, 
        enrollment.tenantId
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    return result


@router.post("/unenroll", status_code=200)
async def unenroll_from_course(enrollment: CourseEnrollment):
    """
    Remove a student from a course.
    
    Requires studentId, courseId, and tenantId in request body.
    Validates that the student is actually enrolled.
    
    Returns:
    - 400: Invalid IDs, not enrolled, or validation error
    - 200: Successfully unenrolled
    """
    result = await course_crud.unenroll_student(
        enrollment.courseId, 
        enrollment.studentId, 
        enrollment.tenantId
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    return result


@router.get("/{course_id}/students")
async def get_course_students(
    course_id: str,
    tenantId: str = Query(..., description="Tenant ID (required)")
):
    """
    Get all students enrolled in a specific course.
    
    tenantId is required as a query parameter.
    
    Returns:
    - 400: Invalid course ID or tenant ID format
    - 404: Course not found or belongs to different tenant
    - 200: List of enrolled students
    """
    result = await course_crud.get_enrolled_students(course_id, tenantId)
    
    if not result["success"]:
        message = result["message"]
        
        if "Invalid" in message and "format" in message:
            raise HTTPException(status_code=400, detail=message)
        elif "not found" in message or "different tenant" in message:
            raise HTTPException(status_code=404, detail=message)
        else:
            raise HTTPException(status_code=400, detail=message)
    
    return result["students"]


@router.delete("/{course_id}/students/{student_id}", status_code=200)
async def unenroll_student_from_course(
    course_id: str,
    student_id: str,
    tenantId: str = Query(..., description="Tenant ID (required)")
):
    """
    Unenroll a specific student from a course.
    
    tenantId is required as a query parameter.
    
    Returns:
    - 400: Invalid IDs, not enrolled, or validation error
    - 200: Successfully unenrolled
    """
    result = await course_crud.unenroll_student(course_id, student_id, tenantId)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    return result


@router.get("/student/{student_id}", response_model=List[CourseResponse])
async def get_student_courses(
    student_id: str,
    tenantId: str = Query(..., description="Tenant ID (required)")  
):
    """
    Get all courses a student is enrolled in.
    
    tenantId is required as a query parameter.
    
    Returns:
    - 400: Invalid student ID or tenant ID format
    - 403: Student belongs to different tenant
    - 404: Student not found
    - 200: List of courses (can be empty if not enrolled)
    """
    result = await course_crud.get_student_courses(student_id, tenantId)
    
    if not result["success"]:
        message = result["message"]
        
        if "Invalid" in message and "format" in message:
            raise HTTPException(status_code=400, detail=message)
        elif "different tenant" in message:
            raise HTTPException(status_code=403, detail=message)
        elif "not found" in message:
            raise HTTPException(status_code=404, detail=message)
        else:
            raise HTTPException(status_code=400, detail=message)
    
    return result["courses"]


# Course Builder Endpoints

@router.patch("/{course_id}/reorder/lessons", response_model=CourseResponse)
async def reorder_lessons(
    course_id: str,
    reorder_request: ReorderLessonsRequest,
    tenantId: str = Query(..., description="Tenant ID (required)")
):
    """
    Reorder lessons within a specific module.
    
    Requires moduleId and lessonIds (ordered list) in request body.
    tenantId is required as a query parameter.
    
    Returns:
    - 400: Invalid IDs or module not found
    - 404: Course not found or belongs to different tenant
    - 200: Updated course with reordered lessons
    """
    result = await course_crud.reorder_lessons(
        course_id,
        tenantId,
        reorder_request.moduleId,
        reorder_request.lessonIds
    )
    
    if not result["success"]:
        message = result["message"]
        
        if "Invalid" in message and "format" in message:
            raise HTTPException(status_code=400, detail=message)
        elif "not found" in message:
            raise HTTPException(status_code=404, detail=message)
        else:
            raise HTTPException(status_code=400, detail=message)
    
    return result["course"]


@router.patch("/{course_id}/reorder/modules", response_model=CourseResponse)
async def reorder_modules(
    course_id: str,
    reorder_request: ReorderModulesRequest,
    tenantId: str = Query(..., description="Tenant ID (required)")
):
    """
    Reorder modules within a course.
    
    Requires moduleIds (ordered list) in request body.
    tenantId is required as a query parameter.
    
    Returns:
    - 400: Invalid course ID or tenant ID format
    - 404: Course not found or belongs to different tenant
    - 200: Updated course with reordered modules
    """
    result = await course_crud.reorder_modules(
        course_id,
        tenantId,
        reorder_request.moduleIds
    )
    
    if not result["success"]:
        message = result["message"]
        
        if "Invalid" in message and "format" in message:
            raise HTTPException(status_code=400, detail=message)
        elif "not found" in message:
            raise HTTPException(status_code=404, detail=message)
        else:
            raise HTTPException(status_code=400, detail=message)
    
    return result["course"]


@router.post("/{course_id}/publish", response_model=CourseResponse)
async def publish_course(
    course_id: str,
    publish_request: PublishCourseRequest,
    tenantId: str = Query(..., description="Tenant ID (required)")
):
    """
    Publish or unpublish a course.
    
    Set publish=true to publish, publish=false to unpublish (set to draft).
    tenantId is required as a query parameter.
    
    Returns:
    - 400: Invalid course ID or tenant ID format
    - 404: Course not found or belongs to different tenant
    - 200: Updated course with new status
    """
    result = await course_crud.publish_course(
        course_id,
        tenantId,
        publish_request.publish
    )
    
    if not result["success"]:
        message = result["message"]
        
        if "Invalid" in message and "format" in message:
            raise HTTPException(status_code=400, detail=message)
        elif "not found" in message:
            raise HTTPException(status_code=404, detail=message)
        else:
            raise HTTPException(status_code=400, detail=message)
    
    return result["course"]