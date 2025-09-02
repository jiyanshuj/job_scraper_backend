from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # MongoDB
    MONGODB_URL: str = "mongodb://localhost:27017"
    DATABASE_NAME: str = "jobscraper"

    # Redis (for Celery)
    REDIS_URL: str = "redis://localhost:6379/0"

    # API
    SECRET_KEY: str = "your-secret-key-here"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Scraping
    SCRAPING_INTERVAL_HOURS: int = 6
    MAX_SCRAPING_PAGES: int = 5
    RATE_LIMIT_SECONDS: int = 2

    # LinkedIn API (if using official API)
    LINKEDIN_CLIENT_ID: str = ""
    LINKEDIN_CLIENT_SECRET: str = ""

    # Job Analytics
    ANALYTICS_RETENTION_DAYS: int = 90
    RECOMMENDATION_LIMIT: int = 10

    model_config = {
        "env_file": ".env"
    }

settings = Settings()
