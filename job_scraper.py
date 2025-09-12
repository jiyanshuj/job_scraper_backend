import requests
from bs4 import BeautifulSoup
import pymongo
from datetime import datetime, timedelta
import re
import json
from typing import List, Dict, Optional
from dataclasses import dataclass
import time
from urllib.parse import urljoin, urlparse
import logging
from flask import Flask, jsonify, request
from flask_cors import CORS
import os
from dotenv import load_dotenv
from auth import require_auth, optional_auth, clerk_auth

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class Job:
    title: str
    company: str
    location: str
    job_type: str
    posted_time: str
    job_link: str
    description: str
    requirements: str
    skills: str
    category: str
    source: str

class JobDatabase:
    def __init__(self):
        self.mongo_uri = os.getenv('MONGO_URI')
        self.client = pymongo.MongoClient(self.mongo_uri)
        self.db = self.client['Tinder_Job']
        self.jobs_collection = self.db['jobs']
        self.trusted_companies_collection = self.db['trusted_companies']
        self.init_trusted_companies()
    
    def init_trusted_companies(self):
        """Initialize trusted companies collection if empty"""
        if self.trusted_companies_collection.count_documents({}) == 0:
            trusted_companies = [
                'Google', 'Microsoft', 'Amazon', 'Apple', 'Meta', 'Netflix',
                'IBM', 'Oracle', 'Salesforce', 'Adobe', 'Uber', 'Airbnb',
                'TCS', 'Infosys', 'Wipro', 'Accenture', 'Deloitte'
            ]
            
            trusted_docs = [
                {
                    'company_name': company,
                    'verified_at': datetime.utcnow()
                } for company in trusted_companies
            ]
            
            self.trusted_companies_collection.insert_many(trusted_docs)
            logger.info("Initialized trusted companies")
    
    def is_trusted_company(self, company_name: str) -> bool:
        """Check if a company is in the trusted list"""
        result = self.trusted_companies_collection.find_one({
            'company_name': {'$regex': company_name, '$options': 'i'}
        })
        return result is not None
    
    def add_job(self, job: Job) -> bool:
        """Add a job to MongoDB if company is trusted"""
        if not self.is_trusted_company(job.company):
            logger.warning(f"Company {job.company} is not in trusted list")
            return False
        
        try:
            # Map to MongoDB schema based on the image
            job_doc = {
                'title': job.title,
                'employer_id_1': job.company,  # Using company as employer_id_1
                'location_1': job.location,
                'job_type': job.job_type,
                'posted_time': job.posted_time,
                'job_link': job.job_link,
                'description_text': job.description,
                'requirements': job.requirements,
                'skills': job.skills,
                'category': job.category,
                'source': job.source,
                'created_at': datetime.utcnow(),
                'is_verified': True
            }
            
            # Use upsert to avoid duplicates based on job_link
            result = self.jobs_collection.update_one(
                {'job_link': job.job_link},
                {'$set': job_doc},
                upsert=True
            )
            
            if result.upserted_id or result.modified_count > 0:
                logger.info(f"Added/Updated job: {job.title} at {job.company}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Database error: {e}")
            return False
    
    def search_jobs(self, query: str = "", category: str = "", 
                   job_type: str = "", location: str = "") -> List[Dict]:
        """Search jobs with filters"""
        try:
            # Build MongoDB query
            mongo_query = {'is_verified': True}
            
            if query:
                mongo_query['$or'] = [
                    {'title': {'$regex': query, '$options': 'i'}},
                    {'employer_id_1': {'$regex': query, '$options': 'i'}},
                    {'skills': {'$regex': query, '$options': 'i'}}
                ]
            
            if category:
                mongo_query['category'] = category
            
            if job_type:
                mongo_query['job_type'] = {'$regex': job_type, '$options': 'i'}
            
            if location:
                mongo_query['location_1'] = {'$regex': location, '$options': 'i'}
            
            # Execute query and sort by created_at descending
            cursor = self.jobs_collection.find(mongo_query).sort('created_at', -1)
            
            # Convert cursor to list and handle ObjectId
            results = []
            for doc in cursor:
                doc['_id'] = str(doc['_id'])  # Convert ObjectId to string
                results.append(doc)
            
            return results
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            return []

class JobScraper:
    def __init__(self, db: JobDatabase):
        self.db = db
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def categorize_job(self, title: str, description: str, skills: str) -> str:
        """Categorize job based on title, description, and skills"""
        content = f"{title} {description} {skills}".lower()
        
        data_analytics_keywords = ['data analyst', 'analytics', 'tableau', 'power bi', 'sql', 'excel', 'statistics']
        data_engineering_keywords = ['data engineer', 'etl', 'pipeline', 'hadoop', 'spark', 'kafka', 'airflow']
        software_eng_keywords = ['software engineer', 'developer', 'programming', 'python', 'java', 'javascript', 'react']
        
        da_score = sum(1 for keyword in data_analytics_keywords if keyword in content)
        de_score = sum(1 for keyword in data_engineering_keywords if keyword in content)
        se_score = sum(1 for keyword in software_eng_keywords if keyword in content)
        
        if da_score >= de_score and da_score >= se_score and da_score > 0:
            return "Data Analytics"
        elif de_score >= se_score and de_score > 0:
            return "Data Engineering"
        else:
            return "Software Engineering"
    
    def extract_job_type(self, text: str) -> str:
        """Extract job type from text"""
        text_lower = text.lower()
        if 'intern' in text_lower:
            return "Internship"
        elif 'part-time' in text_lower or 'part time' in text_lower:
            return "Part-time"
        else:
            return "Full-time"
    
    def scrape_linkedin_jobs(self, role: str = "software engineer", max_pages: int = 5) -> List[Job]:
        """Scrape LinkedIn jobs"""
        jobs = []
        base_url = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
        
        for page in range(max_pages):
            try:
                params = {
                    'keywords': role,
                    'location': 'United States',
                    'f_TPR': 'r86400',  # Last 24 hours
                    'sortBy': 'DD',
                    'start': page * 25
                }
                
                response = self.session.get(base_url, params=params)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                job_cards = soup.find_all('li')
                
                for card in job_cards:
                    try:
                        title_elem = card.find(class_='base-search-card__title')
                        company_elem = card.find(class_='base-search-card__subtitle')
                        location_elem = card.find(class_='job-search-card__location')
                        time_elem = card.find('time')
                        link_elem = card.find(class_='base-card__full-link')
                        
                        if not all([title_elem, company_elem, link_elem]):
                            continue
                        
                        title = title_elem.get_text(strip=True)
                        company = company_elem.get_text(strip=True)
                        location = location_elem.get_text(strip=True) if location_elem else ""
                        posted_time = time_elem.get('datetime', '') if time_elem else ""
                        job_link = link_elem.get('href', '')
                        
                        # Get job details
                        description, requirements, skills = self.get_job_details(job_link)
                        job_type = self.extract_job_type(f"{title} {description}")
                        category = self.categorize_job(title, description, skills)
                        
                        job = Job(
                            title=title,
                            company=company,
                            location=location,
                            job_type=job_type,
                            posted_time=posted_time,
                            job_link=job_link,
                            description=description,
                            requirements=requirements,
                            skills=skills,
                            category=category,
                            source="LinkedIn"
                        )
                        
                        jobs.append(job)
                        
                    except Exception as e:
                        logger.error(f"Error parsing job card: {e}")
                        continue
                
                # Rate limiting
                time.sleep(5)
            except Exception as e:
                logger.error(f"Error scraping page {page}: {e}")
        
        return jobs
    
    def get_job_details(self, job_url: str) -> tuple:
        """Get detailed job information"""
        try:
            response = self.session.get(job_url)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract job description
            desc_elem = soup.find('div', class_='show-more-less-html__markup')
            description = desc_elem.get_text(strip=True) if desc_elem else ""
            
            # Extract requirements and skills (simplified)
            requirements = ""
            skills = ""
            
            if description:
                # Simple keyword extraction
                desc_lower = description.lower()
                if 'requirements' in desc_lower:
                    req_start = desc_lower.find('requirements')
                    requirements = description[req_start:req_start+500]
                
                # Extract skills
                skill_keywords = ['python', 'java', 'javascript', 'react', 'sql', 'aws', 'docker', 'kubernetes']
                found_skills = [skill for skill in skill_keywords if skill in desc_lower]
                skills = ', '.join(found_skills)
            
            return description[:1000], requirements, skills
            
        except Exception as e:
            logger.error(f"Error getting job details: {e}")
            return "", "", ""

class JobManager:
    def __init__(self):
        self.db = JobDatabase()
        self.scraper = JobScraper(self.db)
    
    def add_manual_job(self, job_data: Dict) -> bool:
        """Admin function to manually add a job"""
        job = Job(
            title=job_data['title'],
            company=job_data['company'],
            location=job_data.get('location', ''),
            job_type=job_data.get('job_type', 'Full-time'),
            posted_time=job_data.get('posted_time', 'Today'),
            job_link=job_data['job_link'],
            description=job_data.get('description', ''),
            requirements=job_data.get('requirements', ''),
            skills=job_data.get('skills', ''),
            category=job_data.get('category', 'Software Engineering'),
            source='Manual'
        )
        
        return self.db.add_job(job)
    
    def scrape_linkedin(self, role: str = "software engineer"):
        """Scrape jobs from LinkedIn only"""
        logger.info(f"Starting LinkedIn job scraping for role: {role}")
        
        # Scrape LinkedIn
        linkedin_jobs = self.scraper.scrape_linkedin_jobs(role)
        for job in linkedin_jobs:
            self.db.add_job(job)
        
        logger.info("LinkedIn job scraping completed")
    
    def search_jobs(self, **kwargs) -> List[Dict]:
        """Search jobs with filters"""
        return self.db.search_jobs(**kwargs)
    
    def get_job_stats(self) -> Dict:
        """Get job statistics"""
        try:
            # Get category statistics
            pipeline = [
                {'$match': {'is_verified': True}},
                {'$group': {'_id': '$category', 'count': {'$sum': 1}}}
            ]
            
            category_results = list(self.db.jobs_collection.aggregate(pipeline))
            category_stats = {item['_id']: item['count'] for item in category_results}
            
            # Get total jobs count
            total_jobs = self.db.jobs_collection.count_documents({'is_verified': True})
            
            return {
                'total_jobs': total_jobs,
                'by_category': category_stats
            }
        except Exception as e:
            logger.error(f"Error getting job stats: {e}")
            return {'total_jobs': 0, 'by_category': {}}

# Flask app for serving jobs
app = Flask(__name__)
CORS(app)

job_manager = JobManager()

@app.route('/api/jobs')
@optional_auth
def get_jobs():
    """Get jobs - optional authentication for public access"""
    query = request.args.get('query', '')
    category = request.args.get('category', '')
    job_type = request.args.get('job_type', '')
    location = request.args.get('location', '')
    
    jobs = job_manager.search_jobs(
        query=query,
        category=category,
        job_type=job_type,
        location=location
    )
    
    response_data = {
        'jobs': jobs,
        'user_authenticated': request.current_user is not None
    }
    
    if request.current_user:
        response_data['user'] = {
            'id': request.current_user['user_id'],
            'email': request.current_user['email'],
            'name': f"{request.current_user['first_name']} {request.current_user['last_name']}".strip()
        }
    
    return jsonify(response_data)

@app.route('/api/jobs/stats')
@require_auth
def get_job_stats():
    """Get job statistics - requires authentication"""
    stats = job_manager.get_job_stats()
    return jsonify({
        'stats': stats,
        'user': {
            'id': request.current_user['user_id'],
            'email': request.current_user['email']
        }
    })

@app.route('/api/jobs/manual', methods=['POST'])
@require_auth
def add_manual_job():
    """Add a manual job - requires authentication"""
    try:
        job_data = request.get_json()
        
        # Validate required fields
        required_fields = ['title', 'company', 'job_link']
        for field in required_fields:
            if field not in job_data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Add the job
        success = job_manager.add_manual_job(job_data)
        
        if success:
            return jsonify({
                'message': 'Job added successfully',
                'user': request.current_user['user_id']
            }), 201
        else:
            return jsonify({'error': 'Failed to add job - company not trusted'}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/verify')
@require_auth
def verify_auth():
    """Verify authentication status"""
    return jsonify({
        'authenticated': True,
        'user': {
            'id': request.current_user['user_id'],
            'email': request.current_user['email'],
            'name': f"{request.current_user['first_name']} {request.current_user['last_name']}".strip(),
            'username': request.current_user['username']
        }
    })

# Example usage
if __name__ == "__main__":
    # Initialize job manager
    job_manager = JobManager()
    
    # Scrape jobs from LinkedIn only
    job_manager.scrape_linkedin("data analyst")
    
    # Add a manual job
    manual_job = {
        'title': 'Senior Data Scientist',
        'company': 'Google',
        'location': 'Mountain View, CA',
        'job_type': 'Full-time',
        'job_link': 'https://careers.google.com/jobs/123',
        'description': 'Looking for a senior data scientist...',
        'skills': 'Python, Machine Learning, SQL'
    }
    job_manager.add_manual_job(manual_job)
    
    # Search jobs
    results = job_manager.search_jobs(query="python", category="Data Analytics")
    print(f"Found {len(results)} jobs")
    
    # Get statistics
    stats = job_manager.get_job_stats()
    print("Job Statistics:", stats)

    # Run Flask app
    app.run(debug=True)