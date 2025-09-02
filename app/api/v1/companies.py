from fastapi import APIRouter, Depends, HTTPException, Query, Request
from typing import List, Optional
from app.schemas.company import CompanyCreate, CompanyResponse, CompanyUpdate
from app.models.company import TrustedCompany
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/", response_model=List[CompanyResponse])
async def get_companies(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=1000),
    search: Optional[str] = Query(None),
    is_verified: Optional[bool] = Query(None)
):
    """Get all trusted companies with filtering"""
    logger.info(f"Request received: {request.method} {request.url.path}")
    query = {}
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"industry": {"$regex": search, "$options": "i"}}
        ]
    if is_verified is not None:
        query["is_verified"] = is_verified

    companies = await TrustedCompany.find(query).skip(skip).limit(limit).to_list()
    return companies

@router.post("/", response_model=CompanyResponse)
async def create_company(request: Request, company: CompanyCreate):
    """Create a new trusted company"""
    logger.info(f"Request received: {request.method} {request.url.path}")
    # Check if company already exists
    existing = await TrustedCompany.find_one({"name": company.name})
    if existing:
        raise HTTPException(status_code=400, detail="Company already exists")

    db_company = TrustedCompany(**company.dict())
    await db_company.insert()
    return db_company

@router.get("/{company_id}", response_model=CompanyResponse)
async def get_company(request: Request, company_id: str):
    """Get company by ID"""
    logger.info(f"Request received: {request.method} {request.url.path}")
    try:
        company = await TrustedCompany.get(company_id)
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        return company
    except Exception:
        raise HTTPException(status_code=404, detail="Company not found")

@router.put("/{company_id}", response_model=CompanyResponse)
async def update_company(request: Request, company_id: str, company_update: CompanyUpdate):
    """Update company information"""
    logger.info(f"Request received: {request.method} {request.url.path}")
    try:
        company = await TrustedCompany.get(company_id)
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")

        update_data = company_update.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(company, key, value)

        await company.save()
        return company
    except Exception:
        raise HTTPException(status_code=404, detail="Company not found")

@router.delete("/{company_id}")
async def delete_company(request: Request, company_id: str):
    """Delete a company"""
    logger.info(f"Request received: {request.method} {request.url.path}")
    try:
        company = await TrustedCompany.get(company_id)
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")

        await company.delete()
        return {"message": "Company deleted successfully"}
    except Exception:
        raise HTTPException(status_code=404, detail="Company not found")
