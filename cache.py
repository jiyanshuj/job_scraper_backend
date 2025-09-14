import json
import os
import hashlib
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

class JobDataCache:
    def __init__(self, cache_dir: str = "cache", cache_duration_hours: int = 72):
        """
        Initialize cache manager
        
        Args:
            cache_dir: Directory to store cache files
            cache_duration_hours: Cache duration in hours (default: 72 hours = 3 days)
        """
        self.cache_dir = cache_dir
        self.cache_duration = timedelta(hours=cache_duration_hours)
        self.ensure_cache_directory()
        
    def ensure_cache_directory(self):
        """Create cache directory if it doesn't exist"""
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
            logger.info(f"Created cache directory: {self.cache_dir}")
    
    def generate_cache_key(self, keywords: str, location: str, max_jobs: int = 50, 
                         job_type_filter: str = None, category_filter: str = None, 
                         trusted_only: bool = True) -> str:
        """Generate unique cache key based on search parameters"""
        search_params = f"{keywords}_{location}_{max_jobs}_{job_type_filter}_{category_filter}_{trusted_only}"
        return hashlib.md5(search_params.encode()).hexdigest()
    
    def get_cache_file_path(self, cache_key: str) -> str:
        """Get full path for cache file"""
        return os.path.join(self.cache_dir, f"{cache_key}.json")
    
    def is_cache_valid(self, cache_file_path: str) -> bool:
        """Check if cache file exists and is still valid"""
        if not os.path.exists(cache_file_path):
            return False
        
        try:
            # Get file modification time
            file_mtime = datetime.fromtimestamp(os.path.getmtime(cache_file_path))
            current_time = datetime.now()
            
            # Check if file is within cache duration
            if current_time - file_mtime <= self.cache_duration:
                return True
            else:
                logger.info(f"Cache expired for file: {cache_file_path}")
                return False
                
        except Exception as e:
            logger.error(f"Error checking cache validity: {str(e)}")
            return False
    
    def save_to_cache(self, cache_key: str, data: List[Dict], metadata: Dict = None) -> bool:
        """Save job data to cache"""
        try:
            cache_file_path = self.get_cache_file_path(cache_key)
            
            cache_data = {
                'timestamp': datetime.now().isoformat(),
                'cache_key': cache_key,
                'metadata': metadata or {},
                'job_count': len(data),
                'data': data
            }
            
            with open(cache_file_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved {len(data)} jobs to cache: {cache_file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving to cache: {str(e)}")
            return False
    
    def load_from_cache(self, cache_key: str) -> Optional[Dict]:
        """Load job data from cache"""
        try:
            cache_file_path = self.get_cache_file_path(cache_key)
            
            if not self.is_cache_valid(cache_file_path):
                return None
            
            with open(cache_file_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            logger.info(f"Loaded {cache_data.get('job_count', 0)} jobs from cache")
            return cache_data
            
        except Exception as e:
            logger.error(f"Error loading from cache: {str(e)}")
            return None
    
    def clear_expired_cache(self):
        """Remove expired cache files"""
        try:
            if not os.path.exists(self.cache_dir):
                return
            
            current_time = datetime.now()
            expired_files = []
            
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.json'):
                    file_path = os.path.join(self.cache_dir, filename)
                    try:
                        file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                        if current_time - file_mtime > self.cache_duration:
                            os.remove(file_path)
                            expired_files.append(filename)
                    except Exception as e:
                        logger.error(f"Error removing expired cache file {filename}: {str(e)}")
            
            if expired_files:
                logger.info(f"Removed {len(expired_files)} expired cache files")
            
        except Exception as e:
            logger.error(f"Error clearing expired cache: {str(e)}")
    
    def get_cache_info(self) -> Dict:
        """Get information about current cache status"""
        try:
            if not os.path.exists(self.cache_dir):
                return {
                    'total_files': 0,
                    'total_jobs': 0,
                    'cache_size_mb': 0,
                    'files': []
                }
            
            files_info = []
            total_jobs = 0
            total_size = 0
            
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.json'):
                    file_path = os.path.join(self.cache_dir, filename)
                    try:
                        file_size = os.path.getsize(file_path)
                        file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                        is_valid = self.is_cache_valid(file_path)
                        
                        # Try to get job count from file
                        job_count = 0
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                cache_data = json.load(f)
                                job_count = cache_data.get('job_count', 0)
                        except:
                            pass
                        
                        files_info.append({
                            'filename': filename,
                            'size_bytes': file_size,
                            'modified': file_mtime.isoformat(),
                            'is_valid': is_valid,
                            'job_count': job_count
                        })
                        
                        total_size += file_size
                        if is_valid:
                            total_jobs += job_count
                            
                    except Exception as e:
                        logger.error(f"Error reading cache file info {filename}: {str(e)}")
            
            return {
                'total_files': len(files_info),
                'valid_files': sum(1 for f in files_info if f['is_valid']),
                'total_jobs': total_jobs,
                'cache_size_mb': round(total_size / (1024 * 1024), 2),
                'files': files_info
            }
            
        except Exception as e:
            logger.error(f"Error getting cache info: {str(e)}")
            return {'error': str(e)}
    
    def clear_all_cache(self):
        """Remove all cache files"""
        try:
            if not os.path.exists(self.cache_dir):
                return
            
            removed_files = 0
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.json'):
                    file_path = os.path.join(self.cache_dir, filename)
                    try:
                        os.remove(file_path)
                        removed_files += 1
                    except Exception as e:
                        logger.error(f"Error removing cache file {filename}: {str(e)}")
            
            logger.info(f"Removed {removed_files} cache files")
            return removed_files
            
        except Exception as e:
            logger.error(f"Error clearing all cache: {str(e)}")
            return 0

class CachedJobScraper:
    """Wrapper class that combines scraper with cache functionality"""
    
    def __init__(self, cache_duration_hours: int = 72):
        from scraper import LinkedInJobScraper
        self.scraper = LinkedInJobScraper()
        self.cache = JobDataCache(cache_duration_hours=cache_duration_hours)
    
    def get_jobs(self, keywords: str = "software engineer", location: str = "United States", 
                max_jobs: int = 50, job_type_filter: str = None, category_filter: str = None,
                trusted_only: bool = True, force_refresh: bool = False) -> List[Dict]:
        """
        Get jobs with caching support and advanced filtering
        
        Args:
            keywords: Job search keywords
            location: Job location
            max_jobs: Maximum number of jobs to return
            job_type_filter: Filter by job type (full-time, part-time, contract, internship)
            category_filter: Filter by job category
            trusted_only: Only return jobs from trusted companies
            force_refresh: If True, bypass cache and scrape fresh data
        
        Returns:
            List of job dictionaries
        """
        
        # Generate cache key with all parameters
        cache_key = self.cache.generate_cache_key(
            keywords, location, max_jobs, job_type_filter, category_filter, trusted_only
        )
        
        # Try to load from cache first (unless force refresh)
        if not force_refresh:
            cached_data = self.cache.load_from_cache(cache_key)
            if cached_data:
                logger.info("Returning cached data")
                return cached_data['data']
        
        # Scrape fresh data with enhanced parameters
        logger.info("Cache miss or force refresh - scraping fresh data")
        jobs_data = self.scraper.scrape_jobs(
            keywords=keywords,
            location=location,
            max_jobs=max_jobs,
            job_type_filter=job_type_filter,
            category_filter=category_filter,
            trusted_only=trusted_only
        )
        
        # Save to cache
        metadata = {
            'keywords': keywords,
            'location': location,
            'max_jobs': max_jobs,
            'job_type_filter': job_type_filter,
            'category_filter': category_filter,
            'trusted_only': trusted_only,
            'scraped_at': datetime.now().isoformat()
        }
        
        self.cache.save_to_cache(cache_key, jobs_data, metadata)
        
        return jobs_data
    
    def get_job_categories(self) -> List[str]:
        """Get available job categories from scraper"""
        return self.scraper.get_available_categories()
    
    def get_trusted_companies(self) -> List[str]:
        """Get list of trusted companies from scraper"""
        return self.scraper.get_trusted_companies_list()
    
    def get_cache_status(self) -> Dict:
        """Get current cache status"""
        return self.cache.get_cache_info()
    
    def clear_cache(self, expired_only: bool = True):
        """Clear cache files"""
        if expired_only:
            self.cache.clear_expired_cache()
        else:
            self.cache.clear_all_cache()

# Example usage
if __name__ == "__main__":
    # Test enhanced cache functionality
    cached_scraper = CachedJobScraper()
    
    # Test with different filters
    print("Testing Software Engineering jobs from trusted companies:")
    jobs1 = cached_scraper.get_jobs(
        keywords="python developer",
        location="San Francisco",
        max_jobs=5,
        category_filter="Software Engineering",
        trusted_only=True
    )
    print(f"Got {len(jobs1)} jobs")
    
    # Test Data Science category
    print("\nTesting Data Science jobs:")
    jobs2 = cached_scraper.get_jobs(
        keywords="data scientist",
        location="New York",
        max_jobs=5,
        category_filter="Data Science & Analytics",
        trusted_only=True
    )
    print(f"Got {len(jobs2)} jobs")
    
    # Get available categories and companies
    print(f"\nAvailable categories: {cached_scraper.get_job_categories()}")
    print(f"Number of trusted companies: {len(cached_scraper.get_trusted_companies())}")
    
    # Get cache status
    print("\nCache status:")
    cache_info = cached_scraper.get_cache_status()
    print(json.dumps({k: v for k, v in cache_info.items() if k != 'files'}, indent=2))