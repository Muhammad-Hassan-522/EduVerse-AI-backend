

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from bson import ObjectId

class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, _schema_generator):
        return {"type": "string"}

# Schema for a single course module (title, description, content, etc.)
class ModuleSchema(BaseModel):
    title: str
    description: Optional[str] = None
    content: Optional[str] = None
    order: int = 0

# Base schema containing shared fields for all course-related operations
class CourseBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = None
    category: str
    level: str = "Beginner"  # Possible values: Beginner, Intermediate, Advanced
    status: str = "Active"  # Possible values: Active, Inactive, Upcoming, Completed
    courseCode: Optional[str] = None
    duration: Optional[str] = None
    thumbnailUrl: Optional[str] = ""
    modules: List[ModuleSchema] = []

# Schema for creating a new course (requires IDs for teacher and tenant)
class CourseCreate(CourseBase):
    teacherId: str
    tenantId: str
    enrolledStudents: int = 0

# Schema for updating an existing course (all fields are optional)
class CourseUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=200)
    description: Optional[str] = None
    category: Optional[str] = None
    level: Optional[str] = None
    status: Optional[str] = None
    courseCode: Optional[str] = None  
    duration: Optional[str] = None
    thumbnailUrl: Optional[str] = None
    modules: Optional[List[ModuleSchema]] = None
    teacherId: Optional[str] = None
    tenantId: Optional[str] = None

# Schema for the full course data as returned in API responses
class CourseResponse(CourseBase):
    id: str = Field(alias="_id")
    teacherId: str
    tenantId: str
    instructorName: Optional[str] = None
    enrolledStudents: int = 0
    createdAt: datetime
    updatedAt: datetime

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}

# Schema for enrolling a student into a specific course
class CourseEnrollment(BaseModel):
    studentId: str
    courseId: str
    tenantId: str  

# Schema for course data including student progress tracking
class CourseWithProgress(CourseResponse):
    progress: Optional[int] = 0  # Percentage (0-100)
    lessonsCompleted: Optional[int] = 0
    totalLessons: Optional[int] = 0
    nextLesson: Optional[str] = None