from beanie import Document
from pydantic import BaseModel, Field
from bson import ObjectId
from typing import Optional, List
from datetime import datetime
from .base import BaseDocument, PyObjectId

class TrustedCompany(BaseDocument):
    name: str = Field(..., max_length=255, unique=True)
    domain: Optional[str] = Field(None, max_length=255)
    linkedin_company_id: Optional[str] = Field(None, max_length=100)
    is_verified: bool = Field(default=False)

    # Additional company information
    description: Optional[str] = None
    industry: Optional[str] = Field(None, max_length=100)
    company_size: Optional[str] = Field(None, max_length=50)
    headquarters: Optional[str] = Field(None, max_length=255)
    website: Optional[str] = None

    # Analytics
    total_jobs_posted: int = Field(default=0)
    active_jobs_count: int = Field(default=0)

    class Config:
        json_encoders = {ObjectId: str}
        json_schema_extra = {
            "example": {
                "name": "Google",
                "domain": "google.com",
                "linkedin_company_id": "google",
                "is_verified": True,
                "industry": "Technology",
                "company_size": "10000+",
                "headquarters": "Mountain View, CA"
            }
        }

    class Settings:
        name = "trusted_companies"
        indexes = [
            "name",
            "domain",
            "is_verified",
            "industry"
        ]

class CompanyCreate(BaseModel):
    name: str = Field(..., max_length=255)
    domain: Optional[str] = Field(None, max_length=255)
    linkedin_company_id: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    industry: Optional[str] = Field(None, max_length=100)
    company_size: Optional[str] = Field(None, max_length=50)
    headquarters: Optional[str] = Field(None, max_length=255)
    website: Optional[str] = None

class CompanyUpdate(BaseModel):
    domain: Optional[str] = Field(None, max_length=255)
    linkedin_company_id: Optional[str] = Field(None, max_length=100)
    is_verified: Optional[bool] = None
    description: Optional[str] = None
    industry: Optional[str] = Field(None, max_length=100)
    company_size: Optional[str] = Field(None, max_length=50)
    headquarters: Optional[str] = Field(None, max_length=255)
    website: Optional[str] = None

class CompanyResponse(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    name: str
    domain: Optional[str]
    linkedin_company_id: Optional[str]
    is_verified: bool
    description: Optional[str]
    industry: Optional[str]
    company_size: Optional[str]
    headquarters: Optional[str]
    website: Optional[str]
    total_jobs_posted: int
    active_jobs_count: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
