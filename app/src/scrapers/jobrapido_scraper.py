"""
JobRapido Job Scraper

Handles all JobRapido-specific job scraping functionality.
"""

import requests
import time
import random
from datetime import datetime, timedelta
from urllib.parse import urlencode, urljoin
from typing import List, Dict, Optional, Any
from bs4 import BeautifulSoup, Tag
import re
from collections import defaultdict

try:
    from .base_scraper import BaseScraper
except ImportError:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from base_scraper import BaseScraper


class JobrapidoScraper(BaseScraper):
    """JobRapido-specific job scraper with international job aggregation."""
    
    def __init__(self, debug: bool = False, use_flaresolverr: bool = False):
        """
        Initialize Jobrapido scraper.
        
        Args:
            debug: Enable debug logging
            use_flaresolverr: Use FlareSolverr for requests
        """
        super().__init__(debug, use_flaresolverr=use_flaresolverr)
        self.base_url = 'https://de.jobrapido.com'
        self._current_search_location = ""
    
    def get_platform_name(self) -> str:
        """Return the platform name."""
        return "JobRapido"
    
    def search_jobs(self, keywords: str, location: str = "", max_pages: int = 5, 
                   english_only: bool = False, **kwargs) -> List[Dict]:
        """
        Search JobRapido for jobs using web scraping with enhanced Cloudflare bypass.
        
        Args:
            keywords: Job search keywords (can be a single string or comma-separated)
            location: Job location
            max_pages: Maximum number of pages to scrape (increased to 5)
            english_only: Only return English
            **kwargs: Additional arguments
            
        Returns:
            List of job dictionaries
        """
        all_jobs = []
        
        # Split keywords to search one by one
        keyword_list = [k.strip() for k in keywords.split(',') if k.strip()]
        if not keyword_list:
            keyword_list = [keywords]

        try:
            for keyword in keyword_list:
                print(f"\n--- Searching JobRapido for: '{keyword}' (Enhanced Cloudflare Bypass) ---")
                self._current_search_location = location
                
                # JobRapido-specific anti-detection measures
                if self.debug:
                    print("🛡️ Using enhanced cloudscraper session for JobRapido")
                
                for page in range(1, max_pages + 1):
                    params = {'q': keyword, 'p': page}
                    if location:
                        params['l'] = location
                    
                    search_url = f"{self.base_url}/?" + urlencode(params)
                    
                    print(f"📄 Fetching JobRapido page {page} for '{keyword}'")
                    if self.debug:
                        print(f"   🔍 URL: {search_url}")
                    
                    # Enhanced headers specifically for JobRapido
                    headers = {
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.9,de;q=0.8',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'Cache-Control': 'no-cache',
                        'Pragma': 'no-cache',
                        'Sec-Fetch-Dest': 'document',
                        'Sec-Fetch-Mode': 'navigate',
                        'Sec-Fetch-Site': 'none',
                        'Sec-Fetch-User': '?1',
                        'Upgrade-Insecure-Requests': '1',
                        'DNT': '1'
                    }
                    
                    # Use enhanced session with cloudscraper protection
                    response = self.get_page(search_url, headers=headers, timeout=60)
                    
                    page_jobs = []
                    if response and response.status_code == 200:
                        # Check for Cloudflare challenge indicators in response
                        if self._detect_cloudflare_challenge(response.text):
                            if self.debug:
                                print("   🛡️ Cloudflare challenge detected - cloudscraper handling...")
                            # Cloudscraper should handle this automatically, but log it
                        
                        soup = self.get_soup(response.text)
                        if soup:
                            # Check for invalid pages that might indicate failed bypass
                            if self._detect_invalid_search_results(soup, search_url):
                                print(f"   🚫 Invalid search results detected on page {page}")
                                if page == 1:
                                    # If first page is invalid, try refreshing session
                                    if hasattr(self, '_refresh_session'):
                                        print("   🔄 Refreshing session due to invalid results...")
                                        self._refresh_session()
                                        # Retry the request with fresh session
                                        response = self.get_page(search_url, headers=headers, timeout=60)
                                        if response and response.status_code == 200:
                                            soup = self.get_soup(response.text)
                                            if soup and not self._detect_invalid_search_results(soup, search_url):
                                                page_jobs = self._extract_jobrapido_jobs(soup, search_url)
                                break  # Exit this keyword search if still invalid
                            else:
                                page_jobs = self._extract_jobrapido_jobs(soup, search_url)
                        else:
                            print(f"   ⚠️ Failed to parse HTML for page {page}")
                            
                    elif response and response.status_code == 403:
                        print(f"   🚫 HTTP 403 (Cloudflare Protection) for page {page}")
                        if self.debug:
                            print("   🛡️ Cloudflare protection active - session will auto-refresh")
                        # Session refresh is handled in base_scraper.py
                        if page == 1:
                            break  # Exit keyword search if first page blocked
                            
                    elif response and response.status_code == 429:
                        print(f"   ⚠️ HTTP 429 (Rate Limited) for page {page}")
                        if self.debug:
                            print("   🐌 Implementing additional delay...")
                        # Add extra delay for rate limiting
                        time.sleep(random.uniform(10, 20))
                        continue
                        
                    else:
                        status_code = response.status_code if response else 'N/A'
                        print(f"   ❌ HTTP {status_code} for page {page}")
                        if status_code in ['N/A', 500, 502, 503, 504]:
                            # Server errors - wait and retry
                            print(f"   🔄 Retrying in 10s due to server error...")
                            time.sleep(10)
                            continue

                    if page_jobs:
                        all_jobs.extend(page_jobs)
                        print(f"   ✅ Found {len(page_jobs)} jobs on page {page} for '{keyword}'")

                    if page > 1 and not page_jobs:
                        print("   ℹ️ No more jobs found for this keyword")
                        break
                    
                    # Adaptive delay based on response
                    if response and response.status_code == 200:
                        # Normal delay for successful requests
                        delay = random.uniform(3, 8)
                    else:
                        # Longer delay for errors
                        delay = random.uniform(8, 15)
                        
                    if self.debug:
                        print(f"   ⏳ Waiting {delay:.1f}s before next request...")
                    time.sleep(delay)
                
        except Exception as e:
            print(f"❌ Error during JobRapido search: {e}")
            if self.debug:
                import traceback
                print(f"   📋 Stack trace: {traceback.format_exc()}")
        
        # Deduplicate results
        seen_urls = set()
        unique_jobs = []
        for job in all_jobs:
            if (job_url := job.get('url')) and job_url not in seen_urls:
                unique_jobs.append(job)
                seen_urls.add(job_url)

        print(f"\n🎯 Total unique JobRapido jobs found: {len(unique_jobs)}")
        return unique_jobs

    def _detect_invalid_search_results(self, soup: BeautifulSoup, page_url: str) -> bool:
        """Detect if the search results page contains invalid content."""
        try:
            page_text = soup.get_text().lower()
            
            # Check for indicators of invalid pages
            invalid_indicators = [
                'favouritejobs',
                'möchten sie ihre favorisierten',
                'ihre vorteile',
                'hier klicken',
                'favorite jobs',
                'saved jobs',
                'zu viele anfragen',
                'too many requests',
                'rate limit',
                'access denied',
                'blocked',
                'forbidden',
                'cloudflare',
                'captcha',
                'challenge'
            ]
            
            # Check for actual job listings in the HTML structure FIRST
            job_elements = soup.find_all(['div', 'article', 'li'], class_=lambda x: x and any(term in x.lower() for term in ['job', 'position', 'stelle', 'listing']))
            
            # If we found job elements, the page is likely valid regardless of other indicators
            if job_elements and len(job_elements) > 5:
                if self.debug:
                    print(f"   ✅ Found {len(job_elements)} job elements, page appears valid")
                return False
            
            # Check if the page has job-related elements in text
            job_indicators = ['job', 'position', 'stelle', 'arbeit', 'career', 'employment', 'entwickler', 'developer', 'engineer']
            job_related_count = sum(1 for indicator in job_indicators if indicator in page_text)
            
            # Only consider invalid if we have invalid indicators AND very few job-related terms
            if any(indicator in page_text for indicator in invalid_indicators) and job_related_count < 3:
                if self.debug:
                    print(f"   🚫 Detected invalid search results page: {page_url}")
                return True
            
            # More lenient check - only consider invalid if very few job-related terms AND page is very short
            if job_related_count < 1 and len(page_text) < 500:
                if self.debug:
                    print(f"   ⚠️ Page has very few job-related terms and is short, might be invalid")
                return True
            
            return False
            
        except Exception as e:
            if self.debug:
                print(f"   ⚠️ Error detecting invalid search results: {e}")
            return False

    def _extract_jobrapido_jobs(self, soup: BeautifulSoup, page_url: str) -> List[Dict]:
        """Extract job listings from JobRapido search results."""
        jobs = []
        
        try:
            # First, check if this is a valid search results page
            if self._detect_invalid_search_results(soup, page_url):
                print(f"   🚫 Invalid search results detected, skipping page")
                return []
            
            # Enhanced JobRapido job cards selectors
            job_cards = []
            
            # Try specific JobRapido selectors first
            patterns = [
                {'tag': ['div'], 'class': lambda x: x and any(term in x.lower() for term in ['job', 'result', 'listing', 'offer'])},
                {'tag': ['article'], 'class': lambda x: x and 'job' in x.lower()},
                {'tag': ['li'], 'class': lambda x: x and any(term in x.lower() for term in ['job', 'result'])},
                {'tag': ['section'], 'class': lambda x: x and 'job' in x.lower()},
            ]
            
            for pattern in patterns:
                cards = soup.find_all(pattern['tag'], class_=pattern['class'])
                if cards:
                    # Filter out invalid cards (navigation, buttons, etc.)
                    valid_cards = []
                    for card in cards:
                        card_text = card.get_text(strip=True)
                        # Skip if it's just navigation text or too short
                        if (len(card_text) > 50 and  # Must have substantial content
                            not any(nav_text in card_text.lower() for nav_text in 
                                   ['next page', 'previous', 'filter', 'sort', 'sponsored']) and
                            any(job_indicator in card_text.lower() for job_indicator in 
                               ['job', 'position', 'role', 'developer', 'engineer', 'manager'])):
                            valid_cards.append(card)
                    
                    if valid_cards:
                        job_cards = valid_cards
                        if self.debug:
                            print(f"   🎯 Found {len(valid_cards)} valid job cards using pattern: {pattern}")
                        break
            
            # Fallback: look for any elements with job-related attributes or text
            if not job_cards and self.debug:
                print("   ⚠️ No job cards found with any pattern")
            
            for card in job_cards:
                try:
                    if isinstance(card, Tag):
                        job_data = self._parse_jobrapido_job_card(card, page_url)
                        if job_data and self._is_valid_job_listing(job_data):
                            jobs.append(job_data)
                except Exception as e:
                    if self.debug:
                        print(f"   ⚠️ Error parsing JobRapido job card: {e}")
                    continue
                    
        except Exception as e:
            print(f"❌ Error extracting JobRapido jobs: {e}")
        
        return jobs

    def _parse_jobrapido_job_card(self, card: Tag, page_url: str) -> Dict:
        """Parse individual JobRapido job card."""
        job_data = {}
        title = ""
        company = ""
        location = ""
        job_url = ""
        description = ""

        title_element = card.find(['h2', 'h3'])
        if title_element:
            title = title_element.get_text(strip=True)

        link_element = card.find('a', href=True)
        if link_element and isinstance(link_element.get('href'), str):
            href = link_element.get('href')
            if href and href.startswith('http'):
                job_url = href
            elif href:
                job_url = urljoin(self.base_url, href)

        company_element = card.find('p', class_='job-company')
        if company_element:
            company = company_element.get_text(strip=True)

        location_element = card.find('p', class_='job-location')
        if location_element:
            location = location_element.get_text(strip=True)

        description_element = card.find('p', class_='job-description')
        if description_element:
            description = description_element.get_text(strip=True)
            
        job_data = {
            'title': title,
            'company': company,
            'location': location,
            'url': job_url,
            'description': description,
            'posted_date': ''
        }

        return job_data

    def _is_valid_job_listing(self, job: Dict) -> bool:
        """Validate if a scraped item is a valid job listing."""
        # Basic validation: must have a title and URL
        if not job.get('title') or not job.get('url'):
            return False
        
        # Check for minimum content
        title = job.get('title', '').lower()
        description = job.get('description', '').lower()
        
        # Must contain job-related keywords
        job_keywords = ['entwickler', 'developer', 'engineer', 'programmierer', 'it', 'software', 'job', 'stelle', 'position', 'mitarbeiter', 'vollzeit', 'teilzeit']
        if not any(keyword in title or keyword in description for keyword in job_keywords):
            return False
        
        # Must not be navigation or non-job content
        nav_keywords = ['seite', 'weiter', 'zurück', 'navigation', 'filter', 'sortieren', 'impressum', 'datenschutz', 'agb']
        if any(keyword in title or keyword in description for keyword in nav_keywords):
            return False
        
        # Must have reasonable title length
        if len(title) < 5 or len(title) > 200:
            return False
        
        return True

    def fetch_job_details(self, job_url: str) -> Optional[Dict[str, Any]]:
        """Fetch detailed information for a single job from its URL."""
        try:
            # Import cache service
            try:
                from ..services.job_details_cache import job_details_cache
            except ImportError:
                from services.job_details_cache import job_details_cache
            
            # Check cache first with retry mechanism
            cached_details = job_details_cache.get_job_details_with_retry(job_url, max_retries=2, retry_delay=0.5)
            if cached_details:
                print(f"   📋 Using cached job details for: {job_url}")
                return cached_details
            
            # If not in cache, fetch fresh data
            print(f"   🔄 Fetching fresh job details for: {job_url}")
            
            # Skip fetching if URL contains template variables
            if '[[' in job_url and ']]' in job_url:
                if self.debug:
                    print(f"   ⚠️ Skipping URL with template variables: {job_url}")
                error_details = {
                    "title": "Error - Template Variables",
                    "company": "Unknown",
                    "location": "Unknown",
                    "salary": "",
                    "description": "URL contains template variables",
                    "requirements": "",
                    "benefits": "",
                    "contact_info": "",
                    "application_url": "",
                    "external_url": job_url,
                    "html_content": "",
                    "scraped_date": datetime.now(),
                    "last_accessed": datetime.now()
                }
                job_details_cache.cache_job_details(job_url, error_details, is_valid=False, error_message="URL contains template variables")
                return None
            
            # Validate URL format and domain
            if not job_url or not job_url.startswith('http'):
                if self.debug:
                    print(f"   ⚠️ Skipping invalid URL format: {job_url}")
                error_details = {
                    "title": "Error - Invalid URL Format",
                    "company": "Unknown",
                    "location": "Unknown",
                    "salary": "",
                    "description": "Invalid URL format",
                    "requirements": "",
                    "benefits": "",
                    "contact_info": "",
                    "application_url": "",
                    "external_url": job_url,
                    "html_content": "",
                    "scraped_date": datetime.now(),
                    "last_accessed": datetime.now()
                }
                job_details_cache.cache_job_details(job_url, error_details, is_valid=False, error_message="Invalid URL format")
                return None
            
            # Check for known invalid domains
            invalid_domains = [
                'xing-premium.com', 'premium.xing.com', 'invalid-domain.com',
                'example.com', 'test.com', 'placeholder.com'
            ]
            if any(invalid_domain in job_url.lower() for invalid_domain in invalid_domains):
                if self.debug:
                    print(f"   ⚠️ Skipping URL with invalid domain: {job_url}")
                error_details = {
                    "title": "Error - Invalid Domain",
                    "company": "Unknown",
                    "location": "Unknown",
                    "salary": "",
                    "description": "Invalid domain",
                    "requirements": "",
                    "benefits": "",
                    "contact_info": "",
                    "application_url": "",
                    "external_url": job_url,
                    "html_content": "",
                    "scraped_date": datetime.now(),
                    "last_accessed": datetime.now()
                }
                job_details_cache.cache_job_details(job_url, error_details, is_valid=False, error_message="Invalid domain")
                return None
            
            # Step 1: Get the JobRapido job page to find the "Angebot anzeigen" button
            if self.debug:
                print(f"   📄 Fetching JobRapido page: {job_url}")
            
            html_content = None
            response = self.get_page(job_url, timeout=30)
            if response and response.status_code == 200:
                html_content = response.text
                print(f"   ✅ JobRapido page fetched successfully")
            else:
                print(f"   ❌ Failed to fetch JobRapido page: HTTP {response.status_code if response else 'No response'}")
                return None
            
            soup = self.get_soup(html_content)
            
            # Step 2: Find the "Angebot anzeigen" button to get the external job URL
            external_url = None
            # Try multiple selectors for the apply/view button
            apply_button_selectors = [
                lambda: soup.find_all('a', string=lambda text: text and any(term in text.lower() for term in ['angebot anzeigen', 'apply', 'bewerben', 'zur stelle', 'view job', 'job ansehen'])),
                lambda: soup.find_all('a', text=lambda text: text and any(term in text.lower() for term in ['angebot anzeigen', 'apply', 'bewerben', 'zur stelle', 'view job', 'job ansehen'])),
                lambda: soup.find_all('a', class_=lambda x: x and any(term in ' '.join(x).lower() for term in ['apply', 'btn-apply', 'job-apply', 'external', 'redirect'])),
                lambda: soup.find_all('a', attrs={'data-testid': lambda x: x and 'apply' in x.lower()}),
            ]
            for selector_func in apply_button_selectors:
                try:
                    buttons = selector_func()
                    for button in buttons:
                        href = button.get('href', '')
                        if href and href.startswith('http') and 'jobrapido.com' not in href:
                            external_url = href
                            if self.debug:
                                print(f"   🔗 Found external URL: {external_url}")
                            break
                    if external_url:
                        break
                except Exception as e:
                    if self.debug:
                        print(f"   ⚠️ Error with selector: {e}")
                    continue
            
            # If no external URL found, return basic info from JobRapido page
            if not external_url:
                if self.debug:
                    print(f"   ⚠️ No external URL found, using JobRapido page content")
                description = ""
                description_selectors = [
                    'div.job-description',
                    'div[class*="description"]',
                    'section[class*="description"]',
                    '.job-content',
                    '.job-details'
                ]
                for selector in description_selectors:
                    description_container = soup.select_one(selector)
                    if description_container:
                        description = description_container.get_text('\n').strip()
                        break
                # Build comprehensive details
                details = {
                    "title": "Unknown Job",
                    "company": "Unknown Company",
                    "location": "Unknown Location",
                    "salary": "",
                    "description": description or "No description available",
                    "requirements": "",
                    "benefits": "",
                    "contact_info": "",
                    "application_url": "",
                    "external_url": job_url,
                    "html_content": html_content,
                    "scraped_date": datetime.now(),
                    "last_accessed": datetime.now()
                }
                job_details_cache.cache_job_details(job_url, details)
                return details
            
            # Step 3: Fetch the actual external job posting
            if self.debug:
                print(f"   🌐 Fetching external job posting: {external_url}")
            try:
                external_html = None
                response = self.get_page(external_url, timeout=30)
                if response and response.status_code == 200:
                    external_html = response.text
                    print(f"   ✅ External job posting fetched successfully")
                else:
                    print(f"   ❌ Failed to fetch external job posting: HTTP {response.status_code if response else 'No response'}")
                    return None
                external_soup = self.get_soup(external_html)
                # Extract comprehensive job details from the external site
                result = {
                    "external_url": external_url or job_url,
                    "title": "",
                    "company": "",
                    "location": "",
                    "salary": "",
                    "description": "",
                    "requirements": "",
                    "benefits": "",
                    "contact_info": "",
                    "application_url": "",
                    "html_content": external_html,
                    "scraped_date": datetime.now(),
                    "last_accessed": datetime.now()
                }
                # Extract job title
                title_selectors = [
                    'h1',
                    'h2.job-title',
                    '.job-title',
                    '[class*="title"]',
                    '.position-title'
                ]
                for selector in title_selectors:
                    title_elem = external_soup.select_one(selector)
                    if title_elem and title_elem.get_text(strip=True):
                        result['title'] = title_elem.get_text(strip=True)
                        break
                # Extract company name
                company_selectors = [
                    '.company-name',
                    '[class*="company"]',
                    '.employer',
                    '[data-testid*="company"]'
                ]
                for selector in company_selectors:
                    company_elem = external_soup.select_one(selector)
                    if company_elem and company_elem.get_text(strip=True):
                        result['company'] = company_elem.get_text(strip=True)
                        break
                # Extract location
                location_selectors = [
                    '.location',
                    '[class*="location"]',
                    '.job-location',
                    '[data-testid*="location"]'
                ]
                for selector in location_selectors:
                    location_elem = external_soup.select_one(selector)
                    if location_elem and location_elem.get_text(strip=True):
                        result['location'] = location_elem.get_text(strip=True)
                        break
                # Extract salary
                salary_selectors = [
                    '.salary',
                    '[class*="salary"]',
                    '.compensation',
                    '[data-testid*="salary"]'
                ]
                for selector in salary_selectors:
                    salary_elem = external_soup.select_one(selector)
                    if salary_elem and salary_elem.get_text(strip=True):
                        result['salary'] = salary_elem.get_text(strip=True)
                        break
                # Extract description
                desc_selectors = [
                    '.job-description',
                    '[class*="description"]',
                    '.job-details',
                    '.position-description'
                ]
                for selector in desc_selectors:
                    desc_elem = external_soup.select_one(selector)
                    if desc_elem:
                        desc_text = desc_elem.get_text('\n').strip()
                        if len(desc_text) > 100:
                            result['description'] = desc_text
                            break
                # Extract requirements if available
                requirements_keywords = ['requirements', 'qualifications', 'skills', 'anforderungen', 'voraussetzungen']
                for keyword in requirements_keywords:
                    req_elem = external_soup.find(['div', 'section', 'ul'], class_=lambda x: x and keyword in ' '.join(x).lower())
                    if req_elem:
                        result['requirements'] = req_elem.get_text('\n', strip=True)
                        break
                if self.debug:
                    print(f"   ✅ Extracted {len(result)} fields from external job posting")
                    print(f"   Fields: {list(result.keys())}")
                job_details_cache.cache_job_details(job_url, result)
                return result
            except Exception as e:
                if self.debug:
                    print(f"   ⚠️ Error fetching external job posting {external_url}: {e}")
                error_details = {
                    "title": "Error - External Fetch",
                    "company": "Unknown",
                    "location": "Unknown",
                    "salary": "",
                    "description": f"Failed to fetch external job posting: {str(e)}",
                    "requirements": "",
                    "benefits": "",
                    "contact_info": "",
                    "application_url": "",
                    "external_url": external_url or job_url,
                    "html_content": "",
                    "scraped_date": datetime.now(),
                    "last_accessed": datetime.now()
                }
                job_details_cache.cache_job_details(job_url, error_details, is_valid=False, error_message="Failed to fetch external URL")
                return None
        except Exception as e:
            if self.debug:
                print(f"   ⚠️ Error fetching JobRapido job details for {job_url}: {e}")
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
            job_details_cache.cache_job_details(job_url, error_details, is_valid=False, error_message=f"Error: {str(e)}")
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

    def _detect_cloudflare_challenge(self, html_content: str) -> bool:
        """Detect if the response contains Cloudflare challenge indicators."""
        if not html_content:
            return False
            
        challenge_indicators = [
            'Checking your browser before accessing',
            'DDoS protection by Cloudflare',
            'cf-browser-verification',
            'cf-challenge-error',
            'cf_captcha_kind',
            'turnstile',
            'cf-turnstile',
            '__cf_chl_jschl_tk__',
            'cF-rchal',
            'cf-challenge'
        ]
        
        html_lower = html_content.lower()
        return any(indicator.lower() in html_lower for indicator in challenge_indicators) 