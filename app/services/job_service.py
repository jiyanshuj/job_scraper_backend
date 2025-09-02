from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List, Optional, Dict, Any
from bson import ObjectId
from datetime import datetime
import logging
from app.models.job import Job, JobCreate, JobUpdate
from app.models.company import TrustedCompany
from app.core.database import get_database

logger = logging.getLogger(__name__)

class JobService:
    def __init__(self, db: AsyncIOMotorDatabase = None):
        self.db = db or get_database()

    async def get_jobs(self, skip: int = 0, limit: int = 100,
                      category: Optional[str] = None,
                      job_type: Optional[str] = None,
                      location: Optional[str] = None,
                      search: Optional[str] = None,
                      company: Optional[str] = None,
                      is_active: bool = True) -> List[Job]:

        query = {"is_active": is_active}

        if category:
            query["category_name"] = {"$regex": category, "$options": "i"}

        if job_type:
            query["job_type"] = job_type

        if location:
            query["location"] = {"$regex": location, "$options": "i"}

        if company:
            query["company_name"] = {"$regex": company, "$options": "i"}

        if search:
            search_query = {
                "$or": [
                    {"job_title": {"$regex": search, "$options": "i"}},
                    {"description": {"$regex": search, "$options": "i"}},
                    {"skills": {"$in": [search.lower()]}}
                ]
            }
            query.update(search_query)

        cursor = self.db.jobs.find(query).skip(skip).limit(limit).sort("posted_date", -1)
        jobs = []
        async for job_doc in cursor:
            jobs.append(Job(**job_doc))

        return jobs

    async def create_job(self, job_data: JobCreate) -> Job:
        # Get or create company
        company = await self._get_or_create_company(job_data.company_name)

        job_dict = job_data.dict()
        job_dict.update({
            "company_domain": company.domain if company else None,
            "company_linkedin_id": company.linkedin_company_id if company else None,
            "company_is_verified": company.is_verified if company else False,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        })

        job = Job(**job_dict)
        await job.insert()

        # Update company job counts
        if company:
            await self._update_company_job_counts(company.name)

        logger.info(f"Created job: {job.job_title} at {job.company_name}")
        return job

    async def get_job_by_id(self, job_id: str) -> Optional[Job]:
        try:
            job = await Job.get(ObjectId(job_id))
            return job
        except Exception as e:
            logger.error(f"Error getting job {job_id}: {e}")
            return None

    async def update_job(self, job_id: str, job_update: JobUpdate) -> Optional[Job]:
        job = await self.get_job_by_id(job_id)
        if not job:
            return None

        update_data = job_update.dict(exclude_unset=True)
        update_data["updated_at"] = datetime.utcnow()

        for key, value in update_data.items():
            setattr(job, key, value)

        await job.save()
        logger.info(f"Updated job: {job_id}")
        return job

    async def delete_job(self, job_id: str) -> bool:
        job = await self.get_job_by_id(job_id)
        if not job:
            return False

        # Soft delete by setting is_active to False
        job.is_active = False
        job.updated_at = datetime.utcnow()
        await job.save()

        # Update company job counts
        await self._update_company_job_counts(job.company_name)

        logger.info(f"Deleted job: {job_id}")
        return True

    async def increment_view_count(self, job_id: str) -> bool:
        try:
            result = await self.db.jobs.update_one(
                {"_id": ObjectId(job_id)},
                {"$inc": {"view_count": 1}, "$set": {"updated_at": datetime.utcnow()}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error incrementing view count for job {job_id}: {e}")
            return False

    async def get_jobs_count(self, **filters) -> int:
        query = {}
        if "is_active" in filters:
            query["is_active"] = filters["is_active"]
        if "category" in filters:
            query["category_name"] = filters["category"]
        if "company" in filters:
            query["company_name"] = filters["company"]

        return await self.db.jobs.count_documents(query)

    async def validate_trusted_company(self, company_name: str) -> bool:
        company = await TrustedCompany.find_one({"name": company_name})
        return company is not None and company.is_verified

    async def _get_or_create_company(self, company_name: str) -> Optional[TrustedCompany]:
        company = await TrustedCompany.find_one({"name": company_name})
        if not company:
            company = TrustedCompany(name=company_name)
            await company.insert()
            logger.info(f"Created new company: {company_name}")
        return company

    async def _update_company_job_counts(self, company_name: str):
        try:
            total_count = await self.db.jobs.count_documents({"company_name": company_name})
            active_count = await self.db.jobs.count_documents({
                "company_name": company_name,
                "is_active": True
            })

            await self.db.trusted_companies.update_one(
                {"name": company_name},
                {
                    "$set": {
                        "total_jobs_posted": total_count,
                        "active_jobs_count": active_count,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
        except Exception as e:
            logger.error(f"Error updating company job counts for {company_name}: {e}")

    async def get_popular_jobs(self, limit: int = 10) -> List[Job]:
        cursor = self.db.jobs.find({"is_active": True}) \
                           .sort("view_count", -1) \
                           .limit(limit)
        jobs = []
        async for job_doc in cursor:
            jobs.append(Job(**job_doc))
        return jobs

    async def get_recent_jobs(self, limit: int = 10) -> List[Job]:
        cursor = self.db.jobs.find({"is_active": True}) \
                           .sort("created_at", -1) \
                           .limit(limit)
        jobs = []
        async for job_doc in cursor:
            jobs.append(Job(**job_doc))
        return jobs
