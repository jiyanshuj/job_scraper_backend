from beanie import Document
from pydantic import BaseModel, Field
from bson import ObjectId
from typing import Optional
from datetime import datetime
from .base import BaseDocument, PyObjectId

class Category(BaseDocument):
    name: str = Field(..., max_length=100, unique=True)
    description: Optional[str] = None
    is_active: bool = Field(default=True)

    # Analytics
    total_jobs_count: int = Field(default=0)
    active_jobs_count: int = Field(default=0)

    class Config:
        json_encoders = {ObjectId: str}
        json_schema_extra = {
            "example": {
                "name": "Software Development",
                "description": "Jobs related to software development and programming",
                "is_active": True
            }
        }

    class Settings:
        name = "categories"
        indexes = [
            "name",
            "is_active"
        ]

class CategoryCreate(BaseModel):
    name: str = Field(..., max_length=100)
    description: Optional[str] = None

class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    is_active: Optional[bool] = None

class CategoryResponse(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    name: str
    description: Optional[str]
    is_active: bool
    total_jobs_count: int
    active_jobs_count: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
