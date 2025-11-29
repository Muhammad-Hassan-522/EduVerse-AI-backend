from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class AssignmentSubmissionCreate(BaseModel):
    studentId: str
    assignmentId: str
    fileUrl: str
    courseId: str
    tenantId: str

class AssignmentSubmissionResponse(BaseModel):
    id: str
    studentId: str
    assignmentId: str
    submittedAt: datetime
    fileUrl: str
    obtainedMarks: Optional[int] = None
    feedback: Optional[str] = None
    courseId: str
    tenantId: str
    gradedAt: Optional[datetime] = None

    model_config = {
        "from_attributes": True
    }