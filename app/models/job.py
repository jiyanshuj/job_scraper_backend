from beanie import Document
from pydantic import BaseModel, Field
from bson import ObjectId
from typing import Optional, List
from datetime import datetime
from .base import BaseDocument, PyObjectId

class Job(BaseDocument):
    job_title: str = Field(..., max_length=255)
    job_link: str = Field(..., unique=True)
    description: Optional[str] = None
    location: Optional[str] = Field(None, max_length=255)
    job_type: Optional[str] = Field(None, max_length=50)
    posted_time: Optional[str] = Field(None, max_length=50)
    posted_date: Optional[datetime] = None
    requirements: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    salary_range: Optional[str] = Field(None, max_length=100)
    experience_level: Optional[str] = Field(None, max_length=50)
    is_active: bool = Field(default=True)
    scraped_from: str = Field(..., max_length=50)

    # Company information (denormalized for performance)
    company_name: str = Field(..., max_length=255)
    company_domain: Optional[str] = None
    company_linkedin_id: Optional[str] = Field(None, max_length=100)
    company_is_verified: bool = Field(default=False)

    # Category information (denormalized for performance)
    category_name: str = Field(..., max_length=100)
    category_description: Optional[str] = None

    # Analytics fields
    view_count: int = Field(default=0)
    application_count: int = Field(default=0)
    favorite_count: int = Field(default=0)

    class Config:
        json_encoders = {ObjectId: str}
        json_schema_extra = {
            "example": {
                "job_title": "Senior Python Developer",
                "job_link": "https://example.com/job/123",
                "description": "We are looking for a senior Python developer...",
                "location": "San Francisco, CA",
                "job_type": "Full-time",
                "skills": ["Python", "Django", "PostgreSQL"],
                "company_name": "Tech Corp",
                "category_name": "Software Development",
                "scraped_from": "LinkedIn"
            }
        }

    class Settings:
        name = "jobs"
        indexes = [
            "job_title",
            "location",
            "company_name",
            "category_name",
            "skills",
            "is_active",
            "posted_date",
            "scraped_from"
        ]

class JobCreate(BaseModel):
    job_title: str = Field(..., max_length=255)
    job_link: str = Field(..., unique=True)
    description: Optional[str] = None
    location: Optional[str] = Field(None, max_length=255)
    job_type: Optional[str] = Field(None, max_length=50)
    requirements: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    salary_range: Optional[str] = Field(None, max_length=100)
    experience_level: Optional[str] = Field(None, max_length=50)
    company_name: str = Field(..., max_length=255)
    category_name: str = Field(..., max_length=100)
    scraped_from: str = Field(..., max_length=50)

class JobUpdate(BaseModel):
    job_title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    location: Optional[str] = Field(None, max_length=255)
    job_type: Optional[str] = Field(None, max_length=50)
    requirements: Optional[str] = None
    skills: Optional[List[str]] = None
    salary_range: Optional[str] = Field(None, max_length=100)
    experience_level: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = None

class JobResponse(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    job_title: str
    job_link: str
    description: Optional[str]
    location: Optional[str]
    job_type: Optional[str]
    posted_time: Optional[str]
    posted_date: Optional[datetime]
    requirements: Optional[str]
    skills: List[str]
    salary_range: Optional[str]
    experience_level: Optional[str]
    is_active: bool
    scraped_from: str
    company_name: str
    company_domain: Optional[str]
    company_linkedin_id: Optional[str]
    company_is_verified: bool
    category_name: str
    category_description: Optional[str]
    view_count: int
    application_count: int
    favorite_count: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
