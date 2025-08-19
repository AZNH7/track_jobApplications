"""
LinkedIn Job Scraper

Handles all LinkedIn-specific job scraping functionality with support for authenticated scraping.
"""

import requests
import time
import random
import os
from datetime import datetime
from urllib.parse import urlencode, urljoin
from typing import List, Dict, Optional, Any
from bs4 import BeautifulSoup, Tag
import re

# Load environment variables for authentication
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("⚠️ python-dotenv not found. Install with: pip install python-dotenv")

try:
    from .base_scraper import BaseScraper
except ImportError:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from base_scraper import BaseScraper


class LinkedInScraper(BaseScraper):
    """LinkedIn-specific job scraper with authenticated scraping support."""
    
    def __init__(self, debug: bool = False, use_flaresolverr: bool = False):
        """
        Initialize LinkedIn scraper.
        
        Args:
            debug: Enable debug logging
            use_flaresolverr: Use FlareSolverr for requests
        """
        super().__init__(debug, use_flaresolverr)
        self.platform_name = "linkedin"
        self.base_url = "https://www.linkedin.com"
        
        # Get the LinkedIn session cookie from environment variable
        self.li_at_cookie = os.getenv('LINKEDIN_LI_AT')
        if not self.li_at_cookie or self.li_at_cookie == "Your_long_cookie_string_goes_here":
            print("⚠️ WARNING: LinkedIn `li_at` cookie not found or not configured.")
            print("   Create a .env file with LINKEDIN_LI_AT='your_cookie_value' for authenticated scraping.")
            print("   Scraping will continue without authentication (limited results).")
            self.li_at_cookie = None
        else:
            print("✅ LinkedIn authentication cookie found - using authenticated scraping")
            self.li_at_cookie = self.li_at_cookie.strip('"')  # Remove quotes if present

    def get_platform_name(self) -> str:
        """Return the platform name."""
        return "LinkedIn"

    def _clean_search_term(self, term: str) -> str:
        """Clean and prepare search term."""
        return re.sub(r'\s+', ' ', term).strip()

    def _clean_location_term(self, term: str) -> str:
        """Clean and prepare location term."""
        return term.strip()

    def _validate_job_data(self, job_data: Dict) -> bool:
        """Validate that essential job data fields are present."""
        return all(job_data.get(key) for key in ['title', 'company', 'url'])

    def _clean_linkedin_url(self, url: str) -> str:
        """Clean LinkedIn job URL to remove tracking parameters."""
        if '?' in url:
            return url.split('?')[0]
        return url

    def search_jobs(self, keywords: str, location: str = "", max_pages: int = 3, 
                   english_only: bool = False, **kwargs) -> List[Dict]:
        """
        Search LinkedIn jobs using a public API approach.
        
        Args:
            keywords: Job search keywords (can be a single string or comma-separated)
            location: Job location
            max_pages: Maximum number of pages to scrape
            english_only: This parameter is noted but language filtering is handled later.
            **kwargs: Additional arguments
            
        Returns:
            List of job dictionaries
        """
        print(f"🔍 LinkedIn Job Search: {keywords} in {location or 'Not specified'}")
        
        all_jobs = []
        
        keyword_list = [k.strip() for k in keywords.split(',') if k.strip()]
        if not keyword_list:
            keyword_list = [keywords]

        for keyword in keyword_list:
            print(f"\n--- Searching for keyword: '{keyword}' ---")
            try:
                api_jobs = self._search_linkedin_public(keyword, location, max_pages)
                all_jobs.extend(api_jobs)
                print(f"✅ Found {len(api_jobs)} jobs for '{keyword}' via LinkedIn public API")
            except Exception as e:
                print(f"⚠️ LinkedIn public API search for '{keyword}' failed: {e}")

            sleep_time = random.uniform(2, 5)
            print(f"   ... waiting {sleep_time:.2f} seconds before next keyword ...")
            time.sleep(sleep_time)

        # Deduplicate results
        seen_urls = set()
        unique_jobs = []
        for job in all_jobs:
            if (job_url := job.get('url')) and job_url not in seen_urls:
                unique_jobs.append(job)
                seen_urls.add(job_url)

        print(f"\n🎯 Total unique LinkedIn jobs found: {len(unique_jobs)}")
        
        return unique_jobs
    
    def _search_linkedin_public(self, keywords: str, location: str, max_pages: int) -> List[Dict]:
        """Search LinkedIn jobs using authenticated API approach."""
        jobs = []
        
        clean_keywords = self._clean_search_term(keywords)
        clean_location = self._clean_location_term(location)
        
        # Handle remote jobs specially for LinkedIn
        if clean_location.lower() == "remote":
            # For remote jobs, use Germany as location but add remote filter
            search_location = "Germany"
            remote_filter = True
        else:
            search_location = clean_location
            remote_filter = False
        
        # Define the cookies dictionary for authenticated requests
        cookies = {}
        if self.li_at_cookie:
            cookies = {'li_at': self.li_at_cookie}
            print(f"🔐 Using authenticated LinkedIn search with session cookie")
        else:
            print(f"⚠️ Using unauthenticated LinkedIn search (limited results)")
        
        for page in range(max_pages):
            start = page * 25 # LinkedIn uses a start index, 25 jobs per page
            
            params = {
                'keywords': clean_keywords,
                'location': search_location,
                'f_TPR': 'r604800',  # Past week
                'sortBy': 'DD',  # Sort by date
                'start': start
            }
            
            # Add remote work filter for remote searches
            if remote_filter:
                params['f_WT'] = '2'  # Remote work filter
                params['geoId'] = '101282230'  # Germany geo ID
                params['distance'] = '25'  # Distance parameter
            
            api_url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?{urlencode(params)}"
            
            print(f"🔍 Searching LinkedIn {'AUTHENTICATED' if self.li_at_cookie else 'public'} API page {page+1}: {clean_keywords} in {clean_location or 'anywhere'}")
            
            # Use authenticated request if cookie is available
            response = self.get_page(api_url, timeout=30, cookies=cookies)
            if response and response.status_code == 200:
                soup = self.get_soup(response.content)
            else:
                status = response.status_code if response else "N/A"
                print(f"   ❌ Failed to fetch LinkedIn public API: {api_url} (Status: {status})")
                break
                
            if not soup:
                print("   ❌ Failed to parse response content.")
                break

            job_cards = soup.find_all('div', {'class': 'base-card'})
            
            if not job_cards:
                print("   ⚠️ No job cards found on this page. Ending search for this keyword.")
                break
            
            print(f"   📊 Found {len(job_cards)} job cards in API response")
            
            for card in job_cards:
                try:
                    if isinstance(card, Tag):
                        job_data = self._parse_linkedin_job_card(card)
                        if job_data and self._validate_job_data(job_data):
                            jobs.append(job_data)
                except Exception as e:
                    if self.debug:
                        print(f"   ❌ Error parsing LinkedIn job card: {e}")
                    continue
        
        return jobs
    
    def _parse_linkedin_job_card(self, card: Tag) -> Optional[Dict]:
        """Parse a job from a LinkedIn job card."""
        try:
            job_data = {}

            title_elem = card.find('h3', class_='base-search-card__title')
            job_data['title'] = title_elem.text.strip() if title_elem else ''

            company_elem = card.find('h4', class_='base-search-card__subtitle')
            job_data['company'] = company_elem.text.strip() if company_elem else ''

            location_elem = card.find('span', class_='job-search-card__location')
            job_data['location'] = location_elem.text.strip() if location_elem else ''

            url_elem = card.find('a', class_='base-card__full-link')
            job_data['url'] = self._clean_linkedin_url(url_elem['href']) if url_elem and 'href' in url_elem.attrs else ''

            # Try to extract basic description from card if available
            description = ''
            description_selectors = [
                '.base-search-card__metadata',
                '.job-search-card__snippet',
                '.base-card__metadata',
                '.job-result-card__snippet'
            ]
            for selector in description_selectors:
                desc_elem = card.select_one(selector)
                if desc_elem:
                    description = desc_elem.get_text(strip=True)
                    break
            
            job_data['description'] = description
            job_data['posted_date'] = ''  # Posted date requires more complex parsing
            job_data['platform'] = self.get_platform_name().lower()  # Use consistent platform naming
            job_data['source'] = self.get_platform_name()  # Add source field for consistency
            
            return job_data
        except Exception as e:
            if self.debug:
                print(f"Error parsing LinkedIn job card: {e}")
            return None

    def fetch_job_details(self, job_url: str) -> Optional[Dict[str, Any]]:
        """Fetch detailed information for a single job from its URL."""
        try:
            # Import cache service
            try:
                from ..services.job_details_cache import job_details_cache
            except ImportError:
                from services.job_details_cache import job_details_cache

            # Enhanced cache check with better retry mechanism for LinkedIn
            cached_details = None
            max_cache_retries = 3
            cache_retry_delay = 0.5
            
            for cache_attempt in range(max_cache_retries):
                try:
                    cached_details = job_details_cache.get_job_details_with_retry(
                        job_url, 
                        max_retries=2, 
                        retry_delay=cache_retry_delay
                    )
                    if cached_details:
                        print(f"   📋 Using cached job details for: {job_url}")
                        return cached_details
                    break  # Exit retry loop if we got a response (even if None)
                except Exception as cache_error:
                    print(f"   ⚠️ Cache retry {cache_attempt + 1}/{max_cache_retries} failed: {cache_error}")
                    if cache_attempt < max_cache_retries - 1:
                        time.sleep(cache_retry_delay)
            
            # If not in cache, fetch fresh data
            print(f"   🔄 Fetching fresh job details for: {job_url}")
            
            # Enhanced LinkedIn-specific headers and timeout
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.8,de;q=0.5,de-DE;q=0.3',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Cache-Control': 'max-age=0'
            }
            
            # Add LinkedIn session cookie for authenticated requests
            cookies = {}
            if self.li_at_cookie:
                cookies = {'li_at': self.li_at_cookie}
                print(f"   🔐 Using authenticated request for job details")
            else:
                print(f"   ⚠️ Using unauthenticated request for job details")
            
            html_content = None
            error_info = None
            response = None
            
            # Enhanced request with retry mechanism
            max_request_retries = 3
            request_retry_delay = 1.0
            
            for request_attempt in range(max_request_retries):
                try:
                    if self.flaresolverr_client:
                        # For FlareSolverr, we need to pass cookies through the session
                        result = self.get_page_with_flaresolverr(job_url, max_timeout=120000)
                        if result and result.get("status") == "ok":
                            html_content = result.get("solution", {}).get("response", "")
                            break
                        else:
                            error_msg = result.get('message', 'Unknown error') if result else 'No response'
                            print(f"   ⚠️ FlareSolverr attempt {request_attempt + 1}/{max_request_retries} failed: {error_msg}")
                            if request_attempt < max_request_retries - 1:
                                time.sleep(request_retry_delay * (request_attempt + 1))
                                continue
                            else:
                                error_info = f"FlareSolverr failed: {error_msg}"
                                print(f"   ❌ All FlareSolverr attempts failed for: {job_url}")
                    else:
                        # Use authenticated request with cookies
                        response = self.make_rate_limited_request(job_url, headers=headers, cookies=cookies, timeout=45)  # Increased timeout
                        if response and response.status_code == 200:
                            html_content = response.text
                            break
                        elif response and response.status_code in [403, 429, 500, 502, 503, 504]:
                            print(f"   ⚠️ HTTP {response.status_code} for job details (attempt {request_attempt + 1}/{max_request_retries}): {job_url}")
                            if request_attempt < max_request_retries - 1:
                                time.sleep(request_retry_delay * (request_attempt + 1))  # Exponential backoff
                                continue
                        else:
                            status_code = response.status_code if response else 'No response'
                            print(f"   ❌ HTTP {status_code} for job details: {job_url}")
                            break
                except Exception as request_error:
                    print(f"   ⚠️ Request attempt {request_attempt + 1}/{max_request_retries} failed: {request_error}")
                    if request_attempt < max_request_retries - 1:
                        time.sleep(request_retry_delay * (request_attempt + 1))
                        continue
                    else:
                        print(f"   ❌ All request attempts failed for: {job_url}")
            
            # Handle failed requests
            if not html_content:
                error_details = {
                    "title": "Error - HTTP Failed",
                    "company": "Unknown",
                    "location": "Unknown",
                    "salary": "",
                    "description": f"HTTP {response.status_code if response else 'No response'} error",
                    "requirements": "",
                    "benefits": "",
                    "contact_info": "",
                    "application_url": "",
                    "external_url": job_url,
                    "html_content": "",
                    "scraped_date": datetime.now(),
                    "last_accessed": datetime.now()
                }
                
                # Enhanced cache saving with retry mechanism
                max_save_retries = 3
                save_retry_delay = 0.5
                
                for save_attempt in range(max_save_retries):
                    try:
                        job_details_cache.cache_job_details(job_url, error_details, is_valid=False, error_message=f"HTTP {response.status_code if response else 'No response'} error")
                        print(f"   💾 Cached error details for: {job_url}")
                        break
                    except Exception as save_error:
                        print(f"   ⚠️ Cache save attempt {save_attempt + 1}/{max_save_retries} failed: {save_error}")
                        if save_attempt < max_save_retries - 1:
                            time.sleep(save_retry_delay)
                
                return None
            
            # Parse HTML content
            soup = None
            try:
                soup = BeautifulSoup(html_content, 'html.parser')
            except Exception as parse_error:
                print(f"   ⚠️ HTML parsing error for: {job_url} - {parse_error}")
                # Cache partial HTML for debugging
                error_details = {
                    "title": "Error - HTML Parse Failed",
                    "company": "Unknown",
                    "location": "Unknown",
                    "salary": "",
                    "description": f"HTML parsing error: {parse_error}",
                    "requirements": "",
                    "benefits": "",
                    "contact_info": "",
                    "application_url": "",
                    "external_url": job_url,
                    "html_content": html_content[:1000] if html_content else "",  # Store partial content
                    "scraped_date": datetime.now(),
                    "last_accessed": datetime.now()
                }
                
                # Enhanced cache saving with retry mechanism
                max_save_retries = 3
                save_retry_delay = 0.5
                
                for save_attempt in range(max_save_retries):
                    try:
                        job_details_cache.cache_job_details(job_url, error_details, is_valid=False, error_message=f"HTML parsing error: {parse_error}")
                        print(f"   💾 Cached parsing error for: {job_url}")
                        break
                    except Exception as save_error:
                        print(f"   ⚠️ Cache save attempt {save_attempt + 1}/{max_save_retries} failed: {save_error}")
                        if save_attempt < max_save_retries - 1:
                            time.sleep(save_retry_delay)
                
                return None
            
            # Extract job information from the page
            title = ""
            company = ""
            location = ""
            description = ""
            requirements = ""
            benefits = ""
            contact_info = ""
            application_url = ""
            external_url = job_url
            salary = ""
            
            # Enhanced extraction with comprehensive selectors
            # Title extraction
            title_selectors = [
                'h1', 'h2', 'h3',
                'title',
                '[data-testid*="title"]',
                '[data-at*="title"]',
                '[class*="title"]',
                '[class*="job-title"]',
                '[class*="position-title"]'
            ]
            
            for selector in title_selectors:
                try:
                    title_elem = soup.select_one(selector)
                    if title_elem:
                        title = title_elem.get_text(strip=True)
                        if title:
                            break
                except Exception:
                    continue
            
            title = title or "Unknown Title"
            
            # Company extraction
            company_selectors = [
                '[data-testid="company-name"]',
                '.company-name',
                '.employer-name',
                'span[class*="company"]',
                'div[class*="company"]',
                '[class*="employer"]',
                '[class*="organization"]',
                '[data-testid*="company"]',
                '[data-at*="company"]'
            ]
            
            for selector in company_selectors:
                try:
                    company_elem = soup.select_one(selector)
                    if company_elem:
                        company = company_elem.get_text(strip=True)
                        if company:
                            break
                except Exception:
                    continue
            
            company = company or "Unknown Company"
            
            # Location extraction
            location_selectors = [
                '[data-testid="job-location"]',
                '.job-location',
                '.location',
                'span[class*="location"]',
                'div[class*="location"]',
                '[data-testid*="location"]',
                '[data-at*="location"]',
                '[class*="address"]',
                '[class*="place"]'
            ]
            
            for selector in location_selectors:
                try:
                    location_elem = soup.select_one(selector)
                    if location_elem:
                        location = location_elem.get_text(strip=True)
                        if location:
                            break
                except Exception:
                    continue
            
            location = location or "Unknown Location"
            
            # Salary extraction
            salary_selectors = [
                '.salary-snippet',
                '.salary',
                '[data-testid="salary"]',
                '[class*="salary"]',
                '[class*="compensation"]'
            ]
            
            for selector in salary_selectors:
                try:
                    salary_elem = soup.select_one(selector)
                    if salary_elem:
                        salary = salary_elem.get_text(strip=True)
                        if salary:
                            break
                except Exception:
                    continue
            
            # Enhanced description extraction with more comprehensive selectors
            description_selectors = [
                # Modern LinkedIn selectors
                'div[class*="description"]',
                'div[class*="job-details"]',
                'section[class*="description"]',
                'div[data-testid*="description"]',
                'div[class*="jobs-description"]',
                'div[class*="jobs-box__html-content"]',
                'div[class*="jobs-description-content"]',
                'article[class*="jobs-description"]',
                
                # Additional LinkedIn-specific selectors
                '[data-testid="job-description"]',
                '[data-testid="job-details"]',
                'div[class*="job-description"]',
                'div[class*="job-details-content"]',
                'div[class*="job-content"]',
                'div[class*="job-summary"]',
                'div[class*="job-overview"]',
                
                # LinkedIn 2024+ selectors
                'div[class*="jobs-description__content"]',
                'div[class*="jobs-box__html-content"]',
                'div[class*="jobs-description__text"]',
                'div[class*="jobs-description__full-content"]',
                'div[class*="jobs-description__content-wrapper"]',
                'div[class*="jobs-description__content-body"]',
                
                # Legacy selectors
                'div.description__text',
                '.jobs-description__content',
                '.jobs-box__html-content',
                
                # Fallback selectors
                'div[class*="content"]',
                'section[class*="content"]',
                'main'
            ]
            
            for i, selector in enumerate(description_selectors):
                try:
                    desc_elem = soup.select_one(selector)
                    if desc_elem:
                        desc_text = desc_elem.get_text('\n', strip=True)
                        if desc_text and len(desc_text) > 30:  # Reduced from 50 to 30
                            description = desc_text
                            print(f"   ✅ Found description using selector {i+1}: {selector} (length: {len(description)} chars)")
                            break
                except Exception as e:
                    if self.debug:
                        print(f"   ⚠️ Selector {i+1} failed: {selector} - {e}")
                    continue
            
            # Enhanced fallback: try to extract any meaningful text if specific selectors fail
            if not description or len(description.strip()) < 50:
                print(f"   🔍 Using enhanced fallback extraction for: {job_url}")
                
                # Look for any text that might be a job description
                all_text_elements = soup.find_all(['p', 'div', 'section', 'article', 'span'])
                best_candidate = None
                best_score = 0
                
                for element in all_text_elements:
                    text = element.get_text('\n', strip=True)
                    
                    # Skip if text is too short or too long
                    if not text or len(text) < 30 or len(text) > 50000:
                        continue
                    
                    # Skip navigation, footer, header content
                    if any(skip in text.lower() for skip in ['cookie', 'privacy', 'terms', 'navigation', 'footer', 'header', 'menu', 'search', 'linkedin', 'sign in', 'join now']):
                        continue
                    
                    # Score the text based on job-related keywords
                    text_lower = text.lower()
                    score = 0
                    
                    # German job keywords
                    german_keywords = ['erfahrung', 'kenntnisse', 'aufgaben', 'anforderungen', 'qualifikation', 
                                     'ihre', 'sie', 'wir', 'für', 'mit', 'bei', 'bundesland', 'digitalisierung',
                                     'verwaltung', 'bereich', 'haupttätigkeit', 'aufgabenfeld', 'profil',
                                     'persönlichkeit', 'benefits', 'bewerbung', 'mission', 'gesellschaftlich']
                    
                    # English job keywords
                    english_keywords = ['experience', 'skills', 'responsibilities', 'requirements', 'qualifications',
                                      'you will', 'we are', 'for our', 'team', 'company', 'position', 'role',
                                      'opportunity', 'benefits', 'application', 'mission', 'responsibilities']
                    
                    # Calculate score
                    for keyword in german_keywords + english_keywords:
                        if keyword in text_lower:
                            score += 1
                    
                    # Bonus for longer, more detailed descriptions
                    if len(text) > 200:
                        score += 2
                    if len(text) > 500:
                        score += 3
                    
                    # Bonus for German-specific indicators
                    if any(indicator in text_lower for indicator in ['(m/w/d)', '(w/m/d)', '(d/m/w)', 'gmbh', 'ag']):
                        score += 5
                    
                    # Update best candidate
                    if score > best_score:
                        best_score = score
                        best_candidate = text
                
                if best_candidate and best_score >= 3:
                    description = best_candidate
                    print(f"   ✅ Found description with score {best_score} (length: {len(description)} chars)")
                else:
                    print(f"   ⚠️ No suitable description found (best score: {best_score})")
            
            # Content validation for LinkedIn
            if not title or title == "Unknown Title":
                print(f"   ⚠️ Warning: Could not extract title for: {job_url}")
            
            if not company or company == "Unknown Company":
                print(f"   ⚠️ Warning: Could not extract company for: {job_url}")
            
            if not description or len(description.strip()) < 30:
                print(f"   ⚠️ Warning: Description too short for: {job_url} ({len(description)} chars)")
                
                # Try one more aggressive approach - look for any text that contains German job indicators
                if not description or len(description.strip()) < 30:
                    print(f"   🔍 Trying aggressive text extraction for: {job_url}")
                    
                    # Look for any text containing German job indicators
                    all_text = soup.get_text('\n', strip=True)
                    lines = all_text.split('\n')
                    
                    german_job_indicators = [
                        'ihre mission', 'bei it.nrw', 'bundesland', 'digitalisierung', 'verwaltung',
                        'ihr bereich', 'it-fabrik', 'ihre aufgaben', 'ihre haupttätigkeit',
                        'ihr aufgabenfeld umfasst zudem', 'bewegt mehr', 'ihr profil',
                        'sie bringen mit', 'wünschenswert sind zudem', 'ihre persönlichkeit',
                        'wir bieten', 'ihre benefits', 'der richtige schritt', 'ihre bewerbung',
                        '(m/w/d)', '(w/m/d)', '(d/m/w)', 'gmbh', 'ag'
                    ]
                    
                    # Find lines containing German indicators
                    german_lines = []
                    for line in lines:
                        line_lower = line.lower()
                        if any(indicator in line_lower for indicator in german_job_indicators):
                            german_lines.append(line)
                    
                    if german_lines:
                        # Combine lines and clean up
                        potential_description = '\n'.join(german_lines)
                        # Remove duplicates and clean up
                        lines = potential_description.split('\n')
                        unique_lines = []
                        seen = set()
                        for line in lines:
                            line_clean = line.strip()
                            if line_clean and line_clean not in seen and len(line_clean) > 10:
                                unique_lines.append(line_clean)
                                seen.add(line_clean)
                        
                        if unique_lines:
                            description = '\n'.join(unique_lines)
                            print(f"   ✅ Found German content using aggressive extraction (length: {len(description)} chars)")
            
            details = {
                "title": title or "Unknown Title",
                "company": company or "Unknown Company",
                "location": location or "Unknown Location",
                "salary": salary or "",
                "description": description,
                "requirements": "",
                "benefits": "",
                "contact_info": "",
                "application_url": "",
                "external_url": job_url,
                "html_content": html_content,
                "scraped_date": datetime.now(),
                "last_accessed": datetime.now()
            }
            
            # Enhanced cache saving with retry mechanism
            max_save_retries = 3
            save_retry_delay = 0.5
            
            for save_attempt in range(max_save_retries):
                try:
                    job_details_cache.cache_job_details(job_url, details)
                    print(f"   💾 Successfully cached job details for: {job_url}")
                    break
                except Exception as save_error:
                    print(f"   ⚠️ Cache save attempt {save_attempt + 1}/{max_save_retries} failed: {save_error}")
                    if save_attempt < max_save_retries - 1:
                        time.sleep(save_retry_delay)
            
            return details
            
        except Exception as e:
            if self.debug:
                print(f"   ⚠️ Error fetching LinkedIn job details for {job_url}: {e}")
            error_details = {
                "title": "Error - Job Details Fetch",
                "company": "Unknown",
                "location": "Unknown",
                "salary": "",
                "description": f"Failed to fetch job details: {str(e)}",
                "requirements": "",
                "benefits": "",
                "contact_info": "",
                "application_url": "",
                "external_url": job_url,
                "html_content": "",
                "scraped_date": datetime.now(),
                "last_accessed": datetime.now()
            }
            
            # Enhanced cache saving with retry mechanism
            max_save_retries = 3
            save_retry_delay = 0.5
            
            for save_attempt in range(max_save_retries):
                try:
                    job_details_cache.cache_job_details(job_url, error_details, is_valid=False, error_message=f"Error: {str(e)}")
                    print(f"   💾 Cached error details for: {job_url}")
                    break
                except Exception as save_error:
                    print(f"   ⚠️ Cache save attempt {save_attempt + 1}/{max_save_retries} failed: {save_error}")
                    if save_attempt < max_save_retries - 1:
                        time.sleep(save_retry_delay)
            
            return error_details
    
    def _detect_language_sophisticated(self, title: str, description: str) -> str:
        """Sophisticated language detection for job postings."""
        # Focus on the main job description, not just title
        main_content = description if description else title
        if not main_content:
            return "Other"
        
        # Clean and normalize text
        text_to_check = main_content.lower()
        
        # Strong German language indicators (only count if they appear in meaningful context)
        strong_german_indicators = [
            'wir suchen', 'für unser', 'mitarbeiter', 'unternehmen', 'bereich',
            'erfahrung', 'kenntnisse', 'aufgaben', 'anforderungen', 'qualifikation',
            'bewerbung', 'arbeitsplatz', 'stelle', 'gmbh', 'ag', '(m/w/d)', '(w/m/d)',
            'deutsch', 'deutschland', 'entwickler', 'ingenieur', 'berater'
        ]
        
        # Strong English language indicators
        strong_english_indicators = [
            'we are looking', 'for our', 'team', 'experience', 'skills',
            'responsibilities', 'requirements', 'opportunity', 'position',
            'developer', 'engineer', 'consultant', 'company', 'ltd', 'inc',
            'you will', 'you should', 'you must', 'we offer', 'we provide'
        ]
        
        # Count strong indicators
        german_score = sum(1 for indicator in strong_german_indicators if indicator in text_to_check)
        english_score = sum(1 for indicator in strong_english_indicators if indicator in text_to_check)
        
        # Analyze sentence structure and patterns
        german_patterns = [
            r'\bder\b', r'\bdie\b', r'\bdas\b', r'\bund\b', r'\bmit\b', r'\bfür\b',
            r'\bvon\b', r'\bzu\b', r'\bbei\b', r'\bnach\b', r'\büber\b'
        ]
        english_patterns = [
            r'\bthe\b', r'\band\b', r'\bwith\b', r'\bfor\b', r'\bfrom\b',
            r'\bto\b', r'\bat\b', r'\bafter\b', r'\bover\b'
        ]
        
        # Count pattern matches
        import re
        german_pattern_count = sum(len(re.findall(pattern, text_to_check)) for pattern in german_patterns)
        english_pattern_count = sum(len(re.findall(pattern, text_to_check)) for pattern in english_patterns)
        
        # Weighted scoring system
        total_german_score = german_score * 3 + german_pattern_count * 0.5
        total_english_score = english_score * 3 + english_pattern_count * 0.5
        
        # Determine language based on weighted scores
        if total_german_score > total_english_score and total_german_score >= 2:
            return "DE"  # German
        elif total_english_score > total_german_score and total_english_score >= 2:
            return "EN"  # English
        else:
            # If scores are close or low, check for explicit language indicators
            if any(phrase in text_to_check for phrase in ['english', 'international', 'global']):
                return "EN"
            elif any(phrase in text_to_check for phrase in ['german', 'deutsch', 'deutschland']):
                return "DE"
            else:
                # Default to English for international job postings
                return "EN" 