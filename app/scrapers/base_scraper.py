from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
import logging

class BaseScraper(ABC):
    def __init__(self, source_name: str, base_url: str, rate_limit: int = 2):
        self.source_name = source_name
        self.base_url = base_url
        self.rate_limit = rate_limit
        self.session = requests.Session()
        self.logger = logging.getLogger(f"scraper.{source_name}")
        
    def get_driver(self) -> webdriver.Chrome:
        """Setup Chrome driver for JavaScript-heavy sites"""
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        return webdriver.Chrome(options=options)
    
    def rate_limit_delay(self):
        """Implement rate limiting"""
        time.sleep(self.rate_limit)
    
    @abstractmethod
    def scrape_jobs(self, search_terms: List[str], max_pages: int = 5) -> List[Dict]:
        """Abstract method to scrape jobs from specific platform"""
        pass
    
    @abstractmethod
    def extract_job_details(self, job_url: str) -> Dict:
        """Abstract method to extract detailed job information"""
        pass
    
    def validate_company(self, company_name: str) -> bool:
        """Validate if company is trusted (implement with your business logic)"""
        # This would check against trusted_companies table
        blacklisted = ['bharatintern', 'fake-company', 'scam-inc']
        return company_name.lower() not in blacklisted
