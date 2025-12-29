from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from app.schemas.users import UserResponse

# ---------- Requests ----------


class TeacherCreate(BaseModel):
    userId: str
    qualifications: List[str] = []
    subjects: List[str] = []


class TeacherUpdate(BaseModel):
    # ---- user fields ----
    fullName: Optional[str] = None
    profileImageURL: Optional[str] = None
    contactNo: Optional[str] = None
    country: Optional[str] = None

    # ---- teacher fields ----
    qualifications: Optional[List[str]] = None
    subjects: Optional[List[str]] = None
    assignedCourses: Optional[List[str]] = None
    status: Optional[str] = None

    model_config = {"from_attributes": True}


# ---------- Response ----------


class TeacherResponse(BaseModel):
    id: str
    userId: str
    tenantId: Optional[str] = None  # include in response
    user: UserResponse  # NESTED USER
    assignedCourses: List[str] = []
    qualifications: List[str] = []
    subjects: List[str] = []
    status: str
    createdAt: datetime
    updatedAt: datetime

    model_config = {"from_attributes": True}
