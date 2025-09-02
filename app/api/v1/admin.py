from fastapi import APIRouter, HTTPException, Query, Request
from typing import List, Optional
from app.schemas.category import CategoryCreate, CategoryResponse, CategoryUpdate
from app.models.category import Category
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/categories", response_model=List[CategoryResponse])
async def get_categories(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=1000),
    is_active: Optional[bool] = Query(None)
):
    """Get all categories with optional filtering"""
    logger.info(f"Request received: {request.method} {request.url.path}")
    query = {}
    if is_active is not None:
        query["is_active"] = is_active

    categories = await Category.find(query).skip(skip).limit(limit).to_list()
    return categories

@router.post("/categories", response_model=CategoryResponse)
async def create_category(request: Request, category: CategoryCreate):
    """Create a new category"""
    logger.info(f"Request received: {request.method} {request.url.path}")
    existing = await Category.find_one({"name": category.name})
    if existing:
        raise HTTPException(status_code=400, detail="Category already exists")

    db_category = Category(**category.dict())
    await db_category.insert()
    return db_category

@router.get("/categories/{category_id}", response_model=CategoryResponse)
async def get_category(request: Request, category_id: str):
    """Get category by ID"""
    logger.info(f"Request received: {request.method} {request.url.path}")
    category = await Category.get(category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category

@router.put("/categories/{category_id}", response_model=CategoryResponse)
async def update_category(request: Request, category_id: str, category_update: CategoryUpdate):
    """Update category information"""
    logger.info(f"Request received: {request.method} {request.url.path}")
    category = await Category.get(category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    update_data = category_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(category, key, value)

    await category.save()
    return category

@router.delete("/categories/{category_id}")
async def delete_category(request: Request, category_id: str):
    """Delete a category"""
    logger.info(f"Request received: {request.method} {request.url.path}")
    category = await Category.get(category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    await category.delete()
    return {"message": "Category deleted successfully"}
