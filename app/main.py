from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.api.v1 import jobs, companies, admin
from app.core.database import connect_to_mongo, close_mongo_connection
import logging

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up the application...")
    await connect_to_mongo()

    yield

    # Shutdown
    logger.info("Shutting down the application...")
    await close_mongo_connection()

app = FastAPI(
    title="Job Scraper API",
    description="Backend system for scraping and managing job postings with MongoDB",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(jobs.router, prefix="/api/v1/jobs", tags=["jobs"])
app.include_router(companies.router, prefix="/api/v1/companies", tags=["companies"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])

@app.get("/")
async def root(request: Request):
    logger.info(f"Request received: {request.method} {request.url.path}")
    return {"message": "Job Scraper API with MongoDB", "status": "running"}

@app.get("/health")
async def health_check(request: Request):
    logger.info(f"Request received: {request.method} {request.url.path}")
    return {"status": "healthy", "database": "mongodb"}
