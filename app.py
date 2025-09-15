from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import json
import os
import logging
from datetime import datetime
import traceback

# Import our Redis-powered modules
try:
    from cached_scraper import RedisCachedJobScraper
    REDIS_AVAILABLE = True
except ImportError:
    print("Warning: Could not import Redis modules. Make sure all required files are present.")
    REDIS_AVAILABLE = False

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder='.')
CORS(app)

# Redis configuration (can be moved to environment variables)
REDIS_CONFIG = {
    'redis_host': 'redis-13364.c56.east-us.azure.redns.redis-cloud.com',
    'redis_port': 13364,
    'redis_db': 0,
    'redis_password': 'liiSkjZQkhWPULcAcQ2dV0MZzy82wj2B',
    'cache_duration_hours': 72
}

# Initialize the Redis cached scraper
cached_scraper = None
if REDIS_AVAILABLE:
    try:
        cached_scraper = RedisCachedJobScraper(**REDIS_CONFIG)
        logger.info("RedisCachedJobScraper initialized successfully")
        
        # Test Redis connection
        health = cached_scraper.get_redis_health()
        if health.get('connected'):
            logger.info(f"Redis connected successfully - Version: {health.get('redis_version', 'unknown')}")
        else:
            logger.error(f"Redis connection failed: {health.get('error', 'Unknown error')}")
            
    except Exception as e:
        logger.error(f"Error initializing RedisCachedJobScraper: {str(e)}")
        cached_scraper = None

@app.route('/')
def index():
    """Serve the main HTML page"""
    return send_from_directory('.', 'index.html')

@app.route('/api/search', methods=['POST'])
def search_jobs():
    """Enhanced API endpoint to search for jobs with Redis caching"""
    try:
        data = request.get_json()
        
        # Extract search parameters
        keywords = data.get('keywords', 'software engineer')
        location = data.get('location', 'United States')
        max_jobs = int(data.get('max_jobs', 25))
        job_type_filter = data.get('job_type_filter')
        category_filter = data.get('category_filter')
        trusted_only = data.get('trusted_only', True)
        force_refresh = data.get('force_refresh', False)
        
        logger.info(f"Search request: keywords='{keywords}', location='{location}', "
                   f"max_jobs={max_jobs}, trusted_only={trusted_only}, force_refresh={force_refresh}")
        
        if cached_scraper:
            # Use Redis-powered scraper
            jobs_data = cached_scraper.get_jobs(
                keywords=keywords,
                location=location,
                max_jobs=max_jobs,
                job_type_filter=job_type_filter,
                category_filter=category_filter,
                trusted_only=trusted_only,
                force_refresh=force_refresh
            )
            
            # Get cache status for response
            cache_status = cached_scraper.get_cache_status()
            
            return jsonify({
                'success': True,
                'jobs': jobs_data,
                'count': len(jobs_data),
                'cached': not force_refresh,
                'cache_info': {
                    'total_searches': cache_status.get('total_searches', 0),
                    'total_jobs_cached': cache_status.get('total_jobs_cached', 0),
                    'redis_memory_mb': cache_status.get('redis_memory_used_mb', 0)
                },
                'timestamp': datetime.now().isoformat()
            })
        else:
            # Fallback to mock data if Redis scraper not available
            mock_jobs = get_mock_jobs(keywords, location, max_jobs)
            return jsonify({
                'success': True,
                'jobs': mock_jobs,
                'count': len(mock_jobs),
                'cached': False,
                'mock_data': True,
                'redis_available': False,
                'timestamp': datetime.now().isoformat()
            })
            
    except Exception as e:
        logger.error(f"Error in search_jobs: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/search/cached', methods=['POST'])
def search_cached_jobs():
    """API endpoint to search through cached jobs with specific criteria"""
    try:
        data = request.get_json()
        
        if not cached_scraper:
            return jsonify({
                'success': False,
                'error': 'Redis cache system not available',
                'timestamp': datetime.now().isoformat()
            }), 503
        
        # Extract search criteria
        title_keyword = data.get('title_keyword')
        company_keyword = data.get('company_keyword')
        location_keyword = data.get('location_keyword')
        remote_only = data.get('remote_only', False)
        trusted_only = data.get('trusted_only', False)
        limit = int(data.get('limit', 50))
        
        logger.info(f"Cached search: title='{title_keyword}', company='{company_keyword}', "
                   f"location='{location_keyword}', remote_only={remote_only}, trusted_only={trusted_only}")
        
        # Search cached jobs
        jobs_data = cached_scraper.search_cached_jobs(
            title_keyword=title_keyword,
            company_keyword=company_keyword,
            location_keyword=location_keyword,
            remote_only=remote_only,
            trusted_only=trusted_only,
            limit=limit
        )
        
        return jsonify({
            'success': True,
            'jobs': jobs_data,
            'count': len(jobs_data),
            'search_criteria': {
                'title_keyword': title_keyword,
                'company_keyword': company_keyword,
                'location_keyword': location_keyword,
                'remote_only': remote_only,
                'trusted_only': trusted_only,
                'limit': limit
            },
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error in search_cached_jobs: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/categories', methods=['GET'])
def get_job_categories():
    """Get available job categories"""
    try:
        if cached_scraper:
            categories = cached_scraper.get_job_categories()
        else:
            # Default categories if scraper not available
            categories = [
                'All', 'Software Engineering', 'Data Science & Analytics',
                'DevOps & Infrastructure', 'Product & Design', 'Cybersecurity',
                'Project Management', 'Sales & Marketing', 'Finance & Accounting',
                'Human Resources', 'Operations'
            ]
        
        return jsonify({
            'success': True,
            'categories': categories,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting categories: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/companies', methods=['GET'])
def get_trusted_companies():
    """Get list of trusted companies"""
    try:
        if cached_scraper:
            companies = cached_scraper.get_trusted_companies()
        else:
            # Sample trusted companies if scraper not available
            companies = [
                'google', 'microsoft', 'amazon', 'apple', 'meta', 'tesla',
                'netflix', 'salesforce', 'oracle', 'adobe', 'nvidia', 'intel'
            ]
        
        return jsonify({
            'success': True,
            'companies': sorted(companies),
            'count': len(companies),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting trusted companies: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/cache/status', methods=['GET'])
def cache_status():
    """Get comprehensive Redis cache status information"""
    try:
        if cached_scraper:
            cache_info = cached_scraper.get_cache_status()
            redis_health = cached_scraper.get_redis_health()
            
            return jsonify({
                'success': True,
                'cache_info': cache_info,
                'redis_health': redis_health,
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Redis cache system not available',
                'redis_available': False,
                'timestamp': datetime.now().isoformat()
            }), 503
            
    except Exception as e:
        logger.error(f"Error getting cache status: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/cache/clear', methods=['POST'])
def clear_cache():
    """Clear Redis cache (expired only or all)"""
    try:
        data = request.get_json() or {}
        expired_only = data.get('expired_only', True)
        
        if cached_scraper:
            cleared_count = cached_scraper.clear_cache(expired_only=expired_only)
            
            return jsonify({
                'success': True,
                'message': f'Cache cleared successfully ({"expired only" if expired_only else "all"})',
                'cleared_count': cleared_count,
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Redis cache system not available',
                'timestamp': datetime.now().isoformat()
            }), 503
            
    except Exception as e:
        logger.error(f"Error clearing cache: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/statistics', methods=['GET'])
def get_job_statistics():
    """Get detailed statistics about cached jobs"""
    try:
        if cached_scraper:
            job_stats = cached_scraper.get_job_statistics()
            
            return jsonify({
                'success': True,
                'statistics': job_stats,
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Redis cache system not available',
                'timestamp': datetime.now().isoformat()
            }), 503
            
    except Exception as e:
        logger.error(f"Error getting job statistics: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/export', methods=['POST'])
def export_jobs():
    """Export cached jobs to JSON with optional filtering"""
    try:
        data = request.get_json() or {}
        
        if not cached_scraper:
            return jsonify({
                'success': False,
                'error': 'Redis cache system not available',
                'timestamp': datetime.now().isoformat()
            }), 503
        
        # Extract filter criteria
        filter_criteria = {
            'title_keyword': data.get('title_keyword'),
            'company_keyword': data.get('company_keyword'),
            'location_keyword': data.get('location_keyword'),
            'remote_only': data.get('remote_only', False),
            'trusted_only': data.get('trusted_only', False),
            'limit': int(data.get('limit', 1000))
        }
        
        # Remove None values
        filter_criteria = {k: v for k, v in filter_criteria.items() if v is not None}
        
        export_data = cached_scraper.export_jobs_to_json(filter_criteria if filter_criteria else None)
        
        return jsonify({
            'success': True,
            'export_data': export_data,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error exporting jobs: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/bulk-update', methods=['POST'])
def bulk_update_jobs():
    """Bulk update job status in Redis"""
    try:
        data = request.get_json()
        job_updates = data.get('updates', [])
        
        if not cached_scraper:
            return jsonify({
                'success': False,
                'error': 'Redis cache system not available',
                'timestamp': datetime.now().isoformat()
            }), 503
        
        updated_count = cached_scraper.bulk_update_job_status(job_updates)
        
        return jsonify({
            'success': True,
            'updated_count': updated_count,
            'total_updates_requested': len(job_updates),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error in bulk update: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

def get_mock_jobs(keywords, location, max_jobs):
    """Generate enhanced mock job data for testing when Redis scraper is not available"""
    mock_jobs = [
        {
            'title': f'Senior {keywords.title()} Developer',
            'company': 'TechCorp Solutions',
            'location': location,
            'description': f'We are seeking an experienced {keywords} professional to join our dynamic team.',
            'requirements': [
                f'5+ years of experience in {keywords}',
                'Strong problem-solving skills',
                'Bachelor\'s degree in Computer Science'
            ],
            'job_type': 'Full-time',
            'skills': ['Python', 'JavaScript', 'React', 'Node.js', 'SQL', 'AWS'],
            'posted_date': datetime.now().strftime('%Y-%m-%d'),
            'job_url': f'https://example.com/jobs/senior-{keywords.lower().replace(" ", "-")}-developer',
            'salary': '$90,000 - $120,000',
            'category': 'Software Engineering',
            'is_trusted_company': True,
            'experience_level': 'Senior',
            'employment_type': 'Full-time',
            'job_id': f'mock-{hash(f"{keywords}-senior")%10000}',
            'remote_work': 'Hybrid'
        },
        {
            'title': f'Remote {keywords.title()} Specialist',
            'company': 'Innovation Labs',
            'location': 'Remote',
            'description': f'Full remote position for experienced {keywords} professional.',
            'requirements': [
                f'3+ years of {keywords} experience',
                'Ability to work independently',
                'Strong communication skills'
            ],
            'job_type': 'Full-time',
            'skills': ['Python', 'Docker', 'Kubernetes', 'PostgreSQL'],
            'posted_date': datetime.now().strftime('%Y-%m-%d'),
            'job_url': f'https://example.com/jobs/remote-{keywords.lower().replace(" ", "-")}-specialist',
            'salary': '$85,000 - $110,000',
            'category': 'Software Engineering',
            'is_trusted_company': True,
            'experience_level': 'Mid Level',
            'employment_type': 'Full-time',
            'job_id': f'mock-{hash(f"{keywords}-remote")%10000}',
            'remote_work': 'Yes'
        }
    ]
    
    return mock_jobs[:max_jobs]

@app.errorhandler(404)
def not_found_error(error):
    return jsonify({
        'success': False,
        'error': 'Endpoint not found',
        'timestamp': datetime.now().isoformat()
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'error': 'Internal server error',
        'timestamp': datetime.now().isoformat()
    }), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'redis_available': REDIS_AVAILABLE,
            'scraper_initialized': cached_scraper is not None
        }
        
        if cached_scraper:
            redis_health = cached_scraper.get_redis_health()
            health_status['redis_connected'] = redis_health.get('connected', False)
            health_status['redis_version'] = redis_health.get('redis_version', 'unknown')
        
        return jsonify(health_status)
        
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

if __name__ == '__main__':
    # Check if required files exist
    required_files = ['scraper.py', 'redis_cache.py', 'cached_scraper.py']
    missing_files = [f for f in required_files if not os.path.exists(f)]
    
    print("=" * 60)
    print("🚀 REDIS-POWERED LINKEDIN JOB SCRAPER")
    print("=" * 60)
    
    if missing_files:
        print(f"⚠️  Warning: Missing required files: {', '.join(missing_files)}")
        print("   The application will run with limited functionality.")
    
    if not REDIS_AVAILABLE:
        print("⚠️  Warning: Redis modules not available.")
        print("   Please ensure all Python files are in the same directory.")
    else:
        print("✅ Redis modules loaded successfully")
    
    # Redis connection status
    if cached_scraper:
        health = cached_scraper.get_redis_health()
        if health.get('connected'):
            print(f"✅ Redis connected: {health.get('redis_version', 'unknown')}")
            print(f"   Memory used: {health.get('used_memory_human', 'unknown')}")
        else:
            print(f"❌ Redis connection failed: {health.get('error', 'Unknown error')}")
    else:
        print("❌ Redis scraper not initialized")
    
    print("\n📍 Application URL: http://localhost:5000")
    print("\n🔧 API Endpoints:")
    print("   POST /api/search              - Search jobs with Redis caching")
    print("   POST /api/search/cached       - Search through cached jobs")
    print("   GET  /api/categories          - Get job categories")
    print("   GET  /api/companies           - Get trusted companies")
    print("   GET  /api/cache/status        - Get Redis cache status")
    print("   POST /api/cache/clear         - Clear Redis cache")
    print("   GET  /api/statistics          - Get job statistics")
    print("   POST /api/export              - Export jobs to JSON")
    print("   POST /api/bulk-update         - Bulk update job status")
    print("   GET  /health                  - Health check")
    
    print(f"\n🏢 Trusted Companies: {len(cached_scraper.get_trusted_companies()) if cached_scraper else '500+'}")
    print(f"📂 Job Categories: {len(cached_scraper.get_job_categories()) if cached_scraper else '10+'}")
    
    print("\n📋 Redis Hash Structure 'job-scraping':")
    print("   🔸 title, company, skills, salary, location")
    print("   🔸 job_type, experience_level, category, posted_date")
    print("   🔸 url, job_id, requirements, responsibilities")
    print("   🔸 employment_type, remote, is_trusted_company")
    
    print("\n🛠️  Setup Requirements:")
    print("   1. Redis server running on localhost:6379")
    print("   2. pip install redis flask flask-cors requests beautifulsoup4")
    print("   3. All Python files in same directory")
    
    print("=" * 60)
    
    try:
        app.run(debug=True, host='0.0.0.0', port=5000)
    except Exception as e:
        print(f"❌ Failed to start Flask application: {str(e)}")
        print("Please check if port 5000 is available and try again.")