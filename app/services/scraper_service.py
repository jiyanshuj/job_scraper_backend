from typing import List, Dict
from app.scrapers.base_scraper import BaseScraper

class ScraperService:
    def __init__(self):
        self.scrapers = {}
    
    def register_scraper(self, scraper: BaseScraper):
        """Register a scraper instance"""
        self.scrapers[scraper.source_name] = scraper
    
    def scrape_from_source(self, source_name: str, search_terms: List[str], max_pages: int = 5) -> List[Dict]:
        """Scrape jobs from a specific source"""
        if source_name not in self.scrapers:
            raise ValueError(f"Scraper for {source_name} not registered")
        
        scraper = self.scrapers[source_name]
        return scraper.scrape_jobs(search_terms, max_pages)
    
    def scrape_all_sources(self, search_terms: List[str], max_pages: int = 5) -> Dict[str, List[Dict]]:
        """Scrape jobs from all registered sources"""
        results = {}
        for source_name, scraper in self.scrapers.items():
            try:
                jobs = scraper.scrape_jobs(search_terms, max_pages)
                results[source_name] = jobs
            except Exception as e:
                print(f"Error scraping from {source_name}: {e}")
                results[source_name] = []
        return results
