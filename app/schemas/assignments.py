from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class AssignmentCreate(BaseModel):
    courseId: str = Field(..., description="Course ObjectId as string")
    teacherId: str = Field(..., description="Teacher ObjectId as string")
    title: str
    description: Optional[str] = None
    dueDate: datetime
    totalMarks: int = 100
    passingMarks: int = 50
    status: str = "active"
    dueTime: Optional[datetime] = None
    fileUrl: Optional[str] = None
    tenantId: str
    allowedFormats: List[str] = ["pdf", "docx"]


class AssignmentUpdate(BaseModel):
    title: Optional[str]
    description: Optional[str]
    dueDate: Optional[datetime]
    totalMarks: Optional[int]
    passingMarks: Optional[int]
    status: Optional[str]
    dueTime: Optional[datetime]
    fileUrl: Optional[str]
    allowedFormats: Optional[List[str]]


class AssignmentResponse(BaseModel):
    id: str
    courseId: str
    teacherId: str
    tenantId: str
    title: str
    description: Optional[str]
    dueDate: datetime
    dueTime: Optional[datetime]
    uploadedAt: datetime
    updatedAt: datetime
    totalMarks: int
    passingMarks: int
    status: str
    fileUrl: Optional[str]
    allowedFormats: List[str]

    model_config = {
        "from_attributes": True
    }
