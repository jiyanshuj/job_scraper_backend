import requests
import json
import time
import re
from bs4 import BeautifulSoup
from urllib.parse import urlencode, quote
from typing import Dict, List, Optional, Set
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LinkedInJobScraper:
    def __init__(self):
        self.base_url = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # Trusted companies list - Fortune 500 + Major Tech Companies
        self.trusted_companies = {
            # Major Tech Companies
            'google', 'microsoft', 'amazon', 'apple', 'meta', 'facebook', 'tesla', 'netflix',
            'salesforce', 'oracle', 'adobe', 'nvidia', 'intel', 'ibm', 'cisco', 'vmware',
            'spotify', 'uber', 'airbnb', 'twitter', 'linkedin', 'dropbox', 'slack', 'zoom',
            'shopify', 'square', 'stripe', 'paypal', 'ebay', 'reddit', 'pinterest', 'snap',
            'twilio', 'okta', 'snowflake', 'databricks', 'palantir', 'cloudflare', 'mongodb',
            
            # Financial Services
            'jpmorgan', 'goldman sachs', 'morgan stanley', 'bank of america', 'wells fargo',
            'citigroup', 'american express', 'visa', 'mastercard', 'blackrock', 'fidelity',
            'charles schwab', 'robinhood', 'coinbase', 'stripe', 'square',
            
            # Consulting & Professional Services
            'mckinsey', 'bain', 'bcg', 'deloitte', 'pwc', 'kpmg', 'ey', 'accenture',
            'ibm consulting', 'tcs', 'infosys', 'wipro', 'cognizant', 'capgemini',
            
            # Fortune 500 Companies
            'walmart', 'exxon mobil', 'berkshire hathaway', 'unitedhealth', 'mckesson',
            'cvs health', 'amazon', 'at&t', 'general motors', 'ford', 'verizon',
            'chevron', 'kroger', 'general electric', 'walgreens', 'phillips 66',
            'marathon petroleum', 'costco', 'cardinal health', 'express scripts',
            
            # Healthcare & Pharma
            'johnson & johnson', 'pfizer', 'merck', 'abbott', 'bristol myers squibb',
            'eli lilly', 'gilead', 'amgen', 'biogen', 'regeneron', 'moderna',
            'kaiser permanente', 'anthem', 'humana', 'centene',
            
            # Startups & Unicorns
            'openai', 'anthropic', 'canva', 'figma', 'notion', 'discord', 'github',
            'gitlab', 'atlassian', 'asana', 'monday.com', 'miro', 'airtable'
        }
        
        # Job categories mapping with related keywords
        self.job_categories = {
            'Software Engineering': [
                'software engineer', 'software developer', 'full stack developer', 
                'frontend developer', 'backend developer', 'web developer',
                'mobile developer', 'ios developer', 'android developer',
                'python developer', 'java developer', 'javascript developer',
                'react developer', 'node.js developer', '.net developer'
            ],
            'Data Science & Analytics': [
                'data scientist', 'data analyst', 'data engineer', 'ml engineer',
                'machine learning engineer', 'ai engineer', 'research scientist',
                'business analyst', 'business intelligence', 'data visualization',
                'statistician', 'quantitative analyst', 'analytics engineer'
            ],
            'DevOps & Infrastructure': [
                'devops engineer', 'cloud engineer', 'infrastructure engineer',
                'site reliability engineer', 'platform engineer', 'systems engineer',
                'network engineer', 'security engineer', 'aws engineer',
                'kubernetes engineer', 'docker', 'terraform'
            ],
            'Product & Design': [
                'product manager', 'product owner', 'ux designer', 'ui designer',
                'product designer', 'user experience', 'user interface',
                'design lead', 'creative director', 'graphic designer'
            ],
            'Cybersecurity': [
                'security engineer', 'cybersecurity analyst', 'security architect',
                'penetration tester', 'security consultant', 'incident response',
                'vulnerability assessment', 'compliance analyst'
            ],
            'Project Management': [
                'project manager', 'program manager', 'scrum master',
                'agile coach', 'delivery manager', 'technical program manager',
                'pmp', 'project coordinator'
            ],
            'Sales & Marketing': [
                'sales representative', 'account manager', 'business development',
                'marketing manager', 'digital marketing', 'growth marketing',
                'content marketing', 'social media manager', 'seo specialist'
            ],
            'Finance & Accounting': [
                'financial analyst', 'accountant', 'controller', 'cfo',
                'investment analyst', 'risk analyst', 'auditor',
                'financial planner', 'treasury analyst'
            ],
            'Human Resources': [
                'hr manager', 'recruiter', 'talent acquisition', 'hr business partner',
                'compensation analyst', 'learning and development', 'hr generalist'
            ],
            'Operations': [
                'operations manager', 'supply chain', 'logistics coordinator',
                'business operations', 'process improvement', 'quality assurance'
            ]
        }
    
    def is_trusted_company(self, company_name: str) -> bool:
        """Check if a company is in the trusted companies list"""
        if not company_name:
            return False
        
        company_lower = company_name.lower().strip()
        
        # Direct match
        if company_lower in self.trusted_companies:
            return True
        
        # Partial match for companies with variations
        for trusted in self.trusted_companies:
            if trusted in company_lower or company_lower in trusted:
                return True
        
        return False
    
    def get_job_category(self, title: str, description: str = "") -> str:
        """Determine job category based on title and description"""
        title_lower = title.lower()
        desc_lower = description.lower()
        combined_text = f"{title_lower} {desc_lower}"
        
        category_scores = {}
        
        for category, keywords in self.job_categories.items():
            score = 0
            for keyword in keywords:
                # Higher weight for title matches
                if keyword in title_lower:
                    score += 3
                # Lower weight for description matches
                elif keyword in desc_lower:
                    score += 1
            
            if score > 0:
                category_scores[category] = score
        
        if category_scores:
            return max(category_scores, key=category_scores.get)
        
        return 'Other'
    
    def build_search_params(self, keywords: str = "software engineer", location: str = "United States", 
                          start: int = 0, count: int = 25, job_type_filter: str = None) -> Dict:
        """Build search parameters for LinkedIn API"""
        params = {
            'keywords': keywords,
            'location': location,
            'start': start,
            'count': count,
            'f_TPR': '',  # Time posted (empty for all)
        }
        
        # Job type filter mapping
        job_type_mapping = {
            'full-time': 'F',
            'part-time': 'P', 
            'contract': 'C',
            'temporary': 'T',
            'internship': 'I',
            'volunteer': 'V'
        }
        
        if job_type_filter and job_type_filter.lower() in job_type_mapping:
            params['f_JT'] = job_type_mapping[job_type_filter.lower()]
        else:
            params['f_JT'] = ''
        
        return params
    
    def extract_job_details(self, job_html: str) -> Dict:
        """Extract job details from HTML content"""
        soup = BeautifulSoup(job_html, 'html.parser')
        
        job_data = {
            'title': '',
            'company': '',
            'location': '',
            'description': '',
            'requirements': [],
            'job_type': '',
            'skills': [],
            'posted_date': '',
            'job_url': '',
            'salary': '',
            'category': '',
            'is_trusted_company': False,
            'experience_level': '',
            'employment_type': ''
        }
        
        try:
            # Extract job title
            title_elem = soup.find('h3', class_='base-search-card__title')
            if not title_elem:
                title_elem = soup.find('a', class_='base-card__full-link')
            if title_elem:
                job_data['title'] = title_elem.get_text().strip()
            
            # Extract company name
            company_elem = soup.find('h4', class_='base-search-card__subtitle')
            if not company_elem:
                company_elem = soup.find('a', {'data-tracking-control-name': 'public_jobs_jserp-result_job-search-card-subtitle'})
            if company_elem:
                company_link = company_elem.find('a')
                if company_link:
                    job_data['company'] = company_link.get_text().strip()
                else:
                    job_data['company'] = company_elem.get_text().strip()
            
            # Check if company is trusted
            job_data['is_trusted_company'] = self.is_trusted_company(job_data['company'])
            
            # Extract location
            location_elem = soup.find('span', class_='job-search-card__location')
            if location_elem:
                job_data['location'] = location_elem.get_text().strip()
            
            # Extract job URL
            job_link = soup.find('a', {'data-tracking-control-name': 'public_jobs_jserp-result_search-card'})
            if not job_link:
                job_link = soup.find('a', class_='base-card__full-link')
            if job_link and job_link.get('href'):
                job_data['job_url'] = job_link['href']
            
            # Extract posted date
            time_elem = soup.find('time', class_='job-search-card__listdate')
            if not time_elem:
                time_elem = soup.find('time')
            if time_elem:
                job_data['posted_date'] = time_elem.get('datetime', time_elem.get_text().strip())
            
            # Detect job type and experience level from title
            job_data['job_type'] = self.detect_job_type(job_data['title'])
            job_data['experience_level'] = self.detect_experience_level(job_data['title'])
            
            # Extract additional metadata
            metadata_elem = soup.find('div', class_='base-search-card__metadata')
            if metadata_elem:
                metadata_text = metadata_elem.get_text().strip()
                job_data['employment_type'] = self.parse_employment_type(metadata_text)
            
        except Exception as e:
            logger.error(f"Error extracting job details: {str(e)}")
        
        return job_data
    
    def detect_job_type(self, title: str) -> str:
        """Detect job type from job title"""
        title_lower = title.lower()
        
        if any(keyword in title_lower for keyword in ['intern', 'internship']):
            return 'Internship'
        elif any(keyword in title_lower for keyword in ['contract', 'contractor', 'freelance', 'temporary']):
            return 'Contract'
        elif any(keyword in title_lower for keyword in ['part-time', 'part time']):
            return 'Part-time'
        else:
            return 'Full-time'
    
    def detect_experience_level(self, title: str) -> str:
        """Detect experience level from job title"""
        title_lower = title.lower()
        
        if any(keyword in title_lower for keyword in ['senior', 'sr.', 'lead', 'principal', 'staff']):
            return 'Senior'
        elif any(keyword in title_lower for keyword in ['junior', 'jr.', 'entry', 'associate', 'intern']):
            return 'Entry Level'
        elif any(keyword in title_lower for keyword in ['mid', 'intermediate']):
            return 'Mid Level'
        else:
            return 'Mid Level'  # Default
    
    def parse_employment_type(self, metadata_text: str) -> str:
        """Parse employment type from metadata"""
        metadata_lower = metadata_text.lower()
        
        if 'full-time' in metadata_lower:
            return 'Full-time'
        elif 'part-time' in metadata_lower:
            return 'Part-time'
        elif 'contract' in metadata_lower:
            return 'Contract'
        elif 'internship' in metadata_lower:
            return 'Internship'
        else:
            return 'Full-time'  # Default
    
    def get_job_description(self, job_url: str) -> Dict:
        """Fetch detailed job description from job URL"""
        try:
            if not job_url.startswith('http'):
                job_url = f"https://www.linkedin.com{job_url}"
            
            response = self.session.get(job_url, timeout=15)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Extract job description
                description_elem = soup.find('div', class_='show-more-less-html__markup')
                if not description_elem:
                    description_elem = soup.find('div', class_='description__text')
                
                description = ''
                if description_elem:
                    description = description_elem.get_text().strip()
                
                # Extract requirements and skills
                requirements, skills = self.parse_description_for_requirements(description)
                
                # Extract salary if available
                salary = self.extract_salary_info(soup)
                
                return {
                    'description': description,
                    'requirements': requirements,
                    'skills': skills,
                    'salary': salary
                }
        except Exception as e:
            logger.error(f"Error fetching job description from {job_url}: {str(e)}")
        
        return {'description': '', 'requirements': [], 'skills': [], 'salary': ''}
    
    def extract_salary_info(self, soup) -> str:
        """Extract salary information from job page"""
        try:
            # Look for salary information in various possible locations
            salary_selectors = [
                '.salary',
                '.compensation-text',
                '[data-automation-id="salary"]',
                '.jobs-unified-top-card__job-insight'
            ]
            
            for selector in salary_selectors:
                salary_elem = soup.select_one(selector)
                if salary_elem:
                    salary_text = salary_elem.get_text().strip()
                    if any(char.isdigit() for char in salary_text) and ('$' in salary_text or 'USD' in salary_text):
                        return salary_text
            
        except Exception as e:
            logger.error(f"Error extracting salary: {str(e)}")
        
        return ''
    
    def parse_description_for_requirements(self, description: str) -> tuple:
        """Parse job description to extract requirements and skills"""
        requirements = []
        skills = set()
        
        # Expanded skill keywords by category
        skill_categories = {
            'Programming Languages': [
                'python', 'java', 'javascript', 'typescript', 'c++', 'c#', '.net',
                'php', 'ruby', 'go', 'rust', 'swift', 'kotlin', 'scala', 'r',
                'matlab', 'perl', 'objective-c', 'dart', 'elixir'
            ],
            'Web Technologies': [
                'react', 'angular', 'vue.js', 'node.js', 'express', 'django',
                'flask', 'spring', 'laravel', 'rails', 'asp.net', 'html',
                'css', 'sass', 'less', 'webpack', 'babel', 'jquery'
            ],
            'Databases': [
                'sql', 'mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch',
                'oracle', 'sql server', 'sqlite', 'cassandra', 'dynamodb',
                'neo4j', 'influxdb', 'mariadb'
            ],
            'Cloud & DevOps': [
                'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'terraform',
                'ansible', 'jenkins', 'git', 'github', 'gitlab', 'bitbucket',
                'ci/cd', 'linux', 'ubuntu', 'centos', 'nginx', 'apache'
            ],
            'Data & Analytics': [
                'machine learning', 'deep learning', 'artificial intelligence',
                'ai', 'data science', 'pandas', 'numpy', 'scikit-learn',
                'tensorflow', 'pytorch', 'keras', 'tableau', 'power bi',
                'spark', 'hadoop', 'kafka', 'airflow'
            ],
            'Mobile': [
                'ios', 'android', 'react native', 'flutter', 'xamarin',
                'cordova', 'ionic', 'swift', 'objective-c', 'kotlin', 'java'
            ]
        }
        
        # Flatten all skills
        all_skills = []
        for category_skills in skill_categories.values():
            all_skills.extend(category_skills)
        
        description_lower = description.lower()
        
        # Extract skills (case-insensitive matching)
        for skill in all_skills:
            if skill.lower() in description_lower:
                skills.add(skill.title())
        
        # Extract requirements using more sophisticated patterns
        requirement_patterns = [
            r'(?:required|must have|essential|mandatory)[:\s]([^.!?]{10,100})',
            r'(?:minimum|at least)[\s]+(\d+[\s]*(?:years?|yrs?)[\s]*(?:of)?[\s]*experience)',
            r'(?:bachelor|master|phd|degree)[^.!?]{0,50}',
            r'(?:experience with|proficiency in|knowledge of)[^.!?]{10,80}',
            r'(?:strong|excellent|solid)[\s]+(?:knowledge|understanding|experience)[^.!?]{10,80}'
        ]
        
        for pattern in requirement_patterns:
            matches = re.finditer(pattern, description, re.IGNORECASE | re.DOTALL)
            for match in matches:
                requirement = match.group(0).strip()
                if len(requirement) > 15 and len(requirement) < 200:  # Filter reasonable length
                    requirements.append(requirement)
        
        # Also extract bullet points and numbered lists
        sentences = re.split(r'[.!?•·‣▪▫-]\s*', description)
        for sentence in sentences:
            sentence = sentence.strip()
            sentence_lower = sentence.lower()
            
            # Look for requirement indicators
            if any(indicator in sentence_lower for indicator in [
                'required', 'must have', 'essential', 'mandatory', 'minimum',
                'years of experience', 'degree', 'certification', 'preferred'
            ]):
                if 20 <= len(sentence) <= 150:  # Reasonable length
                    requirements.append(sentence)
        
        # Remove duplicates and limit results
        requirements = list(dict.fromkeys(requirements))[:8]  # Keep unique, limit to 8
        skills = list(skills)[:12]  # Limit to 12 skills
        
        return requirements, skills
    
    def filter_by_category(self, jobs: List[Dict], category: str) -> List[Dict]:
        """Filter jobs by category"""
        if category == 'All' or not category:
            return jobs
        
        filtered_jobs = []
        for job in jobs:
            # Determine category if not already set
            if not job.get('category'):
                job['category'] = self.get_job_category(job['title'], job.get('description', ''))
            
            if job['category'] == category:
                filtered_jobs.append(job)
        
        return filtered_jobs
    
    def make_request_with_backoff(self, url: str, params: Dict = None, max_retries: int = 3,
                                base_timeout: int = 30) -> requests.Response:
        """
        Make HTTP request with exponential backoff and retry logic

        Args:
            url: URL to request
            params: Query parameters
            max_retries: Maximum number of retry attempts
            base_timeout: Base timeout in seconds

        Returns:
            Response object

        Raises:
            Exception: If all retries fail
        """
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, params=params, timeout=base_timeout)

                # Handle rate limiting (429 Too Many Requests)
                if response.status_code == 429:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(f"Rate limited (429). Waiting {wait_time}s before retry {attempt + 1}/{max_retries}")
                    time.sleep(wait_time)
                    continue

                # Handle other client/server errors
                if response.status_code >= 400:
                    if attempt == max_retries - 1:
                        logger.error(f"Request failed with status {response.status_code} after {max_retries} attempts")
                        response.raise_for_status()
                    else:
                        wait_time = 2 ** attempt
                        logger.warning(f"Request failed with status {response.status_code}. Retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                        continue

                return response

            except requests.exceptions.Timeout as e:
                if attempt == max_retries - 1:
                    logger.error(f"Request timed out after {max_retries} attempts: {str(e)}")
                    raise
                wait_time = 2 ** attempt
                logger.warning(f"Request timed out. Retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait_time)

            except requests.exceptions.ConnectionError as e:
                if attempt == max_retries - 1:
                    logger.error(f"Connection error after {max_retries} attempts: {str(e)}")
                    raise
                wait_time = 2 ** attempt
                logger.warning(f"Connection error. Retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait_time)

            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"Request failed after {max_retries} attempts: {str(e)}")
                    raise
                wait_time = 2 ** attempt
                logger.warning(f"Request failed: {str(e)}. Retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait_time)

        # This should never be reached, but just in case
        raise Exception(f"Request failed after {max_retries} attempts")

    def scrape_jobs(self, keywords: str = "software engineer", location: str = "United States",
                   max_jobs: int = 50, job_type_filter: str = None, category_filter: str = None,
                   trusted_only: bool = True) -> List[Dict]:
        """
        Main method to scrape LinkedIn jobs with advanced filtering and retry logic

        Args:
            keywords: Job search keywords
            location: Job location
            max_jobs: Maximum number of jobs to return
            job_type_filter: Filter by job type (full-time, part-time, contract, internship)
            category_filter: Filter by job category
            trusted_only: Only return jobs from trusted companies

        Returns:
            List of job dictionaries
        """
        all_jobs = []
        start = 0
        count = 25

        logger.info(f"Starting job scraping: keywords='{keywords}', location='{location}', "
                   f"max_jobs={max_jobs}, trusted_only={trusted_only}")

        while len(all_jobs) < max_jobs:
            try:
                params = self.build_search_params(keywords, location, start, count, job_type_filter)

                logger.info(f"Fetching jobs: start={start}, count={count}")

                # Use enhanced request method with retry and backoff
                response = self.make_request_with_backoff(self.base_url, params=params, max_retries=3, base_timeout=30)

                soup = BeautifulSoup(response.content, 'html.parser')
                job_cards = soup.find_all('div', class_=['base-card', 'job-search-card'])

                if not job_cards:
                    logger.info("No more job cards found")
                    break

                jobs_added_this_batch = 0

                for card in job_cards:
                    if len(all_jobs) >= max_jobs:
                        break

                    job_data = self.extract_job_details(str(card))

                    # Skip if company is not trusted (when trusted_only is True)
                    if trusted_only and not job_data['is_trusted_company']:
                        continue

                    # Get detailed description if URL is available
                    if job_data['job_url']:
                        detailed_info = self.get_job_description(job_data['job_url'])
                        job_data.update(detailed_info)

                    # Determine job category
                    job_data['category'] = self.get_job_category(
                        job_data['title'],
                        job_data.get('description', '')
                    )

                    all_jobs.append(job_data)
                    jobs_added_this_batch += 1

                    # Add delay to be respectful to LinkedIn's servers
                    time.sleep(0.5)

                # If no jobs were added in this batch, break to avoid infinite loop
                if jobs_added_this_batch == 0:
                    logger.info("No qualifying jobs found in this batch")
                    break

                start += count
                time.sleep(2)  # Delay between pages

            except Exception as e:
                logger.error(f"Error during scraping: {str(e)}")
                break

        # Apply category filter if specified
        if category_filter and category_filter != 'All':
            all_jobs = self.filter_by_category(all_jobs, category_filter)

        logger.info(f"Successfully scraped {len(all_jobs)} jobs")
        return all_jobs
    
    def get_available_categories(self) -> List[str]:
        """Get list of available job categories"""
        return ['All'] + list(self.job_categories.keys())
    
    def get_trusted_companies_list(self) -> List[str]:
        """Get list of trusted companies"""
        return sorted(list(self.trusted_companies))

# Example usage
if __name__ == "__main__":
    scraper = LinkedInJobScraper()
    
    # Test the enhanced scraper
    jobs = scraper.scrape_jobs(
        keywords="python developer",
        location="San Francisco",
        max_jobs=10,
        category_filter="Software Engineering",
        trusted_only=True
    )
    
    # Print results
    for i, job in enumerate(jobs, 1):
        print(f"\n--- Job {i} ---")
        print(f"Title: {job['title']}")
        print(f"Company: {job['company']} {'✓ Trusted' if job['is_trusted_company'] else '✗ Not Trusted'}")
        print(f"Location: {job['location']}")
        print(f"Category: {job['category']}")
        print(f"Job Type: {job['job_type']}")
        print(f"Experience Level: {job['experience_level']}")
        print(f"Skills: {', '.join(job['skills'][:5])}")
        if job['salary']:
            print(f"Salary: {job['salary']}")
        print(f"Posted: {job['posted_date']}")
        
    print(f"\nAvailable Categories: {scraper.get_available_categories()}")
    print(f"Total Trusted Companies: {len(scraper.get_trusted_companies_list())}")