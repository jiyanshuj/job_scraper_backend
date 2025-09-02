from .base_scraper import BaseScraper
from typing import List, Dict
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta

class LinkedInScraper(BaseScraper):
    def __init__(self):
        super().__init__("linkedin", "https://www.linkedin.com/jobs/search", rate_limit=3)
        
    def scrape_jobs(self, search_terms: List[str], max_pages: int = 5) -> List[Dict]:
        jobs = []
        
        for search_term in search_terms:
            self.logger.info(f"Scraping LinkedIn for: {search_term}")
            
            for page in range(max_pages):
                params = {
                    'keywords': search_term,
                    'location': 'India',
                    'start': page * 25,
                    'f_TPR': 'r604800',  # Last week
                    'f_JT': 'I,F,P'  # Internship, Full-time, Part-time
                }
                
                response = self.session.get(self.base_url, params=params)
                if response.status_code != 200:
                    self.logger.error(f"Failed to fetch page {page}")
                    continue
                
                soup = BeautifulSoup(response.content, 'html.parser')
                job_cards = soup.find_all('div', class_='result-card job-result-card')
                
                for card in job_cards:
                    try:
                        job_data = self._extract_job_from_card(card)
                        if job_data and self.validate_company(job_data.get('company_name', '')):
                            jobs.append(job_data)
                    except Exception as e:
                        self.logger.error(f"Error extracting job: {e}")
                
                self.rate_limit_delay()
        
        return jobs
    
    def _extract_job_from_card(self, card) -> Dict:
        """Extract job information from LinkedIn job card"""
        job_link = card.find('a', class_='result-card__full-card-link')['href']
        job_title = card.find('h3', class_='result-card__title').get_text().strip()
        company_name = card.find('h4', class_='result-card__subtitle').get_text().strip()
        location = card.find('span', class_='job-result-card__location').get_text().strip()
        posted_time = card.find('time', class_='job-result-card__listdate')['datetime']
        
        return {
            'job_title': job_title,
            'company_name': company_name,
            'job_link': job_link,
            'location': location,
            'posted_time': posted_time,
            'scraped_from': 'linkedin'
        }
    
    def extract_job_details(self, job_url: str) -> Dict:
        """Extract detailed job information from LinkedIn job page"""
        response = self.session.get(job_url)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        description_div = soup.find('div', class_='description__text')
        description = description_div.get_text().strip() if description_div else ""
        
        # Extract skills, requirements, etc. from description
        skills = self._extract_skills(description)
        requirements = self._extract_requirements(description)
        job_type = self._determine_job_type(description)
        
        return {
            'description': description,
            'skills': skills,
            'requirements': requirements,
            'job_type': job_type
        }
    
    def _extract_skills(self, description: str) -> List[str]:
        """Extract skills from job description using regex patterns"""
        skill_patterns = [
            r'(?i)python', r'(?i)java', r'(?i)javascript', r'(?i)react',
            r'(?i)node\.js', r'(?i)sql', r'(?i)mongodb', r'(?i)postgresql',
            r'(?i)docker', r'(?i)kubernetes', r'(?i)aws', r'(?i)azure'
        ]
        
        skills = []
        for pattern in skill_patterns:
            if re.search(pattern, description):
                skills.append(pattern.replace('(?i)', '').replace('\\', ''))
        
        return skills
