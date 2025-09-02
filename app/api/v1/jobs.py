from fastapi import APIRouter, Depends, HTTPException, Query, Request
from typing import List, Optional
from app.schemas.job import JobCreate, JobResponse, JobUpdate
from app.services.job_service import JobService
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/", response_model=List[JobResponse])
async def get_jobs(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=1000),
    category: Optional[str] = Query(None),
    job_type: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
):
    """Fetch jobs with filtering and pagination"""
    logger.info(f"Request received: {request.method} {request.url.path}")
    job_service = JobService()
    jobs = await job_service.get_jobs(
        skip=skip, limit=limit, category=category,
        job_type=job_type, location=location, search=search
    )
    return jobs

@router.get("/{job_id}", response_model=JobResponse)
async def get_job(request: Request, job_id: str):
    """Get detailed job information"""
    logger.info(f"Request received: {request.method} {request.url.path}")
    job_service = JobService()
    job = await job_service.get_job_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@router.post("/", response_model=JobResponse)
async def create_job(request: Request, job: JobCreate):
    """Create a new job manually (admin only)"""
    logger.info(f"Request received: {request.method} {request.url.path}")
    job_service = JobService()
    
    # Validate company
    if not await job_service.validate_trusted_company(job.company_name):
        raise HTTPException(status_code=400, detail="Company not in trusted list")
    
    created_job = await job_service.create_job(job)
    return created_job

@router.put("/{job_id}", response_model=JobResponse)
async def update_job(request: Request, job_id: str, job_update: JobUpdate):
    """Update existing job"""
    logger.info(f"Request received: {request.method} {request.url.path}")
    job_service = JobService()
    updated_job = await job_service.update_job(job_id, job_update)
    if not updated_job:
        raise HTTPException(status_code=404, detail="Job not found")
    return updated_job

@router.delete("/{job_id}")
async def delete_job(request: Request, job_id: str):
    """Soft delete a job"""
    logger.info(f"Request received: {request.method} {request.url.path}")
    job_service = JobService()
    success = await job_service.delete_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"message": "Job deleted successfully"}
