from datetime import datetime
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class RedisCachedJobScraper:
    """Enhanced job scraper with Redis caching capability"""
    
    def __init__(self, redis_host: str = 'localhost', redis_port: int = 6379, 
                 redis_db: int = 0, redis_password: str = None, 
                 cache_duration_hours: int = 72):
        """
        Initialize Redis-cached job scraper
        
        Args:
            redis_host: Redis server host
            redis_port: Redis server port
            redis_db: Redis database number
            redis_password: Redis password (if required)
            cache_duration_hours: Cache duration in hours (default: 72 hours = 3 days)
        """
        try:
            # Import scraper and Redis cache
            from scraper import LinkedInJobScraper
            from redis_cache import RedisJobDataCache
            
            self.scraper = LinkedInJobScraper()
            self.cache = RedisJobDataCache(
                redis_host=redis_host,
                redis_port=redis_port,
                redis_db=redis_db,
                redis_password=redis_password,
                cache_duration_hours=cache_duration_hours
            )
            
            logger.info("RedisCachedJobScraper initialized successfully")
            
        except ImportError as e:
            logger.error(f"Import error: {str(e)}")
            raise ImportError("Required modules not found. Ensure scraper.py and redis_cache.py are available.")
        except Exception as e:
            logger.error(f"Initialization error: {str(e)}")
            raise
    
    def get_jobs(self, keywords: str = "software engineer", location: str = "United States", 
                max_jobs: int = 50, job_type_filter: str = None, category_filter: str = None,
                trusted_only: bool = True, force_refresh: bool = False) -> List[Dict]:
        """
        Get jobs with Redis caching support and advanced filtering
        
        Args:
            keywords: Job search keywords
            location: Job location
            max_jobs: Maximum number of jobs to return
            job_type_filter: Filter by job type (full-time, part-time, contract, internship)
            category_filter: Filter by job category
            trusted_only: Only return jobs from trusted companies
            force_refresh: If True, bypass cache and scrape fresh data
        
        Returns:
            List of job dictionaries with Redis caching
        """
        
        # Generate cache key with all parameters
        cache_key = self.cache.generate_cache_key(
            keywords, location, max_jobs, job_type_filter, category_filter, trusted_only
        )
        
        logger.info(f"Searching jobs with cache key: {cache_key[:12]}...")
        
        # Try to load from Redis cache first (unless force refresh)
        if not force_refresh:
            cached_data = self.cache.load_from_cache(cache_key)
            if cached_data:
                logger.info(f"Returning {cached_data['job_count']} jobs from Redis cache")
                return cached_data['data']
        
        # Scrape fresh data with enhanced parameters
        logger.info("Cache miss or force refresh - scraping fresh data from LinkedIn")
        jobs_data = self.scraper.scrape_jobs(
            keywords=keywords,
            location=location,
            max_jobs=max_jobs,
            job_type_filter=job_type_filter,
            category_filter=category_filter,
            trusted_only=trusted_only
        )
        
        # Enhanced metadata for Redis storage
        metadata = {
            'keywords': keywords,
            'location': location,
            'max_jobs': max_jobs,
            'job_type_filter': job_type_filter,
            'category_filter': category_filter,
            'trusted_only': trusted_only,
            'scraped_at': datetime.now().isoformat(),
            'scraper_version': '2.0',
            'source': 'LinkedIn'
        }
        
        # Save to Redis with comprehensive job fields
        success = self.cache.save_to_cache(cache_key, jobs_data, metadata)
        if success:
            logger.info(f"Successfully cached {len(jobs_data)} jobs in Redis")
        else:
            logger.warning("Failed to save data to Redis cache")
        
        return jobs_data
    
    def search_cached_jobs(self, title_keyword: str = None, company_keyword: str = None,
                          location_keyword: str = None, remote_only: bool = False,
                          trusted_only: bool = False, limit: int = 50) -> List[Dict]:
        """
        Search through cached jobs using specific criteria
        
        Args:
            title_keyword: Filter by job title containing this keyword
            company_keyword: Filter by company name containing this keyword
            location_keyword: Filter by location containing this keyword
            remote_only: If True, only return remote jobs
            trusted_only: If True, only return jobs from trusted companies
            limit: Maximum number of results to return
        
        Returns:
            List of matching job dictionaries
        """
        try:
            results = self.cache.search_jobs_by_criteria(
                title_keyword=title_keyword,
                company_keyword=company_keyword,
                location_keyword=location_keyword,
                remote_only=remote_only,
                trusted_only=trusted_only,
                limit=limit
            )
            
            logger.info(f"Found {len(results)} jobs matching search criteria")
            return results
            
        except Exception as e:
            logger.error(f"Error searching cached jobs: {str(e)}")
            return []
    
    def get_job_categories(self) -> List[str]:
        """Get available job categories from scraper"""
        try:
            return self.scraper.get_available_categories()
        except Exception as e:
            logger.error(f"Error getting job categories: {str(e)}")
            return ['All', 'Software Engineering', 'Data Science & Analytics', 'DevOps & Infrastructure']
    
    def get_trusted_companies(self) -> List[str]:
        """Get list of trusted companies from scraper"""
        try:
            return self.scraper.get_trusted_companies_list()
        except Exception as e:
            logger.error(f"Error getting trusted companies: {str(e)}")
            return []
    
    def get_cache_status(self) -> Dict:
        """Get comprehensive Redis cache status"""
        try:
            return self.cache.get_cache_info()
        except Exception as e:
            logger.error(f"Error getting cache status: {str(e)}")
            return {'error': str(e), 'redis_connected': False}
    
    def get_job_statistics(self) -> Dict:
        """Get detailed statistics about cached jobs"""
        try:
            return self.cache.get_job_statistics()
        except Exception as e:
            logger.error(f"Error getting job statistics: {str(e)}")
            return {'error': str(e)}
    
    def clear_cache(self, expired_only: bool = True) -> int:
        """
        Clear Redis cache files
        
        Args:
            expired_only: If True, only clear expired entries. If False, clear all cache.
        
        Returns:
            Number of entries cleared
        """
        try:
            if expired_only:
                self.cache.clear_expired_cache()
                logger.info("Cleared expired cache entries from Redis")
                return 0  # clear_expired_cache doesn't return count
            else:
                cleared_count = self.cache.clear_all_cache()
                logger.info(f"Cleared all cache data from Redis: {cleared_count} searches")
                return cleared_count
        except Exception as e:
            logger.error(f"Error clearing cache: {str(e)}")
            return 0
    
    def get_redis_health(self) -> Dict:
        """Check Redis connection health"""
        try:
            # Try to ping Redis
            self.cache.redis_client.ping()
            
            # Get Redis info
            info = self.cache.redis_client.info()
            
            return {
                'connected': True,
                'redis_version': info.get('redis_version', 'unknown'),
                'used_memory_human': info.get('used_memory_human', 'unknown'),
                'connected_clients': info.get('connected_clients', 0),
                'total_commands_processed': info.get('total_commands_processed', 0),
                'uptime_in_seconds': info.get('uptime_in_seconds', 0)
            }
        except Exception as e:
            logger.error(f"Redis health check failed: {str(e)}")
            return {
                'connected': False,
                'error': str(e)
            }
    
    def bulk_update_job_status(self, job_updates: List[Dict]) -> int:
        """
        Bulk update job status in Redis (useful for tracking applications, etc.)
        
        Args:
            job_updates: List of dictionaries with job_id and status updates
            
        Returns:
            Number of jobs successfully updated
        """
        try:
            updated_count = 0
            
            for update in job_updates:
                job_id = update.get('job_id')
                if not job_id:
                    continue
                
                job_key = f"{self.cache.hash_name}:{job_id}"
                
                # Check if job exists
                if self.cache.redis_client.exists(job_key):
                    # Update fields
                    update_fields = {k: v for k, v in update.items() if k != 'job_id'}
                    if update_fields:
                        self.cache.redis_client.hset(job_key, mapping=update_fields)
                        updated_count += 1
            
            logger.info(f"Bulk updated {updated_count} jobs in Redis")
            return updated_count
            
        except Exception as e:
            logger.error(f"Error in bulk update: {str(e)}")
            return 0
    
    def export_jobs_to_json(self, filter_criteria: Dict = None) -> Dict:
        """
        Export cached jobs to JSON format with optional filtering
        
        Args:
            filter_criteria: Optional dictionary with filter parameters
            
        Returns:
            Dictionary with exported job data and metadata
        """
        try:
            if filter_criteria:
                jobs = self.search_cached_jobs(
                    title_keyword=filter_criteria.get('title_keyword'),
                    company_keyword=filter_criteria.get('company_keyword'),
                    location_keyword=filter_criteria.get('location_keyword'),
                    remote_only=filter_criteria.get('remote_only', False),
                    trusted_only=filter_criteria.get('trusted_only', False),
                    limit=filter_criteria.get('limit', 1000)
                )
            else:
                # Export all jobs
                job_keys = self.cache.redis_client.keys(f"{self.cache.hash_name}:*")
                jobs = []
                
                for job_key in job_keys:
                    job_data = self.cache.redis_client.hgetall(job_key)
                    if job_data:
                        processed_job = self.cache._process_redis_job_data(job_data)
                        jobs.append(processed_job)
            
            export_data = {
                'export_timestamp': datetime.now().isoformat(),
                'total_jobs': len(jobs),
                'filter_criteria': filter_criteria or {},
                'jobs': jobs
            }
            
            logger.info(f"Exported {len(jobs)} jobs to JSON")
            return export_data
            
        except Exception as e:
            logger.error(f"Error exporting jobs to JSON: {str(e)}")
            return {'error': str(e), 'jobs': []}

# Example usage and testing
if __name__ == "__main__":
    import json
    
    # Test Redis-cached scraper
    print("Testing Redis-Cached LinkedIn Job Scraper...")
    
    try:
        # Initialize with local Redis (adjust settings as needed)
        cached_scraper = RedisCachedJobScraper(
            redis_host='localhost',
            redis_port=6379,
            redis_db=0,
            cache_duration_hours=72
        )
        
        # Test Redis connection
        health = cached_scraper.get_redis_health()
        print(f"Redis Health: {health}")
        
        if not health.get('connected'):
            print("Redis connection failed. Please ensure Redis is running.")
            exit(1)
        
        # Test job search with caching
        print("\n1. Testing job search with Redis caching...")
        jobs = cached_scraper.get_jobs(
            keywords="python developer",
            location="San Francisco",
            max_jobs=5,
            category_filter="Software Engineering",
            trusted_only=True
        )
        print(f"Found {len(jobs)} jobs")
        
        # Display first job
        if jobs:
            first_job = jobs[0]
            print(f"\nFirst Job:")
            print(f"- Title: {first_job.get('title')}")
            print(f"- Company: {first_job.get('company')}")
            print(f"- Location: {first_job.get('location')}")
            print(f"- Remote: {first_job.get('remote_work', 'No')}")
            print(f"- Skills: {', '.join(first_job.get('skills', [])[:3])}")
        
        # Test cached search
        print("\n2. Testing cached job search...")
        cached_jobs = cached_scraper.search_cached_jobs(
            title_keyword="python",
            trusted_only=True,
            limit=3
        )
        print(f"Found {len(cached_jobs)} cached jobs matching 'python'")
        
        # Test cache statistics
        print("\n3. Cache Status:")
        cache_status = cached_scraper.get_cache_status()
        print(f"- Total searches cached: {cache_status.get('total_searches', 0)}")
        print(f"- Total jobs cached: {cache_status.get('total_jobs_cached', 0)}")
        print(f"- Redis memory used: {cache_status.get('redis_memory_used_mb', 0)} MB")
        
        # Test job statistics
        print("\n4. Job Statistics:")
        job_stats = cached_scraper.get_job_statistics()
        print(f"- Total jobs in Redis: {job_stats.get('total_jobs', 0)}")
        print(f"- Remote jobs: {job_stats.get('remote_stats', {}).get('Yes', 0)}")
        print(f"- Trusted company jobs: {job_stats.get('trusted_companies', 0)}")
        
        # Show top companies
        top_companies = list(job_stats.get('by_company', {}).items())[:3]
        if top_companies:
            print("- Top companies:")
            for company, count in top_companies:
                print(f"  • {company}: {count} jobs")
        
        # Test export functionality
        print("\n5. Testing export functionality...")
        export_data = cached_scraper.export_jobs_to_json({
            'trusted_only': True,
            'limit': 10
        })
        print(f"Exported {export_data.get('total_jobs', 0)} jobs")
        
        print("\n✅ All tests completed successfully!")
        print(f"✅ Available Categories: {len(cached_scraper.get_job_categories())}")
        print(f"✅ Trusted Companies: {len(cached_scraper.get_trusted_companies())}")
        
    except Exception as e:
        print(f"❌ Error during testing: {str(e)}")
        print("Please ensure:")
        print("1. Redis is installed and running on localhost:6379")
        print("2. scraper.py file exists in the same directory")
        print("3. redis-py package is installed: pip install redis")