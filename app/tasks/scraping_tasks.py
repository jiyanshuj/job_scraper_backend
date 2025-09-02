from celery import Celery
from app.scrapers.linkedin_scraper import LinkedInScraper
from app.scrapers.indeed_scraper import IndeedScraper
from app.core.database import SessionLocal
from app.services.job_service import JobService

celery_app = Celery('job_scraper')

@celery_app.task
def scrape_jobs_from_all_sources():
    """Scrape jobs from all configured sources"""
    scrapers = [
        LinkedInScraper(),
        IndeedScraper(),
        # Add other scrapers
    ]
    
    search_terms = ['software engineer', 'data analyst', 'data engineer']
    
    for scraper in scrapers:
        try:
            jobs = scraper.scrape_jobs(search_terms, max_pages=3)
            save_scraped_jobs.delay(jobs, scraper.source_name)
        except Exception as e:
            print(f"Error scraping from {scraper.source_name}: {e}")

@celery_app.task
def save_scraped_jobs(jobs: List[dict], source: str):
    """Save scraped jobs to database"""
    db = SessionLocal()
    job_service = JobService(db)
    
    saved_count = 0
    for job_data in jobs:
        try:
            # Check if job already exists
            existing = db.query(Job).filter(Job.job_link == job_data['job_link']).first()
            if not existing:
                job_service.create_scraped_job(job_data)
                saved_count += 1
        except Exception as e:
            print(f"Error saving job: {e}")
    
    print(f"Saved {saved_count} jobs from {source}")
    db.close()
