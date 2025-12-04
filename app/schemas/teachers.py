from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime

class TeacherCreate(BaseModel):
    fullName: str
    email: EmailStr
    password: str
    profileImageURL: Optional[str] = ""
    assignedCourses: List[str] = []
    contactNo: Optional[str]
    country: Optional[str]
    status: str = "active"
    role: str = "teacher"
    qualifications: List[str] = []
    subjects: List[str] = []
    tenantId: str

class TeacherUpdate(BaseModel):
    fullName: Optional[str]
    email: Optional[EmailStr]
    profileImageURL: Optional[str]
    assignedCourses: Optional[List[str]]
    contactNo: Optional[str]
    country: Optional[str]
    status: Optional[str]
    qualifications: Optional[List[str]]
    subjects: Optional[List[str]]

class TeacherResponse(BaseModel):
    id: str
    fullName: str
    email: str
    profileImageURL: str
    assignedCourses: List[str]
    contactNo: Optional[str]
    country: Optional[str]
    status: str
    role: str
    createdAt: datetime
    updatedAt: datetime
    lastLogin: Optional[datetime]
    qualifications: List[str]
    subjects: List[str]
    tenantId: str

    model_config = {"from_attributes": True}

class ChangePassword(BaseModel):
    oldPassword: str
    newPassword: str
