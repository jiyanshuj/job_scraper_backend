from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import json
import os
import logging
from datetime import datetime

# Import our custom modules
try:
    from cache import CachedJobScraper
except ImportError:
    print("Warning: Could not import cache module. Make sure cache.py and scraper.py are in the same directory.")
    CachedJobScraper = None

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder='.')
CORS(app)

# Initialize the cached scraper
cached_scraper = None
if CachedJobScraper:
    try:
        cached_scraper = CachedJobScraper(cache_duration_hours=72)  # 3 days cache
        logger.info("CachedJobScraper initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing CachedJobScraper: {str(e)}")

@app.route('/')
def index():
    """Serve the main HTML page"""
    return send_from_directory('.', 'index.html')

@app.route('/api/search', methods=['POST'])
def search_jobs():
    """API endpoint to search for jobs"""
    try:
        data = request.get_json()
        keywords = data.get('keywords', 'software engineer')
        location = data.get('location', 'United States')
        max_jobs = int(data.get('max_jobs', 25))
        force_refresh = data.get('force_refresh', False)
        
        logger.info(f"Search request: keywords='{keywords}', location='{location}', max_jobs={max_jobs}, force_refresh={force_refresh}")
        
        if cached_scraper:
            # Use the real scraper
            jobs_data = cached_scraper.get_jobs(
                keywords=keywords,
                location=location,
                max_jobs=max_jobs,
                force_refresh=force_refresh
            )
            
            return jsonify({
                'success': True,
                'jobs': jobs_data,
                'count': len(jobs_data),
                'cached': not force_refresh,
                'timestamp': datetime.now().isoformat()
            })
        else:
            # Return mock data if scraper is not available
            mock_jobs = get_mock_jobs(keywords, location, max_jobs)
            return jsonify({
                'success': True,
                'jobs': mock_jobs,
                'count': len(mock_jobs),
                'cached': False,
                'mock_data': True,
                'timestamp': datetime.now().isoformat()
            })
            
    except Exception as e:
        logger.error(f"Error in search_jobs: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/cache/status', methods=['GET'])
def cache_status():
    """Get cache status information"""
    try:
        if cached_scraper:
            cache_info = cached_scraper.get_cache_status()
            return jsonify({
                'success': True,
                'cache_info': cache_info,
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Cache system not available',
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
    """Clear cache (expired only or all)"""
    try:
        data = request.get_json() or {}
        expired_only = data.get('expired_only', True)
        
        if cached_scraper:
            cached_scraper.clear_cache(expired_only=expired_only)
            
            return jsonify({
                'success': True,
                'message': f'Cache cleared successfully ({"expired only" if expired_only else "all"})',
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Cache system not available',
                'timestamp': datetime.now().isoformat()
            }), 503
            
    except Exception as e:
        logger.error(f"Error clearing cache: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

def get_mock_jobs(keywords, location, max_jobs):
    """Generate mock job data for testing when scraper is not available"""
    mock_jobs = [
        {
            'title': f'Senior {keywords.title()} Developer',
            'company': 'TechCorp Solutions',
            'location': location,
            'description': f'We are seeking an experienced {keywords} professional to join our dynamic team. You will work on cutting-edge projects and collaborate with talented developers.',
            'requirements': [
                f'5+ years of experience in {keywords}',
                'Strong problem-solving skills',
                'Bachelor\'s degree in Computer Science or related field',
                'Experience with agile development methodologies'
            ],
            'job_type': 'Full-time',
            'skills': ['Python', 'JavaScript', 'React', 'Node.js', 'SQL', 'AWS'],
            'posted_date': datetime.now().strftime('%Y-%m-%d'),
            'job_url': f'https://example.com/jobs/senior-{keywords.lower().replace(" ", "-")}-developer',
            'salary': '$90,000 - $120,000'
        },
        {
            'title': f'{keywords.title()} Intern',
            'company': 'Innovation Labs',
            'location': location,
            'description': f'Great opportunity for students to gain hands-on experience in {keywords}. Work alongside experienced professionals and contribute to real projects.',
            'requirements': [
                f'Currently studying Computer Science or related field',
                f'Basic knowledge of {keywords}',
                'Eagerness to learn and grow',
                'Good communication skills'
            ],
            'job_type': 'Internship',
            'skills': ['Python', 'Git', 'HTML', 'CSS'],
            'posted_date': datetime.now().strftime('%Y-%m-%d'),
            'job_url': f'https://example.com/jobs/{keywords.lower().replace(" ", "-")}-intern',
            'salary': '$20/hour'
        },
        {
            'title': f'Contract {keywords.title()} Specialist',
            'company': 'Freelance Solutions Inc',
            'location': 'Remote',
            'description': f'Contract position for experienced {keywords} professional. Work on diverse projects with flexible schedule and competitive rates.',
            'requirements': [
                f'3+ years of {keywords} experience',
                'Ability to work independently',
                'Strong portfolio of previous work',
                'Available for 6-month contract'
            ],
            'job_type': 'Contract',
            'skills': ['Python', 'Django', 'PostgreSQL', 'Docker'],
            'posted_date': datetime.now().strftime('%Y-%m-%d'),
            'job_url': f'https://example.com/jobs/contract-{keywords.lower().replace(" ", "-")}-specialist',
            'salary': '$65/hour'
        },
        {
            'title': f'Part-time {keywords.title()}',
            'company': 'Startup Hub',
            'location': location,
            'description': f'Perfect for professionals seeking part-time work in {keywords}. Join our growing startup and make a real impact.',
            'requirements': [
                f'2+ years of {keywords} experience',
                'Available 20-25 hours per week',
                'Self-motivated and organized',
                'Startup experience preferred'
            ],
            'job_type': 'Part-time',
            'skills': ['Python', 'Flask', 'MySQL', 'Linux'],
            'posted_date': datetime.now().strftime('%Y-%m-%d'),
            'job_url': f'https://example.com/jobs/part-time-{keywords.lower().replace(" ", "-")}',
            'salary': '$45/hour'
        },
        {
            'title': f'Lead {keywords.title()} Architect',
            'company': 'Enterprise Systems Corp',
            'location': location,
            'description': f'Leadership role for senior {keywords} professional. Design and implement large-scale systems and mentor junior developers.',
            'requirements': [
                f'8+ years of {keywords} experience',
                'Previous leadership experience',
                'Strong system design skills',
                'Experience with microservices architecture'
            ],
            'job_type': 'Full-time',
            'skills': ['Python', 'Microservices', 'Kubernetes', 'AWS', 'System Design'],
            'posted_date': datetime.now().strftime('%Y-%m-%d'),
            'job_url': f'https://example.com/jobs/lead-{keywords.lower().replace(" ", "-")}-architect',
            'salary': '$140,000 - $180,000'
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

if __name__ == '__main__':
    # Check if required files exist
    required_files = ['index.html', 'scraper.py', 'cache.py']
    missing_files = [f for f in required_files if not os.path.exists(f)]
    
    if missing_files:
        print(f"Warning: Missing required files: {', '.join(missing_files)}")
        print("The application will run with limited functionality.")
    
    print("Starting Enhanced LinkedIn Job Scraper Web Application...")
    print("Open your browser and navigate to: http://localhost:5000")
    print("\nNew Features:")
    print("✓ Trusted company filtering (Fortune 500 + Major Tech)")
    print("✓ Job category classification (10+ categories)")
    print("✓ Advanced filtering by job type and experience level")
    print("✓ Enhanced skill extraction and requirement parsing")
    print("✓ 3-day intelligent caching system")
    print("\nAPI Endpoints:")
    print("- POST /api/search - Search for jobs with advanced filters")
    print("- GET /api/categories - Get available job categories")  
    print("- GET /api/companies - Get list of trusted companies")
    print("- GET /api/cache/status - Get cache status")
    print("- POST /api/cache/clear - Clear cache")
    print(f"\nTrusted Companies: {len(cached_scraper.get_trusted_companies()) if cached_scraper else '500+'}")
    print(f"Job Categories: {len(cached_scraper.get_job_categories()) if cached_scraper else '10+'}")
    
    app.run(debug=True, host='0.0.0.0', port=5000)