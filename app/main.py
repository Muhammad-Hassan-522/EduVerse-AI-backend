from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers.roles import admins, students, super_admin, teachers

from app.routers import (
    assignment_submissions,
    assignments,
    courses,
    quiz_submissions,
    quizzes,
    student_performance,
    student_progress,
    subscription,
    tenants,
)
from app.routers.auth import admin_auth, student_auth, teacher_auth, login
from app.routers.dashboards import admin_dashboard

app = FastAPI(
    title="EduVerse AI Backend",
    description="Multi-Tenant E-Learning Platform API",
    version="1.0.0",
)


origins = [
    "http://localhost:4200",
    "http://localhost:8000",
    "http://localhost:8000/assignments/",
    "http://127.0.0.1:4200",
    "http://127.0.0.1:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "message": "EduVerse AI Backend API",
        "version": "1.0.0",
        "status": "operational",
    }


# Include routers

app.include_router(admin_auth.router)
app.include_router(student_auth.router)
app.include_router(teacher_auth.router)
app.include_router(admin_dashboard.router)

app.include_router(login.router)

app.include_router(super_admin.router)
app.include_router(admins.router)
app.include_router(students.router)
app.include_router(teachers.router)

# Student Performance
app.include_router(student_performance.router)

# Course Management
# Student Progress Management (Directly on app to avoid router conflicts)
from app.schemas.student_progress import MarkLessonCompleteRequest, CourseProgressResponse
from app.crud.student_progress import progress_crud
from app.auth.dependencies import require_role
from typing import List
from fastapi import Query, Depends, HTTPException

@app.get("/courses/progress/{courseId}", response_model=CourseProgressResponse, tags=["Student Progress"])
async def get_course_progress_top(
    courseId: str,
    tenantId: str = Query(..., alias="tenantId"),
    current_user=Depends(require_role("student"))
):
    try:
        student_id = current_user.get("user_id")
        progress = await progress_crud.get_or_create_progress(student_id, courseId, tenantId)
        return progress
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/courses/progress/mark-complete", response_model=CourseProgressResponse, tags=["Student Progress"])
async def mark_lesson_complete_top(
    data: MarkLessonCompleteRequest,
    current_user=Depends(require_role("student"))
):
    try:
        student_id = current_user.get("user_id")
        tenant_id = current_user.get("tenant_id")
        result = await progress_crud.mark_lesson_complete(
            student_id, data.courseId, tenant_id, data.lessonId
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/courses/progress/summary/all", response_model=List[CourseProgressResponse], tags=["Student Progress"])
async def get_all_progress_top(
    tenantId: str = Query(..., alias="tenantId"),
    current_user=Depends(require_role("student"))
):
    student_id = current_user.get("user_id")
    results = await progress_crud.get_student_course_progress(student_id, tenantId)
    return results

# Include other routers
app.include_router(courses.router)
app.include_router(assignments.router)
app.include_router(assignment_submissions.router)


# Tenant & Quizzes
app.include_router(tenants.router)
app.include_router(quizzes.router)
app.include_router(quiz_submissions.router)

# Subscription
app.include_router(subscription.router)
