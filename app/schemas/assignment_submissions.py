# from pydantic import BaseModel
# from typing import Optional
# from datetime import datetime


# class AssignmentSubmissionCreate(BaseModel):
#     assignmentId: str
#     courseId: str
#     fileUrl: str


# class AssignmentSubmissionResponse(BaseModel):
#     id: str
#     studentId: str
#     assignmentId: str
#     submittedAt: datetime
#     fileUrl: str
#     obtainedMarks: Optional[int] = None
#     feedback: Optional[str] = None
#     courseId: str
#     tenantId: str
#     gradedAt: Optional[datetime] = None

#     model_config = {"from_attributes": True}


# class AssignmentSubmissionUpdate(BaseModel):
#     obtainedMarks: Optional[int] = None
#     feedback: Optional[str] = None


from pydantic import BaseModel, Field, model_validator
from typing import Optional
from datetime import datetime


class AssignmentSubmissionCreate(BaseModel):
    studentId: str
    assignmentId: str
    courseId: str
    tenantId: str

    fileUrl: str = Field(..., min_length=3)

    @model_validator(mode="after")
    def validate_ids(cls, values):
        # Basic safety: IDs must not be empty strings
        for field in ["studentId", "assignmentId", "courseId", "tenantId"]:
            if not getattr(values, field):
                raise ValueError(f"{field} cannot be empty")
        return values


class AssignmentSubmissionUpdate(BaseModel):
    obtainedMarks: Optional[int] = Field(None, ge=0)
    feedback: Optional[str] = None
    gradedAt: Optional[datetime] = None

    @model_validator(mode="before")
    def convert_empty_strings_to_none(cls, data):
        if isinstance(data, dict):
            for k, v in data.items():
                if v == "":
                    data[k] = None
        return data


class AssignmentSubmissionResponse(BaseModel):
    id: str

    studentId: str
    assignmentId: str
    courseId: str
    tenantId: str

    fileUrl: str
    submittedAt: datetime

    obtainedMarks: Optional[int] = None
    feedback: Optional[str] = None
    gradedAt: Optional[datetime] = None

    model_config = {"from_attributes": True}
