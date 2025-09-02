from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from .config import settings
import logging

logger = logging.getLogger(__name__)

class Database:
    client: AsyncIOMotorClient = None
    database = None

db = Database()

async def connect_to_mongo():
    """Connect to MongoDB"""
    try:
        db.client = AsyncIOMotorClient(settings.MONGODB_URL)
        db.database = db.client[settings.DATABASE_NAME]

        # Test the connection
        await db.client.admin.command('ping')
        logger.info("Connected to MongoDB")

        # Initialize Beanie with the document models
        from app.models.job import Job
        from app.models.company import TrustedCompany
        from app.models.category import Category

        await init_beanie(
            database=db.database,
            document_models=[Job, TrustedCompany, Category]
        )
        logger.info("Beanie initialized with document models")

    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise

async def close_mongo_connection():
    """Close MongoDB connection"""
    if db.client:
        db.client.close()
        logger.info("MongoDB connection closed")

async def get_database():
    """Get database instance"""
    return db.database
