from fastapi import APIRouter
from app.crud.student_performance import StudentPerformanceCRUD

router = APIRouter(prefix="/studentPerformance", tags=["Student Performance"])


# -------------------- GLOBAL LEADERBOARDS --------------------
@router.get("/leaderboard/global-full")
async def global_full():
    return await StudentPerformanceCRUD.global_full()


@router.get("/leaderboard/global-top5")
async def global_top5():
    return await StudentPerformanceCRUD.global_top5()


# -------------------- TENANT LEADERBOARDS --------------------
@router.get("/{tenantId}/leaderboard")
async def tenant_full(tenantId: str):
    return await StudentPerformanceCRUD.tenant_full(tenantId)


@router.get("/{tenantId}/leaderboard-top5")
async def tenant_top5(tenantId: str):
    return await StudentPerformanceCRUD.tenant_top5(tenantId)


# -------------------- STUDENT PERFORMANCE --------------------
@router.get("/{tenantId}/{studentId}")
async def get_student_performance(tenantId: str, studentId: str):
    return await StudentPerformanceCRUD.get_student_performance(studentId, tenantId)


# -------------------- BADGES --------------------
@router.get("/{tenantId}/{studentId}/badges")
async def get_badges(tenantId: str, studentId: str):
    return await StudentPerformanceCRUD.view_badges(studentId, tenantId)


@router.post("/{tenantId}/{studentId}/badges")
async def add_badge(tenantId: str, studentId: str, badge: dict):
    return await StudentPerformanceCRUD.add_badge(studentId, tenantId, badge)


# -------------------- CERTIFICATES --------------------
@router.get("/{tenantId}/{studentId}/certificates")
async def get_certificates(tenantId: str, studentId: str):
    return await StudentPerformanceCRUD.view_certificates(studentId, tenantId)


@router.post("/{tenantId}/{studentId}/certificates")
async def add_certificate(tenantId: str, studentId: str, cert: dict):
    return await StudentPerformanceCRUD.add_certificate(studentId, tenantId, cert)


# -------------------- COURSE STATS --------------------
@router.get("/{tenantId}/{studentId}/course-stats")
async def course_stats(tenantId: str, studentId: str):
    return await StudentPerformanceCRUD.get_course_stats(studentId, tenantId)


@router.post("/{tenantId}/{studentId}/course-progress/{courseId}")
async def update_course_progress(tenantId: str, studentId: str, courseId: str, completion: int, lastActive: str):
    return await StudentPerformanceCRUD.update_course_progress(studentId, tenantId, courseId, completion, lastActive)


# -------------------- WEEKLY TIME --------------------
@router.post("/{tenantId}/{studentId}/weekly-time")
async def weekly_time(tenantId: str, studentId: str, weekStart: str, minutes: int):
    return await StudentPerformanceCRUD.add_weekly_time(studentId, tenantId, weekStart, minutes)


# -------------------- POINTS --------------------
@router.post("/{tenantId}/{studentId}/add-points")
async def add_points(tenantId: str, studentId: str, points: int):
    return await StudentPerformanceCRUD.add_points(studentId, tenantId, points)
