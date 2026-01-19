# from pydantic import BaseModel
# from typing import List, Optional
# from datetime import datetime


# class AssignmentCreate(BaseModel):
#     courseId: str
#     title: str
#     description: Optional[str] = None
#     dueDate: datetime
#     totalMarks: int = 100
#     passingMarks: int = 50
#     status: str = "active"
#     dueTime: Optional[datetime] = None
#     fileUrl: Optional[str] = None
#     allowedFormats: List[str] = ["pdf", "docx"]


# class AssignmentUpdate(BaseModel):
#     title: Optional[str] = None
#     description: Optional[str] = None
#     dueDate: Optional[datetime] = None
#     totalMarks: Optional[int] = None
#     passingMarks: Optional[int] = None
#     status: Optional[str] = None
#     dueTime: Optional[datetime] = None
#     fileUrl: Optional[str] = None
#     allowedFormats: Optional[List[str]] = None


# class AssignmentResponse(BaseModel):
#     id: str
#     courseId: str
#     teacherId: str
#     tenantId: str
#     title: str
#     description: Optional[str]
#     dueDate: datetime
#     dueTime: Optional[datetime]
#     uploadedAt: datetime
#     updatedAt: datetime
#     totalMarks: int
#     passingMarks: int
#     status: str
#     fileUrl: Optional[str]
#     allowedFormats: List[str]

#     model_config = {"from_attributes": True}


from pydantic import BaseModel, Field, model_validator
from typing import List, Optional
from datetime import datetime


class AssignmentCreate(BaseModel):
    courseId: str
    # teacherId: str
    # tenantId: str

    title: str = Field(..., min_length=3)
    description: Optional[str] = None

    dueDate: datetime
    dueTime: Optional[datetime] = None

    totalMarks: int = Field(100, ge=1)
    passingMarks: int = Field(50, ge=0)

    status: str = Field("active", json_schema_extra={"example": "active"})
    fileUrl: Optional[str] = None
    allowedFormats: List[str] = Field(default_factory=lambda: ["pdf", "docx"])

    @model_validator(mode="after")
    def validate_marks(cls, values):
        if values.passingMarks > values.totalMarks:
            raise ValueError("passingMarks cannot be greater than totalMarks")
        return values


class AssignmentUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3)
    description: Optional[str] = None

    dueDate: Optional[datetime] = None
    dueTime: Optional[datetime] = None

    totalMarks: Optional[int] = Field(None, ge=1)
    passingMarks: Optional[int] = Field(None, ge=0)

    status: Optional[str] = Field(None, json_schema_extra={"example": "inactive"})
    fileUrl: Optional[str] = None
    allowedFormats: Optional[List[str]] = None

    @model_validator(mode="before")
    def convert_empty_strings_to_none(cls, data):
        if isinstance(data, dict):
            for key, value in data.items():
                if value == "":
                    data[key] = None
        return data

    @model_validator(mode="after")
    def validate_marks(cls, values):
        if (
            values.totalMarks is not None
            and values.passingMarks is not None
            and values.passingMarks > values.totalMarks
        ):
            raise ValueError("passingMarks cannot be greater than totalMarks")
        return values


class AssignmentResponse(BaseModel):
    id: str
    courseId: str
    teacherId: str
    tenantId: str

    title: str
    description: Optional[str]

    dueDate: datetime
    dueTime: Optional[datetime]

    totalMarks: int
    passingMarks: int
    status: str

    fileUrl: Optional[str]
    allowedFormats: List[str]

    uploadedAt: datetime
    updatedAt: datetime

    model_config = {"from_attributes": True}
