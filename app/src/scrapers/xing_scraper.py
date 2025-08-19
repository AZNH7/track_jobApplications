"""
Xing Job Scraper

Handles all Xing-specific job scraping functionality.
"""

import requests
import time
import random
from datetime import datetime
from urllib.parse import urlencode, urljoin
from typing import List, Dict, Optional, Any
from bs4 import BeautifulSoup, Tag
import re

try:
    from .base_scraper import BaseScraper
except ImportError:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from base_scraper import BaseScraper


class XingScraper(BaseScraper):
    """Xing-specific job scraper with enhanced extraction."""
    
    def __init__(self, debug: bool = False, use_flaresolverr: bool = False):
        """
        Initialize Xing scraper.
        
        Args:
            debug: Enable debug logging
            use_flaresolverr: Use FlareSolverr for requests
        """
        super().__init__(debug, use_flaresolverr=use_flaresolverr)
        self.base_url = 'https://www.xing.com'
        self._current_search_location = ""
        # Use provided debug setting
        self.debug = debug
    
    def get_platform_name(self) -> str:
        """Return the platform name."""
        return "Xing"
    
    def search_jobs(self, keywords: str, location: str = "", max_pages: int = 3, 
                   english_only: bool = False, **kwargs) -> List[Dict]:
        """
        Search Xing for jobs using enhanced web scraping.
        
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
        
        # Split keywords to search one by one
        keyword_list = [k.strip() for k in keywords.split(',') if k.strip()]
        if not keyword_list:
            keyword_list = [keywords]

        try:
            for keyword in keyword_list:
                print(f"\n--- Searching Xing.com for: '{keyword}' ---")
                # Store current search location for fallback in parsing
                self._current_search_location = location
                
                for page in range(1, max_pages + 1):
                    # Build Xing search URL
                    params = {
                        'keywords': keyword,
                        'page': page
                    }
                    if location:
                        params['location'] = location
                    
                    search_url = f"{self.base_url}/jobs/search?" + urlencode(params)
                    
                    print(f"📄 Fetching Xing page {page} for '{keyword}'")
                    
                    response = self.get_page(search_url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'}, timeout=30)

                    page_jobs = []
                    if response and response.status_code == 200:
                        soup = self.get_soup(response.text)
                        if soup:
                            page_jobs = self._extract_xing_jobs(soup, search_url)
                    else:
                        status_code = response.status_code if response else 'N/A'
                        print(f"   ❌ HTTP {status_code} for page {page}")

                    if page_jobs:
                        all_jobs.extend(page_jobs)
                        print(f"   Found {len(page_jobs)} jobs on page {page} for '{keyword}'")

                    # Break if no jobs found (likely end of results)
                    if page > 1 and not page_jobs:
                        print("   ℹ️ No more jobs found for this keyword")
                        break
                    
                    time.sleep(random.uniform(1, 3))
                
        except Exception as e:
            print(f"❌ Error during Xing search: {e}")
        
        # Deduplicate results
        seen_urls = set()
        unique_jobs = []
        for job in all_jobs:
            if (job_url := job.get('url')) and job_url not in seen_urls:
                unique_jobs.append(job)
                seen_urls.add(job_url)

        # When English is not selected, use local LLM for language detection
        # The LLM will be used in the job processing pipeline to determine language
        if not english_only:
            print(f"   🤖 Will use local LLM for language detection during job processing")
        
        print(f"\n🎯 Total unique Xing jobs found: {len(unique_jobs)}")
        return unique_jobs

    def _extract_xing_jobs(self, soup: BeautifulSoup, page_url: str) -> List[Dict]:
        """Extract job listings from Xing search results with enhanced selectors."""
        jobs = []
        
        try:
            # Target only the main job article elements, not fragments
            job_cards = soup.find_all('article', {'data-testid': 'job-search-result'})
            
            if self.debug:
                print(f"   🎯 Found {len(job_cards)} job article elements")
            
            if not job_cards:
                # Fallback: look for other article elements
                job_cards = soup.find_all('article')
                if self.debug:
                    print(f"   🔄 Fallback: Found {len(job_cards)} article elements")
            
            for card in job_cards:
                try:
                    if isinstance(card, Tag):
                        job_data = self._parse_xing_job_card(card, page_url)
                        if job_data and job_data.get('title') and job_data.get('url'):
                            jobs.append(job_data)
                            if self.debug:
                                print(f"   ✅ Added job: {job_data.get('title')[:50]}...")
                        elif self.debug and job_data.get('title'):
                            print(f"   ❌ Skipped job (no URL): {job_data.get('title')[:50]}...")
                except Exception as e:
                    if self.debug:
                        print(f"   ⚠️ Error parsing Xing job card: {e}")
                    continue
                    
        except Exception as e:
            print(f"❌ Error extracting Xing jobs: {e}")
        
        return jobs

    def _parse_xing_job_card(self, card: Tag, page_url: str) -> Dict:
        """Parse individual Xing job card with enhanced extraction."""
        job_data = {}
        title = ""
        company = ""
        location = ""
        job_url = ""

        # Extract title
        title_element = card.find(['h1', 'h2', 'h3', 'h4'])
        if title_element:
            title = title_element.get_text(strip=True)

        # Extract URL
        link_element = card.find('a', href=True)
        if link_element and isinstance(link_element['href'], str):
            href = link_element['href']
            if href.startswith('http'):
                job_url = href
            else:
                job_url = urljoin(self.base_url, href)
        
        # Extract Company
        company_element = card.find('p', class_=lambda c: c and 'Company' in c)
        if company_element:
            company = company_element.get_text(strip=True)

        # Extract Location
        location_element = card.find('p', class_=lambda c: c and 'Location' in c)
        if location_element:
            location = location_element.get_text(strip=True)


        job_data = {
            'title': title,
            'company': company,
            'location': location,
            'url': job_url,
            'description': '', 
            'posted_date': '' 
        }

        return job_data


    def fetch_job_details(self, job_url: str) -> Optional[Dict[str, Any]]:
        """Fetch detailed information for a single job from its URL."""
        try:
            # Import cache service
            try:
                from ..services.job_details_cache import job_details_cache
            except ImportError:
                from services.job_details_cache import job_details_cache
            
            # Enhanced cache check with better retry mechanism for Xing
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
            
            # Enhanced Xing-specific headers and timeout
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            html_content = None
            response = None
            
            # Enhanced request with retry mechanism
            max_request_retries = 3
            request_retry_delay = 1.0
            
            for request_attempt in range(max_request_retries):
                try:
                    response = self.get_page(job_url, headers=headers, timeout=45)  # Increased timeout for Xing
                    if response and response.status_code == 200:
                        html_content = response.text
                        break
                    elif response and response.status_code in [403, 429, 500, 502, 503, 504]:
                        print(f"   ⚠️ HTTP {response.status_code} for job details (attempt {request_attempt + 1}/{max_request_retries}): {job_url}")
                        if request_attempt < max_request_retries - 1:
                            time.sleep(request_retry_delay * (request_attempt + 1))  # Exponential backoff
                            continue
                    else:
                        print(f"   ❌ HTTP {response.status_code if response else 'No response'} for job details: {job_url}")
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
                error_details = {
                    "title": f"Error - HTTP {response.status_code if response else 'No response'}",
                    "company": "Unknown",
                    "location": "Unknown",
                    "salary": "",
                    "description": f"HTTP {response.status_code if response else 'No response'} error after {max_request_retries} attempts",
                    "requirements": "",
                    "benefits": "",
                    "contact_info": "",
                    "application_url": "",
                    "external_url": job_url,
                    "html_content": "",
                    "scraped_date": datetime.now(),
                    "last_accessed": datetime.now()
                }
                job_details_cache.cache_job_details(job_url, error_details, is_valid=False, error_message=f"HTTP {response.status_code if response else 'No response'} error")
                return None
            
            if not html_content:
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
                job_details_cache.cache_job_details(job_url, error_details, is_valid=False, error_message="No HTML content received")
                return None
            
            # Enhanced HTML parsing with error handling
            try:
                soup = BeautifulSoup(html_content, 'html.parser')
            except Exception as parse_error:
                print(f"   ⚠️ HTML parsing error for {job_url}: {parse_error}")
                error_details = {
                    "title": "Error - HTML Parsing",
                    "company": "Unknown",
                    "location": "Unknown",
                    "salary": "",
                    "description": f"Failed to parse HTML content: {str(parse_error)}",
                    "requirements": "",
                    "benefits": "",
                    "contact_info": "",
                    "application_url": "",
                    "external_url": job_url,
                    "html_content": html_content[:1000] if html_content else "",  # Store partial content for debugging
                    "scraped_date": datetime.now(),
                    "last_accessed": datetime.now()
                }
                job_details_cache.cache_job_details(job_url, error_details, is_valid=False, error_message=f"HTML parsing error: {str(parse_error)}")
                return None
            
            # Extract job information from the page with enhanced error handling
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
            
            try:
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
                title = self._extract_with_multiple_selectors(soup, title_selectors) or "Unknown Title"
                
                # Company extraction
                company_selectors = [
                    'span[class*="company"]',
                    'div[class*="company"]',
                    '[data-testid*="company"]',
                    '[data-at*="company"]',
                    '[class*="employer"]',
                    '[class*="organization"]',
                    'p[class*="company"]'
                ]
                company = self._extract_with_multiple_selectors(soup, company_selectors) or "Unknown Company"
                
                # Location extraction
                location_selectors = [
                    'span[class*="location"]',
                    'div[class*="location"]',
                    '[data-testid*="location"]',
                    '[data-at*="location"]',
                    '[class*="address"]',
                    '[class*="place"]',
                    '[class*="city"]'
                ]
                location = self._extract_with_multiple_selectors(soup, location_selectors) or "Unknown Location"
                
                # Enhanced description extraction
                description = self._extract_comprehensive_description(soup)
                
            except Exception as extraction_error:
                print(f"   ⚠️ Content extraction error for {job_url}: {extraction_error}")
                # Continue with basic extraction as fallback
                title = title or "Unknown Title"
                company = company or "Unknown Company"
                location = location or "Unknown Location"
                description = description or "Failed to extract description"
            
            # Create job details with enhanced metadata
            details = {
                "title": title or "Unknown Title",
                "company": company or "Unknown Company",
                "location": location or "Unknown Location",
                "salary": "",
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
            
            # Enhanced caching with retry mechanism
            cache_success = False
            max_cache_save_retries = 3
            cache_save_retry_delay = 0.5
            
            for cache_save_attempt in range(max_cache_save_retries):
                try:
                    cache_success = job_details_cache.cache_job_details(job_url, details)
                    if cache_success:
                        print(f"   ✅ Successfully cached Xing job details for: {job_url}")
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
            
            return details
            
        except Exception as e:
            if self.debug:
                print(f"   ⚠️ Error fetching Xing job details for {job_url}: {e}")
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
            
            # Try to cache the error details
            try:
                job_details_cache.cache_job_details(job_url, error_details, is_valid=False, error_message=f"Error: {str(e)}")
            except Exception as cache_error:
                print(f"   ⚠️ Failed to cache error details: {cache_error}")
            
            return error_details

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
        
        # Xing-specific description containers
        description_selectors = [
            # Xing-specific selectors
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
            
            # Xing-specific patterns
            'div[class*="xing-job"]',
            'div[class*="xing-content"]',
            
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