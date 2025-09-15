import redis
import json
import hashlib
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

class RedisJobDataCache:
    def __init__(self, redis_host: str = 'localhost', redis_port: int = 6379, 
                 redis_db: int = 0, redis_password: str = None, 
                 cache_duration_hours: int = 72):
        """
        Initialize Redis cache manager
        
        Args:
            redis_host: Redis server host
            redis_port: Redis server port
            redis_db: Redis database number
            redis_password: Redis password (if required)
            cache_duration_hours: Cache duration in hours (default: 72 hours = 3 days)
        """
        self.cache_duration_seconds = cache_duration_hours * 3600
        self.hash_name = "job-scraping"
        
        # Test connection with retry
        max_retries = 3

        try:
            # Enhanced Redis configuration with connection pooling and retry logic
            self.redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                password=redis_password,
                decode_responses=True,
                socket_timeout=30,              # Increased from 5s to 30s
                socket_connect_timeout=10,      # Increased from 5s to 10s
                retry_on_timeout=True,          # Enable retries on timeout
                health_check_interval=30,       # Health check every 30 seconds
                max_connections=20,             # Connection pool size
                socket_keepalive=True           # Keep connections alive
            )

            for attempt in range(max_retries):
                try:
                    self.redis_client.ping()
                    logger.info(f"Connected to Redis at {redis_host}:{redis_port} (attempt {attempt + 1})")
                    break
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    logger.warning(f"Redis connection attempt {attempt + 1} failed: {str(e)}. Retrying...")
                    time.sleep(2 ** attempt)  # Exponential backoff

        except Exception as e:
            logger.error(f"Failed to connect to Redis after {max_retries} attempts: {str(e)}")
            raise ConnectionError(f"Could not connect to Redis: {str(e)}")
    
    def generate_cache_key(self, keywords: str, location: str, max_jobs: int = 50, 
                         job_type_filter: str = None, category_filter: str = None, 
                         trusted_only: bool = True) -> str:
        """Generate unique cache key based on search parameters"""
        search_params = f"{keywords}_{location}_{max_jobs}_{job_type_filter}_{category_filter}_{trusted_only}"
        return hashlib.md5(search_params.encode()).hexdigest()
    
    def save_job_to_redis(self, job_data: Dict) -> bool:
        """Save individual job to Redis hash with comprehensive fields"""
        try:
            # Generate unique job ID if not present
            if 'job_id' not in job_data:
                job_id_source = f"{job_data.get('title', '')}{job_data.get('company', '')}{job_data.get('location', '')}"
                job_data['job_id'] = hashlib.md5(job_id_source.encode()).hexdigest()[:12]
            
            job_id = job_data['job_id']
            
            # Prepare comprehensive job fields for Redis Hash
            redis_fields = {
                'title': job_data.get('title', ''),
                'company': job_data.get('company', ''),
                'skills': json.dumps(job_data.get('skills', [])),
                'salary': job_data.get('salary', ''),
                'location': job_data.get('location', ''),
                'job_type': job_data.get('job_type', ''),
                'experience_level': job_data.get('experience_level', ''),
                'category': job_data.get('category', ''),
                'posted_date': job_data.get('posted_date', ''),
                'url': job_data.get('job_url', ''),
                'job_id': job_id,
                'requirements': json.dumps(job_data.get('requirements', [])),
                'responsibilities': job_data.get('description', ''),
                'employment_type': job_data.get('employment_type', ''),
                'remote': self._determine_remote_status(job_data),
                'is_trusted_company': str(job_data.get('is_trusted_company', False)),
                'created_at': datetime.now().isoformat(),
                'expires_at': (datetime.now() + timedelta(seconds=self.cache_duration_seconds)).isoformat()
            }
            
            # Save to Redis Hash
            self.redis_client.hset(f"{self.hash_name}:{job_id}", mapping=redis_fields)
            
            # Set expiration for the individual job hash
            self.redis_client.expire(f"{self.hash_name}:{job_id}", self.cache_duration_seconds)
            
            return True
            
        except Exception as e:
            logger.error(f"Error saving job to Redis: {str(e)}")
            return False
    
    def _determine_remote_status(self, job_data: Dict) -> str:
        """Determine remote work status from job data"""
        location = job_data.get('location', '').lower()
        description = job_data.get('description', '').lower()
        title = job_data.get('title', '').lower()
        
        remote_indicators = ['remote', 'work from home', 'wfh', 'telecommute']
        hybrid_indicators = ['hybrid', 'flexible', 'part remote']
        
        combined_text = f"{location} {description} {title}"
        
        if any(indicator in combined_text for indicator in hybrid_indicators):
            return 'Hybrid'
        elif any(indicator in combined_text for indicator in remote_indicators):
            return 'Yes'
        else:
            return 'No'
    
    def save_to_cache(self, cache_key: str, jobs_data: List[Dict], metadata: Dict = None) -> bool:
        """Save job search results to Redis with metadata"""
        try:
            # Save individual jobs to Redis hashes
            saved_job_ids = []
            for job_data in jobs_data:
                if self.save_job_to_redis(job_data):
                    saved_job_ids.append(job_data.get('job_id'))
            
            # Save search results metadata
            search_metadata = {
                'cache_key': cache_key,
                'job_ids': json.dumps(saved_job_ids),
                'job_count': len(saved_job_ids),
                'metadata': json.dumps(metadata or {}),
                'created_at': datetime.now().isoformat(),
                'expires_at': (datetime.now() + timedelta(seconds=self.cache_duration_seconds)).isoformat()
            }
            
            # Store search metadata
            self.redis_client.hset(f"search:{cache_key}", mapping=search_metadata)
            self.redis_client.expire(f"search:{cache_key}", self.cache_duration_seconds)
            
            # Add to search index for easy retrieval
            self.redis_client.sadd("active_searches", cache_key)
            
            logger.info(f"Saved {len(saved_job_ids)} jobs to Redis cache with key: {cache_key}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving to Redis cache: {str(e)}")
            return False
    
    def load_from_cache(self, cache_key: str) -> Optional[Dict]:
        """Load job search results from Redis cache"""
        try:
            # Check if search exists
            search_data = self.redis_client.hgetall(f"search:{cache_key}")
            if not search_data:
                logger.info(f"No cached data found for key: {cache_key}")
                return None
            
            # Check if cache has expired
            expires_at = datetime.fromisoformat(search_data.get('expires_at', ''))
            if datetime.now() > expires_at:
                logger.info(f"Cache expired for key: {cache_key}")
                self.clear_search_cache(cache_key)
                return None
            
            # Load individual jobs
            job_ids = json.loads(search_data.get('job_ids', '[]'))
            jobs_data = []
            
            for job_id in job_ids:
                job_data = self.redis_client.hgetall(f"{self.hash_name}:{job_id}")
                if job_data:
                    # Convert Redis hash back to job dictionary
                    processed_job = self._process_redis_job_data(job_data)
                    jobs_data.append(processed_job)
            
            logger.info(f"Loaded {len(jobs_data)} jobs from Redis cache")
            
            return {
                'timestamp': search_data.get('created_at'),
                'cache_key': cache_key,
                'metadata': json.loads(search_data.get('metadata', '{}')),
                'job_count': len(jobs_data),
                'data': jobs_data
            }
            
        except Exception as e:
            logger.error(f"Error loading from Redis cache: {str(e)}")
            return None
    
    def _process_redis_job_data(self, redis_job_data: Dict) -> Dict:
        """Convert Redis hash data back to job dictionary format"""
        try:
            return {
                'title': redis_job_data.get('title', ''),
                'company': redis_job_data.get('company', ''),
                'location': redis_job_data.get('location', ''),
                'description': redis_job_data.get('responsibilities', ''),
                'requirements': json.loads(redis_job_data.get('requirements', '[]')),
                'job_type': redis_job_data.get('job_type', ''),
                'skills': json.loads(redis_job_data.get('skills', '[]')),
                'posted_date': redis_job_data.get('posted_date', ''),
                'job_url': redis_job_data.get('url', ''),
                'salary': redis_job_data.get('salary', ''),
                'category': redis_job_data.get('category', ''),
                'is_trusted_company': redis_job_data.get('is_trusted_company', 'False') == 'True',
                'experience_level': redis_job_data.get('experience_level', ''),
                'employment_type': redis_job_data.get('employment_type', ''),
                'job_id': redis_job_data.get('job_id', ''),
                'remote_work': redis_job_data.get('remote', 'No')
            }
        except Exception as e:
            logger.error(f"Error processing Redis job data: {str(e)}")
            return {}
    
    def clear_expired_cache(self):
        """Remove expired cache entries"""
        try:
            current_time = datetime.now()
            expired_searches = []
            expired_jobs = []
            
            # Check active searches
            active_searches = self.redis_client.smembers("active_searches")
            for search_key in active_searches:
                search_data = self.redis_client.hget(f"search:{search_key}", "expires_at")
                if search_data:
                    try:
                        expires_at = datetime.fromisoformat(search_data)
                        if current_time > expires_at:
                            expired_searches.append(search_key)
                    except:
                        expired_searches.append(search_key)  # Invalid date format
            
            # Clear expired searches
            for search_key in expired_searches:
                self.clear_search_cache(search_key)
            
            # Check individual job hashes
            job_keys = self.redis_client.keys(f"{self.hash_name}:*")
            for job_key in job_keys:
                expires_at_str = self.redis_client.hget(job_key, "expires_at")
                if expires_at_str:
                    try:
                        expires_at = datetime.fromisoformat(expires_at_str)
                        if current_time > expires_at:
                            expired_jobs.append(job_key)
                    except:
                        expired_jobs.append(job_key)  # Invalid date format
            
            # Remove expired job hashes
            for job_key in expired_jobs:
                self.redis_client.delete(job_key)
            
            logger.info(f"Cleaned up {len(expired_searches)} expired searches and {len(expired_jobs)} expired jobs")
            
        except Exception as e:
            logger.error(f"Error clearing expired cache: {str(e)}")
    
    def clear_search_cache(self, cache_key: str):
        """Clear specific search cache"""
        try:
            # Get job IDs from search
            search_data = self.redis_client.hgetall(f"search:{cache_key}")
            if search_data and 'job_ids' in search_data:
                job_ids = json.loads(search_data['job_ids'])
                
                # Remove individual job hashes
                for job_id in job_ids:
                    self.redis_client.delete(f"{self.hash_name}:{job_id}")
            
            # Remove search metadata
            self.redis_client.delete(f"search:{cache_key}")
            
            # Remove from active searches
            self.redis_client.srem("active_searches", cache_key)
            
            logger.info(f"Cleared cache for search: {cache_key}")
            
        except Exception as e:
            logger.error(f"Error clearing search cache: {str(e)}")
    
    def clear_all_cache(self):
        """Remove all cached data"""
        try:
            # Get all active searches
            active_searches = self.redis_client.smembers("active_searches")
            
            # Clear each search
            for search_key in active_searches:
                self.clear_search_cache(search_key)
            
            # Clear any remaining job hashes
            job_keys = self.redis_client.keys(f"{self.hash_name}:*")
            if job_keys:
                self.redis_client.delete(*job_keys)
            
            # Clear search keys
            search_keys = self.redis_client.keys("search:*")
            if search_keys:
                self.redis_client.delete(*search_keys)
            
            # Clear active searches set
            self.redis_client.delete("active_searches")
            
            logger.info("Cleared all cached data from Redis")
            return len(active_searches)
            
        except Exception as e:
            logger.error(f"Error clearing all cache: {str(e)}")
            return 0
    
    def get_cache_info(self) -> Dict:
        """Get comprehensive cache information"""
        try:
            # Get active searches
            active_searches = self.redis_client.smembers("active_searches")
            
            # Get job statistics
            job_keys = self.redis_client.keys(f"{self.hash_name}:*")
            
            # Calculate memory usage
            memory_info = self.redis_client.info('memory')
            used_memory = memory_info.get('used_memory', 0)
            
            # Get detailed search info
            search_details = []
            total_jobs = 0
            
            for search_key in active_searches:
                search_data = self.redis_client.hgetall(f"search:{search_key}")
                if search_data:
                    job_count = int(search_data.get('job_count', 0))
                    total_jobs += job_count
                    
                    search_details.append({
                        'cache_key': search_key,
                        'job_count': job_count,
                        'created_at': search_data.get('created_at'),
                        'expires_at': search_data.get('expires_at'),
                        'metadata': json.loads(search_data.get('metadata', '{}'))
                    })
            
            return {
                'total_searches': len(active_searches),
                'total_job_hashes': len(job_keys),
                'total_jobs_cached': total_jobs,
                'redis_memory_used_mb': round(used_memory / (1024 * 1024), 2),
                'redis_connected': True,
                'cache_duration_hours': self.cache_duration_seconds // 3600,
                'searches': search_details[:10]  # Limit to first 10 for display
            }
            
        except Exception as e:
            logger.error(f"Error getting cache info: {str(e)}")
            return {
                'error': str(e),
                'redis_connected': False
            }
    
    def search_jobs_by_criteria(self, title_keyword: str = None, company_keyword: str = None,
                               location_keyword: str = None, remote_only: bool = False,
                               trusted_only: bool = False, limit: int = 50) -> List[Dict]:
        """Search cached jobs by specific criteria"""
        try:
            job_keys = self.redis_client.keys(f"{self.hash_name}:*")
            matching_jobs = []
            
            for job_key in job_keys:
                if len(matching_jobs) >= limit:
                    break
                    
                job_data = self.redis_client.hgetall(job_key)
                if not job_data:
                    continue
                
                # Apply filters
                if title_keyword and title_keyword.lower() not in job_data.get('title', '').lower():
                    continue
                
                if company_keyword and company_keyword.lower() not in job_data.get('company', '').lower():
                    continue
                
                if location_keyword and location_keyword.lower() not in job_data.get('location', '').lower():
                    continue
                
                if remote_only and job_data.get('remote', 'No') == 'No':
                    continue
                
                if trusted_only and job_data.get('is_trusted_company', 'False') != 'True':
                    continue
                
                # Convert and add to results
                processed_job = self._process_redis_job_data(job_data)
                matching_jobs.append(processed_job)
            
            logger.info(f"Found {len(matching_jobs)} jobs matching criteria")
            return matching_jobs
            
        except Exception as e:
            logger.error(f"Error searching jobs by criteria: {str(e)}")
            return []
    
    def get_job_statistics(self) -> Dict:
        """Get statistics about cached jobs"""
        try:
            job_keys = self.redis_client.keys(f"{self.hash_name}:*")
            
            if not job_keys:
                return {'total_jobs': 0}
            
            # Collect statistics
            stats = {
                'total_jobs': 0,
                'by_company': {},
                'by_location': {},
                'by_job_type': {},
                'by_category': {},
                'by_experience_level': {},
                'remote_stats': {'Yes': 0, 'No': 0, 'Hybrid': 0},
                'trusted_companies': 0
            }
            
            for job_key in job_keys:
                job_data = self.redis_client.hgetall(job_key)
                if not job_data:
                    continue
                
                stats['total_jobs'] += 1
                
                # Company stats
                company = job_data.get('company', 'Unknown')
                stats['by_company'][company] = stats['by_company'].get(company, 0) + 1
                
                # Location stats
                location = job_data.get('location', 'Unknown')
                stats['by_location'][location] = stats['by_location'].get(location, 0) + 1
                
                # Job type stats
                job_type = job_data.get('job_type', 'Unknown')
                stats['by_job_type'][job_type] = stats['by_job_type'].get(job_type, 0) + 1
                
                # Category stats
                category = job_data.get('category', 'Unknown')
                stats['by_category'][category] = stats['by_category'].get(category, 0) + 1
                
                # Experience level stats
                exp_level = job_data.get('experience_level', 'Unknown')
                stats['by_experience_level'][exp_level] = stats['by_experience_level'].get(exp_level, 0) + 1
                
                # Remote work stats
                remote = job_data.get('remote', 'No')
                if remote in stats['remote_stats']:
                    stats['remote_stats'][remote] += 1
                
                # Trusted company stats
                if job_data.get('is_trusted_company', 'False') == 'True':
                    stats['trusted_companies'] += 1
            
            # Sort top categories by count
            for category in ['by_company', 'by_location', 'by_job_type', 'by_category', 'by_experience_level']:
                stats[category] = dict(sorted(stats[category].items(), key=lambda x: x[1], reverse=True))
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting job statistics: {str(e)}")
            return {'error': str(e)}