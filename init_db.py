#!/usr/bin/env python3
"""
Database initialization script for MongoDB
Creates indexes and initial data for the job scraper application
"""

import asyncio
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
from app.models.category import Category
from app.models.company import TrustedCompany

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def init_database():
    """Initialize MongoDB database with indexes and initial data"""
    try:
        # Connect to MongoDB
        client = AsyncIOMotorClient(settings.MONGODB_URL)
        db = client[settings.DATABASE_NAME]

        # Test connection
        await client.admin.command('ping')
        logger.info("Connected to MongoDB")

        # Create indexes for jobs collection
        await db.jobs.create_index([("job_title", 1)])
        await db.jobs.create_index([("location", 1)])
        await db.jobs.create_index([("company_name", 1)])
        await db.jobs.create_index([("category_name", 1)])
        await db.jobs.create_index([("skills", 1)])
        await db.jobs.create_index([("is_active", 1)])
        await db.jobs.create_index([("posted_date", -1)])
        await db.jobs.create_index([("scraped_from", 1)])
        await db.jobs.create_index([("view_count", -1)])
        await db.jobs.create_index([("created_at", -1)])
        logger.info("Created indexes for jobs collection")

        # Create indexes for companies collection
        await db.trusted_companies.create_index([("name", 1)], unique=True)
        await db.trusted_companies.create_index([("domain", 1)])
        await db.trusted_companies.create_index([("is_verified", 1)])
        await db.trusted_companies.create_index([("industry", 1)])
        logger.info("Created indexes for companies collection")

        # Create indexes for categories collection
        await db.categories.create_index([("name", 1)], unique=True)
        await db.categories.create_index([("is_active", 1)])
        logger.info("Created indexes for categories collection")

        # Initialize default categories
        default_categories = [
            {"name": "Software Development", "description": "Software engineering and development roles"},
            {"name": "Data Science", "description": "Data analysis, machine learning, and AI roles"},
            {"name": "DevOps", "description": "System administration and deployment roles"},
            {"name": "Product Management", "description": "Product management and strategy roles"},
            {"name": "Design", "description": "UI/UX design and creative roles"},
            {"name": "Marketing", "description": "Marketing and growth roles"},
            {"name": "Sales", "description": "Sales and business development roles"},
            {"name": "Finance", "description": "Finance and accounting roles"},
            {"name": "Operations", "description": "Operations and logistics roles"},
            {"name": "Human Resources", "description": "HR and talent management roles"}
        ]

        for category_data in default_categories:
            existing = await db.categories.find_one({"name": category_data["name"]})
            if not existing:
                category = Category(**category_data)
                await category.insert()
                logger.info(f"Created category: {category_data['name']}")

        # Initialize some well-known companies
        default_companies = [
            {"name": "Google", "domain": "google.com", "is_verified": True, "industry": "Technology"},
            {"name": "Microsoft", "domain": "microsoft.com", "is_verified": True, "industry": "Technology"},
            {"name": "Amazon", "domain": "amazon.com", "is_verified": True, "industry": "Technology"},
            {"name": "Apple", "domain": "apple.com", "is_verified": True, "industry": "Technology"},
            {"name": "Meta", "domain": "meta.com", "is_verified": True, "industry": "Technology"},
            {"name": "Netflix", "domain": "netflix.com", "is_verified": True, "industry": "Technology"},
            {"name": "Tesla", "domain": "tesla.com", "is_verified": True, "industry": "Technology"},
            {"name": "Uber", "domain": "uber.com", "is_verified": True, "industry": "Technology"}
        ]

        for company_data in default_companies:
            existing = await db.trusted_companies.find_one({"name": company_data["name"]})
            if not existing:
                company = TrustedCompany(**company_data)
                await company.insert()
                logger.info(f"Created company: {company_data['name']}")

        logger.info("Database initialization completed successfully")

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(init_database())
