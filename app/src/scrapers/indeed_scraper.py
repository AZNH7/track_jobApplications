"""
Indeed Job Scraper

Handles all Indeed-specific job scraping functionality.
"""

import requests
import time
import random
from datetime import datetime
from urllib.parse import urlencode, urljoin, quote_plus
from typing import List, Dict, Optional, Union, Any
from bs4 import BeautifulSoup, Tag
import re

try:
    import streamlit as st
except ImportError:
    st = None

try:
    from .base_scraper import BaseScraper
except ImportError:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from base_scraper import BaseScraper


class IndeedScraper(BaseScraper):
    """Indeed-specific job scraper."""
    
    def __init__(self, debug: bool = False, country: str = 'de', use_flaresolverr: bool = False):
        """
        Initialize Indeed scraper.
        
        Args:
            debug: Enable debug logging
            country: Indeed country code (only 'de' supported)
            use_flaresolverr: Whether to use FlareSolverr for bypassing Cloudflare
        """
        super().__init__(debug, use_flaresolverr=use_flaresolverr)
        
        # Only Germany is supported
        if country != 'de':
            print(f"⚠️ Warning: Only Germany (de) is supported. Defaulting to Indeed Germany.")
            country = 'de'
        
        self.country = country
        self.base_url = 'https://de.indeed.com'
    
    def get_platform_name(self) -> str:
        """Return the platform name."""
        return "Indeed"

    def _clean_search_term(self, term: str) -> str:
        """Clean and prepare search term."""
        return re.sub(r'\s+', ' ', term).strip()

    def _clean_location_term(self, term: str) -> str:
        """Clean and prepare location term."""
        return term.strip()

    def search_jobs(self, keywords: str, location: str = "", max_pages: int = 3, 
                   english_only: bool = False, **kwargs) -> List[Dict]:
        """
        Search Indeed for jobs using FlareSolverr only.
        
        Args:
            keywords: Job search keywords (can be a single string or comma-separated)
            location: Job location
            max_pages: Maximum number of pages to scrape
            english_only: Only return English language jobs
            **kwargs: Additional arguments
            
        Returns:
            List of job dictionaries
        """
        all_jobs = []
        
        print(f"🔍 Searching Indeed jobs (enhanced): {keywords} in {location}")

        # Split keywords to search one by one
        keyword_list = [k.strip() for k in keywords.split(',') if k.strip()]
        if not keyword_list:
            keyword_list = [keywords]

        for keyword in keyword_list:
            print(f"\n--- Searching Indeed for: '{keyword}' ---")
            
            try:
                print(f"🌐 Using configured session for '{keyword}'...")
                flare_jobs = self._search_indeed_with_session(keyword, location, max_pages, english_only)
                if flare_jobs:
                    all_jobs.extend(flare_jobs)
                    print(f"✅ Found {len(flare_jobs)} jobs for '{keyword}'")
            except Exception as e:
                print(f"❌ Search method failed for '{keyword}': {e}")

        # Deduplicate results
        seen_urls = set()
        unique_jobs = []
        for job in all_jobs:
            if (job_url := job.get('url')) and job_url not in seen_urls:
                unique_jobs.append(job)
                seen_urls.add(job_url)

        print(f"\n🎯 Total unique Indeed jobs found: {len(unique_jobs)}")
        return unique_jobs

    def _search_indeed_with_session(self, keywords: str, location: str = "", max_pages: int = 3, english_only: bool = False) -> List[Dict]:
        """Search Indeed using the configured session from BaseScraper."""
        jobs = []
        
        clean_keywords = self._clean_search_term(keywords)
        clean_location = self._clean_location_term(location)
        
        # Handle remote jobs specially for Indeed
        if clean_location.lower() == "remote":
            # For remote jobs, use Germany as location but add remote filter
            search_location = "germany"
            remote_filter = True
        else:
            search_location = clean_location
            remote_filter = False
        
        print(f"🌐 Enhanced search: '{clean_keywords}' in '{search_location}'")
        
        for page in range(max_pages):
            start = page * 10
            
            params = {
                'q': clean_keywords,
                'l': search_location,
                'start': start,
                'sort': 'date',
                'fromage': '7',
                'radius': '35'
            }
            
            # Add remote work filter for remote searches
            if remote_filter:
                params['sc'] = '0kf%3Aattr%28DSQF7%29%3B'  # Remote work filter
            
            if english_only:
                params['lang'] = 'en'

            url = f"{self.base_url}/jobs?{urlencode(params)}"
            print(f"   📄 Page {page + 1}/{max_pages}")
            print(f"   [DEBUG] URL: {url}")
            
            # Use cloudscraper timeout configuration instead of max_timeout
            timeout = 300 if page == 0 else 240  # Convert from milliseconds to seconds
            
            response = self.get_page(url, timeout=timeout)
            
            if response and response.status_code == 200:
                html_content = response.text
                soup = self.get_soup(html_content)
                if soup:
                    page_jobs = self._extract_indeed_jobs_from_html(soup, url)
                    jobs.extend(page_jobs)
                else:
                    print("   ❌ Failed to parse HTML content.")
            else:
                status = response.status_code if response else 'N/A'
                print(f"   ❌ Failed to fetch page {page + 1}, status code: {status}")
                # Potentially add logic for different status codes
                if status == 429: # Too Many Requests
                    print("   🕒 Rate limited. Waiting before next attempt.")
                    time.sleep(60)
                elif response is not None:
                    try:
                        # Safely check for captcha without printing binary data
                        response_text = response.text if hasattr(response, 'text') else str(response.content, 'utf-8', errors='ignore')
                        if "captcha" in response_text.lower():
                            print(f"   🧩 Manual CAPTCHA required - Indeed blocking automated access")
                            break
                    except Exception as e:
                        if self.debug:
                            print(f"   ⚠️ Could not check response for CAPTCHA: {e}")
                else:
                    break
                    
        return jobs

    def _extract_indeed_jobs_from_html(self, soup: BeautifulSoup, page_url: str) -> List[Dict]:
        """Extract jobs from Indeed HTML with enhanced selectors."""
        jobs = []
        
        try:
            # Enhanced Indeed job selectors - try multiple patterns
            job_selectors = [
                # Modern Indeed selectors
                'div[data-jk]',  # Job cards with data-jk attribute
                '.job_seen_beacon',  # Job cards with seen beacon
                '.jobsearch-SerpJobCard',  # Classic job card
                '.result',  # Generic result
                '[data-testid="job-card"]',  # Test ID based
                '.slider_container .slider_item',  # Slider items
                # Fallback selectors
                'table[cellpadding="0"][cellspacing="0"][border="0"]',  # Table-based layout
                'div[style*="padding"]',  # Divs with padding (job cards)
            ]
            
            job_cards = []
            for selector in job_selectors:
                cards = soup.select(selector)
                if cards:
                    job_cards = cards
                    print(f"   🎯 Found {len(cards)} job cards using selector: {selector}")
                    break
            
            if not job_cards:
                # Emergency fallback: look for any container with job-like content
                all_divs = soup.find_all('div')
                job_cards = [div for div in all_divs if div.get_text() and any(keyword in div.get_text().lower() for keyword in ['developer', 'engineer', 'administrator', 'manager'])]
                print(f"   ⚠️ Using emergency fallback, found {len(job_cards)} potential job elements")
            
            for card in job_cards:
                try:
                    job_data = self._parse_indeed_job_card(card, page_url)
                    if job_data and job_data.get('title'):
                        jobs.append(job_data)
                except Exception as e:
                    continue
                    
        except Exception as e:
            print(f"❌ Error extracting Indeed jobs: {e}")
        
        return jobs

    def _parse_indeed_job_card(self, card, page_url: str) -> Dict:
        """Parse individual Indeed job card with enhanced extraction."""
        try:
            # Extract job title
            title = ""
            title_selectors = [
                'h2 a[data-jk]',  # Modern Indeed title
                'h2 a',  # Generic h2 link
                '.jobTitle a',  # Classic job title
                'a[data-jk]',  # Any link with job key
                'h2',  # Any h2
                '.title'  # Title class
            ]
            
            for selector in title_selectors:
                element = card.select_one(selector)
                if element:
                    title = element.get_text(strip=True)
                    break
            
            # Extract company
            company = ""
            company_selectors = [
                '.companyName a',  # Company link
                '.companyName',  # Company name
                '[data-testid="company-name"]',  # Test ID
                'span[title]'  # Span with title attribute
            ]
            
            for selector in company_selectors:
                element = card.select_one(selector)
                if element:
                    company = element.get_text(strip=True)
                    break
            
            # Extract location
            location = ""
            location_selectors = [
                '[data-testid="job-location"]',  # Test ID location
                '.companyLocation',  # Company location
                '.locationsContainer',  # Locations container
                'div[title]'  # Div with title (often location)
            ]
            
            for selector in location_selectors:
                element = card.select_one(selector)
                if element:
                    location = element.get_text(strip=True)
                    break
            
            # Extract job URL
            job_url = ""
            url_element = card.select_one('h2 a[href], a[data-jk][href], a[href]')
            if url_element:
                href = url_element.get('href', '')
                if href.startswith('http'):
                    job_url = href
                elif href.startswith('/'):
                    job_url = urljoin(self.base_url, href)
            
            # Extract salary if available
            salary = ""
            salary_element = card.select_one('.metadata .salary-snippet, .salaryText')
            if salary_element:
                salary = salary_element.get_text(strip=True)
            
            # Enhanced description extraction from job card
            description = self._extract_description_from_card(card)

            return {
                'title': title,
                'company': company,
                'location': location,
                'salary': salary,
                'url': job_url,
                'source': 'Indeed',
                'description': description,
                'scraped_date': datetime.now(),
                'posted_date': "",
                'language': self._detect_language_sophisticated(title, description)
            }
            
        except Exception as e:
            return {} 

    def fetch_job_details(self, job_url: str) -> Optional[Dict[str, Any]]:
        """Fetch detailed information for a single job from its URL."""
        try:
            # Import cache service
            try:
                from ..services.job_details_cache import job_details_cache
            except ImportError:
                from services.job_details_cache import job_details_cache

            # Enhanced cache check with better retry mechanism for Indeed
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
                        print(f"   ✅ Found cached job details for: {job_url}")
                        return cached_details
                    break  # Exit retry loop if we got a response (even if None)
                except Exception as cache_error:
                    print(f"   ⚠️ Cache retry {cache_attempt + 1}/{max_cache_retries} failed: {cache_error}")
                    if cache_attempt < max_cache_retries - 1:
                        time.sleep(cache_retry_delay)
            
            # If not in cache, fetch fresh data
            print(f"   🔄 Fetching fresh job details for: {job_url}")
            
            # Enhanced Indeed-specific headers and timeout
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Cache-Control': 'max-age=0'
            }
            
            html_content = None
            error_info = None
            response = None
            
            # Enhanced request with retry mechanism
            max_request_retries = 3
            request_retry_delay = 1.0
            
            for request_attempt in range(max_request_retries):
                try:
                    response = self.get_page(job_url, headers=headers, timeout=45)  # Increased timeout for Indeed
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
            if not response or response.status_code != 200:
                status_code = response.status_code if response else 'No response'
                error_info = f"HTTP {status_code} error after {max_request_retries} attempts"
                print(f"   ❌ Failed to fetch Indeed job details: {job_url} (Status: {status_code})")
                
                # Cache error details
                error_details = {
                    "title": f"Error - HTTP {status_code}",
                    "company": "Unknown",
                    "location": "Unknown",
                    "salary": "",
                    "description": f"HTTP {status_code} error after {max_request_retries} attempts",
                    "requirements": "",
                    "benefits": "",
                    "contact_info": "",
                    "application_url": "",
                    "external_url": job_url,
                    "html_content": "",
                    "scraped_date": datetime.now(),
                    "last_accessed": datetime.now()
                }
                
                # Enhanced caching with retry mechanism for error details
                cache_success = False
                max_cache_save_retries = 3
                cache_save_retry_delay = 0.5
                
                for cache_save_attempt in range(max_cache_save_retries):
                    try:
                        cache_success = job_details_cache.cache_job_details(job_url, error_details, is_valid=False, error_message=f"HTTP {status_code} error")
                        if cache_success:
                            print(f"   ✅ Successfully cached Indeed error details for: {job_url}")
                            break
                        else:
                            print(f"   ⚠️ Cache save attempt {cache_save_attempt + 1}/{max_cache_save_retries} failed for: {job_url}")
                            if cache_save_attempt < max_cache_save_retries - 1:
                                time.sleep(cache_save_retry_delay)
                    except Exception as cache_save_error:
                        print(f"   ⚠️ Cache save error (attempt {cache_save_attempt + 1}/{max_cache_save_retries}): {cache_save_error}")
                        if cache_save_attempt < max_cache_save_retries - 1:
                            time.sleep(cache_save_retry_delay)
                
                return None

            # Enhanced HTML parsing with error handling
            if not html_content:
                error_info = "No HTML content received after successful HTTP response"
                print(f"   ❌ No HTML content received for: {job_url}")
                
                error_details = {
                    "title": "Error - No Content",
                    "company": "Unknown",
                    "location": "Unknown",
                    "salary": "",
                    "description": "No HTML content received after successful HTTP response",
                    "requirements": "",
                    "benefits": "",
                    "contact_info": "",
                    "application_url": "",
                    "external_url": job_url,
                    "html_content": "",
                    "scraped_date": datetime.now(),
                    "last_accessed": datetime.now()
                }
                
                try:
                    job_details_cache.cache_job_details(job_url, error_details, is_valid=False, error_message="No HTML content received")
                except Exception as cache_error:
                    print(f"   ⚠️ Failed to cache error details: {cache_error}")
                
                return None
            
            # Parse and extract details with enhanced error handling
            job_details = {}
            
            try:
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Extract job title with enhanced error handling
                title_elem = soup.find('h1') or soup.find('title')
                if title_elem:
                    job_details['title'] = title_elem.get_text(strip=True)
                else:
                    job_details['title'] = "Unknown Title"
                
                # Extract company name with enhanced selectors
                company_selectors = [
                    '[data-testid="company-name"]',
                    '.company-name',
                    '.employer-name',
                    'span[class*="company"]',
                    'div[class*="company"]',
                    '[data-testid*="company"]',
                    '[data-at*="company"]'
                ]
                company_found = False
                for selector in company_selectors:
                    company_elem = soup.select_one(selector)
                    if company_elem:
                        job_details['company'] = company_elem.get_text(strip=True)
                        company_found = True
                        break
                
                if not company_found:
                    job_details['company'] = "Unknown Company"
                
                # Extract location with enhanced selectors
                location_selectors = [
                    '[data-testid="job-location"]',
                    '.job-location',
                    '.location',
                    'span[class*="location"]',
                    'div[class*="location"]',
                    '[data-testid*="location"]',
                    '[data-at*="location"]'
                ]
                location_found = False
                for selector in location_selectors:
                    location_elem = soup.select_one(selector)
                    if location_elem:
                        job_details['location'] = location_elem.get_text(strip=True)
                        location_found = True
                        break
                
                if not location_found:
                    job_details['location'] = "Unknown Location"
                
                # Enhanced job description extraction
                description = self._extract_comprehensive_description(soup)
                job_details['description'] = description
                
                # Extract salary if available
                salary_selectors = [
                    '.salary-snippet',
                    '.salary',
                    '[data-testid="salary"]',
                    'span[class*="salary"]',
                    'div[class*="salary"]'
                ]
                for selector in salary_selectors:
                    salary_elem = soup.select_one(selector)
                    if salary_elem:
                        job_details['salary'] = salary_elem.get_text(strip=True)
                        break
                
                # Add metadata
                job_details['source'] = 'Indeed'
                job_details['scraped_date'] = datetime.now()
                job_details['url'] = job_url
                job_details['external_url'] = job_url
                job_details['html_content'] = html_content
                job_details['last_accessed'] = datetime.now()
                
                print(f"   ✅ Successfully extracted job details from Indeed")
                
            except Exception as e:
                error_info = f"Parsing error: {str(e)}"
                print(f"   ❌ Error parsing Indeed job details: {e}")
                
                # Create error details with partial content
                job_details = {
                    "title": "Error - Parsing Failed",
                    "company": "Unknown",
                    "location": "Unknown",
                    "salary": "",
                    "description": f"Failed to parse Indeed job details: {str(e)}",
                    "requirements": "",
                    "benefits": "",
                    "contact_info": "",
                    "application_url": "",
                    "external_url": job_url,
                    "html_content": html_content[:1000] if html_content else "",  # Store partial content for debugging
                    "scraped_date": datetime.now(),
                    "last_accessed": datetime.now()
                }
            
            # Enhanced caching with retry mechanism
            cache_success = False
            max_cache_save_retries = 3
            cache_save_retry_delay = 0.5
            
            for cache_save_attempt in range(max_cache_save_retries):
                try:
                    if job_details and job_details.get('title') != "Error - Parsing Failed":
                        # Cache successful result
                        cache_success = job_details_cache.cache_job_details(job_url, job_details)
                        if cache_success:
                            print(f"   ✅ Successfully cached Indeed job details for: {job_url}")
                            break
                        else:
                            print(f"   ⚠️ Cache save attempt {cache_save_attempt + 1}/{max_cache_save_retries} failed for: {job_url}")
                            if cache_save_attempt < max_cache_save_retries - 1:
                                time.sleep(cache_save_retry_delay)
                    else:
                        # Cache error information
                        error_details = {
                            'error': True,
                            'error_message': error_info or 'Unknown error',
                            'source': 'Indeed',
                            'scraped_date': datetime.now(),
                            'url': job_url,
                            'external_url': job_url,
                            'html_content': html_content[:1000] if html_content else ""
                        }
                        cache_success = job_details_cache.cache_job_details(job_url, error_details, is_valid=False, error_message=error_info or 'Unknown error')
                        if cache_success:
                            print(f"   ✅ Successfully cached Indeed error details for: {job_url}")
                            break
                        else:
                            print(f"   ⚠️ Cache save attempt {cache_save_attempt + 1}/{max_cache_save_retries} failed for: {job_url}")
                            if cache_save_attempt < max_cache_save_retries - 1:
                                time.sleep(cache_save_retry_delay)
                except Exception as cache_save_error:
                    print(f"   ⚠️ Cache save error (attempt {cache_save_attempt + 1}/{max_cache_save_retries}): {cache_save_error}")
                    if cache_save_attempt < max_cache_save_retries - 1:
                        time.sleep(cache_save_retry_delay)
            
            if not cache_success:
                print(f"   ⚠️ Failed to cache job details after {max_cache_save_retries} attempts for: {job_url}")
            
            return job_details if job_details and job_details.get('title') != "Error - Parsing Failed" else None

        except Exception as e:
            print(f"   ⚠️ Unexpected error in fetch_job_details for {job_url}: {e}")
            
            # Try to cache the error details
            try:
                error_details = {
                    "title": "Error - Unexpected Error",
                    "company": "Unknown",
                    "location": "Unknown",
                    "salary": "",
                    "description": f"Unexpected error in fetch_job_details: {str(e)}",
                    "requirements": "",
                    "benefits": "",
                    "contact_info": "",
                    "application_url": "",
                    "external_url": job_url,
                    "html_content": "",
                    "scraped_date": datetime.now(),
                    "last_accessed": datetime.now()
                }
                job_details_cache.cache_job_details(job_url, error_details, is_valid=False, error_message=f"Unexpected error: {str(e)}")
            except Exception as cache_error:
                print(f"   ⚠️ Failed to cache error details: {cache_error}")
            
            return None

    def _extract_with_multiple_selectors(self, soup: BeautifulSoup, selectors: List[str]) -> str:
        """Extract text using multiple CSS selectors with fallback strategy."""
        for selector in selectors:
            try:
                elements = soup.select(selector)
                for element in elements:
                    text = element.get_text(strip=True)
                    if text and len(text) > 2 and len(text) < 200:  # Reasonable length
                        return text
            except Exception:
                continue
        return ""

    def _extract_comprehensive_description(self, soup: BeautifulSoup) -> str:
        """Extract job description using comprehensive HTML pattern matching."""
        
        # Indeed-specific description containers
        description_selectors = [
            # Indeed-specific selectors
            'div#jobDescriptionText',
            'div[class*="job-description"]',
            'div[class*="description"]',
            'div[class*="content"]',
            'div[class*="details"]',
            'div[class*="job-details"]',
            'div[class*="position-details"]',
            'div[class*="role-description"]',
            'div[class*="job-content"]',
            'div[class*="vacancy-content"]',
            
            # Data attributes
            '[data-testid*="description"]',
            '[data-at*="description"]',
            '[data-genesis-element="BODY"]',
            
            # Generic content containers
            'div[class*="main-content"]',
            'div[class*="primary-content"]',
            'div[class*="body-content"]',
            'div[class*="text-content"]',
            
            # Article and section tags
            'article',
            'section[class*="content"]',
            'section[class*="description"]',
            
            # Indeed-specific patterns
            'div[class*="indeed-job"]',
            'div[class*="indeed-content"]',
            
            # Fallback: any div with substantial text content
            'div'
        ]
        
        best_description = ""
        max_length = 0
        
        for selector in description_selectors:
            try:
                elements = soup.select(selector)
                for element in elements:
                    # Skip navigation, headers, footers
                    if self._is_content_element(element):
                        text = self._clean_description_text(element.get_text(separator='\n', strip=True))
                        if text and len(text) > 100:  # Substantial content
                            if len(text) > max_length:
                                best_description = text
                                max_length = len(text)
            except Exception:
                continue
        
        # If no good description found, try alternative strategies
        if not best_description:
            best_description = self._extract_description_alternative_methods(soup)
        
        return best_description or "No description available"

    def _extract_description_from_card(self, card):
        """Extract description from job card during search results parsing."""
        description_selectors = [
            'div[class*="job-snippet"]',
            'div[class*="job-summary"]',
            'div[class*="job-description"]',
            'div[class*="description"]',
            'div[class*="content"]',
            'div[class*="details"]',
            'p[class*="description"]',
            'p[class*="summary"]',
            'span[class*="description"]',
            'span[class*="summary"]',
            '[data-testid*="description"]',
            '[data-at*="description"]',
            '[data-genesis-element="TEXT"]',
            'p',
            'div'
        ]
        best_description = ""
        max_length = 0
        for selector in description_selectors:
            try:
                elements = card.select(selector)
                for element in elements:
                    text = element.get_text(separator='\n', strip=True)
                    if text and len(text) > 20:
                        if len(text) > max_length:
                            best_description = text
                            max_length = len(text)
            except Exception:
                continue
        return best_description or ""

    def _is_content_element(self, element) -> bool:
        """Check if element is likely to contain job description content."""
        if not element:
            return False
        
        # Skip navigation, headers, footers
        skip_classes = ['nav', 'header', 'footer', 'sidebar', 'menu', 'breadcrumb', 'pagination']
        skip_ids = ['nav', 'header', 'footer', 'sidebar', 'menu']
        
        element_classes = element.get('class', [])
        element_id = element.get('id', '')
        
        # Check for navigation indicators
        for skip_class in skip_classes:
            if any(skip_class in str(cls).lower() for cls in element_classes):
                return False
        
        for skip_id in skip_ids:
            if skip_id in element_id.lower():
                return False
        
        # Check for job-related content indicators
        text = element.get_text().lower()
        job_indicators = ['responsibilities', 'requirements', 'qualifications', 'experience', 
                         'skills', 'duties', 'tasks', 'aufgaben', 'anforderungen', 
                         'qualifikation', 'erfahrung', 'kenntnisse', 'aufgabenbereich']
        
        return any(indicator in text for indicator in job_indicators)

    def _clean_description_text(self, text: str) -> str:
        """Clean and format description text."""
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove common unwanted patterns
        unwanted_patterns = [
            r'cookie|privacy|terms|conditions|legal',
            r'subscribe|newsletter|sign up',
            r'share|social|follow us',
            r'back to top|scroll to top',
            r'©|copyright|all rights reserved',
            r'powered by|built with',
            r'loading|please wait',
            r'javascript|enable javascript'
        ]
        
        for pattern in unwanted_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Clean up line breaks and formatting
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = text.strip()
        
        return text

    def _extract_description_alternative_methods(self, soup: BeautifulSoup) -> str:
        """Alternative methods for extracting job description when standard methods fail."""
        
        # Method 1: Look for the largest text block
        text_blocks = []
        for element in soup.find_all(['div', 'section', 'article']):
            text = element.get_text(separator='\n', strip=True)
            if len(text) > 200:  # Substantial content
                text_blocks.append((len(text), text))
        
        if text_blocks:
            # Sort by length and take the longest
            text_blocks.sort(reverse=True)
            return self._clean_description_text(text_blocks[0][1])
        
        # Method 2: Look for specific job-related sections
        job_sections = [
            'responsibilities', 'requirements', 'qualifications', 'experience',
            'skills', 'duties', 'tasks', 'about the role', 'job description',
            'aufgaben', 'anforderungen', 'qualifikation', 'erfahrung',
            'kenntnisse', 'aufgabenbereich', 'stellenbeschreibung'
        ]
        
        for section in job_sections:
            elements = soup.find_all(text=re.compile(section, re.IGNORECASE))
            for element in elements:
                parent = element.parent
                if parent:
                    # Get the next few siblings or children
                    siblings = list(parent.find_next_siblings())[:5]
                    children = parent.find_all(['p', 'div', 'li'], limit=10)
                    
                    combined_text = ""
                    for sibling in siblings:
                        combined_text += sibling.get_text(separator='\n', strip=True) + "\n"
                    for child in children:
                        combined_text += child.get_text(separator='\n', strip=True) + "\n"
                    
                    if len(combined_text) > 100:
                        return self._clean_description_text(combined_text)
        
        return "" 

    def _detect_language_sophisticated(self, title: str, description: str) -> str:
        """Sophisticated language detection for job postings."""
        main_content = description if description else title
        if not main_content:
            return "Other"
        text_to_check = main_content.lower()
        strong_german_indicators = [
            'wir suchen', 'für unser', 'mitarbeiter', 'unternehmen', 'bereich',
            'erfahrung', 'kenntnisse', 'aufgaben', 'anforderungen', 'qualifikation',
            'bewerbung', 'arbeitsplatz', 'stelle', 'gmbh', 'ag', '(m/w/d)', '(w/m/d)',
            'deutsch', 'deutschland', 'entwickler', 'ingenieur', 'berater'
        ]
        strong_english_indicators = [
            'we are looking', 'for our', 'team', 'experience', 'skills',
            'responsibilities', 'requirements', 'opportunity', 'position',
            'developer', 'engineer', 'consultant', 'company', 'ltd', 'inc',
            'you will', 'you should', 'you must', 'we offer', 'we provide'
        ]
        german_score = sum(1 for indicator in strong_german_indicators if indicator in text_to_check)
        english_score = sum(1 for indicator in strong_english_indicators if indicator in text_to_check)
        import re
        german_patterns = [r'\bder\b', r'\bdie\b', r'\bdas\b', r'\bund\b', r'\bmit\b', r'\bfür\b', r'\bvon\b', r'\bzu\b', r'\bbei\b', r'\bnach\b', r'\büber\b']
        english_patterns = [r'\bthe\b', r'\band\b', r'\bwith\b', r'\bfor\b', r'\bfrom\b', r'\bto\b', r'\bat\b', r'\bafter\b', r'\bover\b']
        german_pattern_count = sum(len(re.findall(pattern, text_to_check)) for pattern in german_patterns)
        english_pattern_count = sum(len(re.findall(pattern, text_to_check)) for pattern in english_patterns)
        total_german_score = german_score * 3 + german_pattern_count * 0.5
        total_english_score = english_score * 3 + english_pattern_count * 0.5
        if total_german_score > total_english_score and total_german_score >= 2:
            return "DE"
        elif total_english_score > total_german_score and total_english_score >= 2:
            return "EN"
        else:
            if any(phrase in text_to_check for phrase in ['english', 'international', 'global']):
                return "EN"
            elif any(phrase in text_to_check for phrase in ['german', 'deutsch', 'deutschland']):
                return "DE"
            else:
                return "EN" 