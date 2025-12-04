from typing import Optional
from datetime import datetime
from pydantic import EmailStr, BaseModel, Field, HttpUrl, model_validator


# -------------------------
# Schema: Used when creating a tenant
# -------------------------
class TenantCreate(BaseModel):
    tenantName: str = Field(..., min_length=2, max_length=100, json_schema_extra={"example": "EduVerse School"})
    tenantLogoUrl: Optional[HttpUrl] = Field(None, json_schema_extra={"example": "https://example.com/logo.png"})
    adminEmail: EmailStr = Field(..., json_schema_extra={"example": "admin@example.com"})
    subscriptionId: str = Field(..., json_schema_extra={"example": "6931699f9fbdab6e6528c050"})

# -------------------------
# Schema: Used when updating tenant information
# -------------------------
class TenantUpdate(BaseModel):
    tenantName: Optional[str] = Field(None, min_length=2, max_length=100)
    tenantLogoUrl: Optional[HttpUrl] = None
    status: Optional[str] = None
    subscriptionId: Optional[str] = None

    # It is completely optional as the validation is being handled in crud file, but it is a good practice to write validator, so I am keeping this.
    # It runs BEFORE Pydantic validates the body
    # It checks all fields in the request body
    # If a field has an empty string " " → it converts it to None
    @model_validator(mode="before")
    def empty_strings_to_none(cls, data):
        if isinstance(data, dict):
            for key, val in data.items():
                if val == "":
                    data[key] = None  # do NOT overwrite
        return data

# -------------------------
# Schema: Response object returned to the frontend
# -------------------------
class TenantResponse(BaseModel):
    id: str
    tenantName: str
    tenantLogoUrl: Optional[HttpUrl] = None
    adminEmail: EmailStr
    status: str
    subscriptionId: Optional[str]
    createdAt: datetime
    updatedAt: Optional[datetime] = None
