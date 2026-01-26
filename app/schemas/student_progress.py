from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class LessonProgress(BaseModel):
    lessonId: str
    completed: bool = False
    completedAt: Optional[datetime] = None
    lastViewedAt: Optional[datetime] = None

class CourseProgress(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    studentId: str
    courseId: str
    tenantId: str
    completedLessons: List[str] = []  # List of lesson IDs
    progressPercentage: int = 0
    isCompleted: bool = False
    lastAccessedAt: datetime = Field(default_factory=datetime.utcnow)
    enrollmentDate: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True

class MarkLessonCompleteRequest(BaseModel):
    lessonId: str
    courseId: str

class CourseProgressResponse(BaseModel):
    courseId: str
    progressPercentage: int
    completedLessons: List[str]
    isCompleted: bool
    lastAccessedAt: datetime
