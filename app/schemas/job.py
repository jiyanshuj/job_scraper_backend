from pydantic import BaseModel, Field
from typing import List, Optional
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
    def __get_pydantic_json_schema__(cls, core_schema, handler):
        return {"type": "string"}

class JobBase(BaseModel):
    job_title: str
    job_link: str
    description: Optional[str] = None
    location: Optional[str] = None
    job_type: Optional[str] = None
    posted_time: Optional[str] = None
    requirements: Optional[str] = None
    skills: Optional[List[str]] = None
    salary_range: Optional[str] = None
    experience_level: Optional[str] = None

class JobCreate(JobBase):
    company_name: str
    category_name: str
    scraped_from: str

class JobUpdate(JobBase):
    pass

class JobResponse(JobBase):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    posted_date: Optional[datetime] = None
    is_active: bool
    scraped_from: str
    company_name: str
    company_domain: Optional[str] = None
    company_linkedin_id: Optional[str] = None
    company_is_verified: bool = False
    category_name: str
    category_description: Optional[str] = None
    view_count: int = 0
    application_count: int = 0
    favorite_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str}
    }
