"""
Stellenanzeigen.de Job Scraper

Handles all Stellenanzeigen.de-specific job scraping functionality.
"""

import requests
import time
import random
from datetime import datetime
from urllib.parse import urlencode, urljoin
from typing import List, Dict, Optional, Any, Union
from bs4 import BeautifulSoup, Tag
import re

try:
    from .base_scraper import BaseScraper
except ImportError:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from base_scraper import BaseScraper


class StellenanzeigenScraper(BaseScraper):
    """Stellenanzeigen.de-specific job scraper with location mapping and cookie handling."""
    
    def __init__(self, debug: bool = False, use_flaresolverr: bool = False):
        """
        Initialize Stellenanzeigen.de scraper.
        
        Args:
            debug: Enable debug logging
            use_flaresolverr: Use FlareSolverr for requests
        """
        super().__init__(debug, use_flaresolverr=use_flaresolverr)
        self.base_url = 'https://www.stellenanzeigen.de'
        self._current_search_location = ""
        
        # Location mapping for Stellenanzeigen.de specific IDs
        self.location_map = {
            'berlin': 'M-DE-12803',
            'hamburg': 'M-DE-12601',
            'munich': 'M-DE-09000',
            'münchen': 'M-DE-09000',
            'düsseldorf': 'M-DE-12804',
            'dusseldorf': 'M-DE-12804',
            'duesseldorf': 'M-DE-12804',
            'essen': 'M-DE-12804',  # Same region as Düsseldorf
            'cologne': 'M-DE-10000',
            'köln': 'M-DE-10000',
            'frankfurt': 'M-DE-08000',
            'stuttgart': 'M-DE-07000',
            'dortmund': 'M-DE-12805',
            'bremen': 'M-DE-04000',
            'hannover': 'M-DE-03000',
            'remote': 'X-HO-100',
            'homeoffice': 'X-HO-100',
            'home office': 'X-HO-100',
            'work from home': 'X-HO-100',
            'wfh': 'X-HO-100'
        }
    
    def get_platform_name(self) -> str:
        """Return the platform name."""
        return "Stellenanzeigen.de"
    
    def search_jobs(self, keywords: str, location: str = "", max_pages: int = 3, 
                   english_only: bool = False, **kwargs) -> List[Dict]:
        """
        Search Stellenanzeigen.de for jobs using web scraping with correct URL format and cookie handling.
        
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
                print(f"\n--- Searching Stellenanzeigen.de for: '{keyword}' ---")
                # Store current search location for fallback in parsing
                self._current_search_location = location
                
                for page in range(1, max_pages + 1):
                    # Build correct Stellenanzeigen.de search URL format
                    params: Dict[str, Union[str, int]] = {
                        'fulltext': keyword
                    }
                    
                    # Add location ID if location is provided
                    if location:
                        location_lower = location.lower().strip()
                        location_id = self.location_map.get(location_lower)
                        if location_id:
                            params['locationIds'] = location_id
                            # Log remote search when using X-HO-100
                            if location_id == 'X-HO-100':
                                print(f"   🏠 Searching for REMOTE jobs (locationId: {location_id})")
                            else:
                                print(f"   📍 Searching in location: {location} (locationId: {location_id})")
                    
                    # Add pagination
                    if page > 1:
                        params['page'] = page
                    
                    search_url = f"{self.base_url}/suche/?" + urlencode(params)
                    
                    print(f"📄 Fetching Stellenanzeigen page {page} for '{keyword}'")
                    
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                        'Accept-Language': 'de-DE,de;q=0.8,en-US;q=0.5,en;q=0.3',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'DNT': '1',
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': '1'
                    }
                    cookies = {'cookieConsent': 'accepted', 'privacy_consent': 'true'}
                    response = self.get_page(search_url, headers=headers, cookies=cookies, timeout=30)
                    
                    page_jobs = []
                    if response and response.status_code == 200:
                        soup = self.get_soup(response.text)
                        if soup:
                            page_jobs = self._extract_stellenanzeigen_jobs(soup, search_url)
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
            print(f"❌ Error during Stellenanzeigen search: {e}")
        
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
        
        print(f"\n🎯 Total unique Stellenanzeigen jobs found: {len(unique_jobs)}")
        return unique_jobs

    def _extract_stellenanzeigen_jobs(self, soup: BeautifulSoup, page_url: str) -> List[Dict]:
        """Extract job listings from Stellenanzeigen.de search results."""
        jobs = []
        
        try:
            # Enhanced Stellenanzeigen.de job cards selectors
            job_cards = []
            
            if self.debug:
                print(f"   🔍 Starting job extraction from: {page_url}")
            
            # Try specific Stellenanzeigen.de selectors first
            patterns = [
                {'tag': ['div'], 'class': lambda x: x and any(term in x.lower() for term in ['job-item', 'job-result', 'stellenanzeige', 'job-card'])},
                {'tag': ['article'], 'class': lambda x: x and 'job' in x.lower()},
                {'tag': ['div'], 'class': lambda x: x and any(term in x.lower() for term in ['job', 'stelle', 'anzeige'])},
                {'tag': ['li'], 'class': lambda x: x and 'job' in x.lower()},
            ]
            
            for pattern in patterns:
                cards = soup.find_all(pattern['tag'], class_=pattern['class'])
                if self.debug:
                    print(f"   🔍 Pattern {pattern} found {len(cards)} potential cards")
                
                if cards:
                    # Filter out invalid cards (navigation, buttons, etc.)
                    valid_cards = []
                    for card in cards:
                        card_text = card.get_text(strip=True)
                        # Skip if it's just navigation text or too short
                        if (len(card_text) > 50 and  # Must have substantial content
                            not any(nav_text in card_text.lower() for nav_text in 
                                   ['seite neu laden', 'weiter', 'zurück', 'finde deinen job', 
                                    'anzeigen', 'navigation', 'filter', 'sortieren']) and
                            any(job_indicator in card_text.lower() for job_indicator in 
                               ['stelle', 'job', 'position', 'mitarbeiter', 'developer', 'administrator'])):
                            valid_cards.append(card)
                    
                    if valid_cards:
                        job_cards = valid_cards
                        if self.debug:
                            print(f"   🎯 Found {len(valid_cards)} valid job cards using pattern: {pattern}")
                        break
            
            # Fallback: look for any elements with job-related attributes or text
            if not job_cards:
                if self.debug:
                    print(f"   ⚠️ No job cards found with specific patterns, trying fallback")
                
                all_elements = soup.find_all(['div', 'article', 'li'])
                job_cards = [elem for elem in all_elements if elem.get_text() and any(keyword in elem.get_text().lower() for keyword in ['developer', 'engineer', 'administrator', 'manager', 'analyst'])]
                if self.debug:
                    print(f"   ⚠️ Using fallback extraction, found {len(job_cards)} potential job elements")
            
            if self.debug:
                print(f"   📊 Total job cards to process: {len(job_cards)}")
            
            for i, card in enumerate(job_cards):
                try:
                    if isinstance(card, Tag):
                        if self.debug:
                            print(f"   🔍 Processing card {i+1}/{len(job_cards)}")
                        
                        job_data = self._parse_stellenanzeigen_job_card(card, page_url)
                        if job_data and job_data.get('title'):
                            jobs.append(job_data)
                            if self.debug:
                                print(f"   ✅ Added job: {job_data.get('title', 'Unknown')}")
                        else:
                            if self.debug:
                                print(f"   ❌ Skipped card {i+1}: No valid job data")
                except Exception as e:
                    if self.debug:
                        print(f"   ⚠️ Error parsing Stellenanzeigen job card {i+1}: {e}")
                    continue
                    
        except Exception as e:
            print(f"❌ Error extracting Stellenanzeigen jobs: {e}")
        
        if self.debug:
            print(f"   🎯 Total jobs extracted: {len(jobs)}")
        
        return jobs

    def _parse_stellenanzeigen_job_card(self, card: Tag, page_url: str) -> Dict:
        """Parse individual Stellenanzeigen.de job card."""
        job_data = {}
        title = ""
        company = ""
        location = ""
        job_url = ""
        description = ""
        
        # Extract title - try multiple approaches
        title_element = card.find(['h1', 'h2', 'h3', 'h4'])
        if title_element:
            title = title_element.get_text(strip=True)
        
        # If no title found, try link text
        if not title:
            link_element = card.find('a', href=True)
            if link_element:
                title = link_element.get_text(strip=True)

        # Extract URL
        link_element = card.find('a', href=True)
        if link_element and isinstance(link_element.get('href'), str):
            href = link_element.get('href')
            if href:
                job_url = urljoin(self.base_url, href)

        # Enhanced Company extraction with multiple selectors
        company_selectors = [
            'span[class*="company"]',
            'div[class*="company"]',
            'p[class*="company"]',
            '[data-testid*="company"]',
            '[data-at*="company"]',
            '[class*="employer"]',
            '[class*="organization"]',
            '[class*="firma"]',
            '[class*="unternehmen"]',
            'span[class*="employer"]',
            'div[class*="employer"]',
            'p[class*="employer"]',
            # Additional Stellenanzeigen-specific selectors
            '[class*="job-company"]',
            '[class*="job-employer"]',
            '[class*="company-name"]',
            '[class*="employer-name"]',
            '[class*="firmenname"]',
            '[class*="unternehmensname"]',
            'span[class*="firma"]',
            'div[class*="firma"]',
            'p[class*="firma"]',
            'span[class*="unternehmen"]',
            'div[class*="unternehmen"]',
            'p[class*="unternehmen"]',
            # Generic text-based fallbacks
            'strong',
            'b',
            'em',
            'span[class*="name"]',
            'div[class*="name"]'
        ]
        
        for selector in company_selectors:
            try:
                elements = card.select(selector)
                for element in elements:
                    text = element.get_text(strip=True)
                    if text and len(text) > 2 and len(text) < 100:  # Reasonable company name length
                        # Additional validation to ensure it's likely a company name
                        if not any(skip in text.lower() for skip in ['stelle', 'job', 'position', 'mitarbeiter', 'developer', 'engineer', 'manager']):
                            company = text
                            break
                if company:
                    break
            except Exception:
                continue
        
        # Fallback: try to extract company from any text that looks like a company name
        if not company:
            # Look for any text that might be a company name
            all_text_elements = card.find_all(['span', 'div', 'p', 'strong', 'b', 'em'])
            for element in all_text_elements:
                text = element.get_text(strip=True)
                # Check if text looks like a company name (not too long, not job-related words)
                if (text and 3 <= len(text) <= 50 and 
                    not any(job_word in text.lower() for job_word in ['stelle', 'job', 'position', 'mitarbeiter', 'developer', 'engineer', 'manager', 'administrator']) and
                    not any(skip in text.lower() for skip in ['seite neu laden', 'weiter', 'zurück', 'finde deinen job', 'anzeigen', 'navigation', 'filter', 'sortieren']) and
                    text != title and text != location):
                    # Additional check: company names usually don't contain certain patterns
                    if not any(pattern in text for pattern in ['(', ')', '[', ']', 'http', 'www', '.com', '.de']):
                        company = text
                        break
        
        # Enhanced Location extraction with multiple selectors
        location_selectors = [
            'span[class*="location"]',
            'div[class*="location"]',
            'p[class*="location"]',
            '[data-testid*="location"]',
            '[data-at*="location"]',
            '[class*="address"]',
            '[class*="place"]',
            '[class*="city"]',
            '[class*="ort"]',
            '[class*="standort"]',
            'span[class*="address"]',
            'div[class*="address"]',
            'p[class*="address"]'
        ]
        
        for selector in location_selectors:
            try:
                elements = card.select(selector)
                for element in elements:
                    text = element.get_text(strip=True)
                    if text and len(text) > 2 and len(text) < 100:  # Reasonable location length
                        location = text
                        break
                if location:
                    break
            except Exception:
                continue
        
        # Fallback: Extract location from URL if not found in HTML
        if not location:
            location = self._extract_location_from_url(job_url)
        
        # Check if this is a remote job search and update location accordingly
        if self._current_search_location and self._current_search_location.lower().strip() in ['remote', 'homeoffice', 'home office', 'work from home', 'wfh']:
            # If we're searching for remote jobs, label the location as remote
            if location:
                # Check if the location text indicates remote work
                remote_indicators = ['remote', 'home office', 'homeoffice', 'wfh', 'work from home', 'telearbeit', 'mobil', 'flexibel']
                if any(indicator in location.lower() for indicator in remote_indicators):
                    location = "Remote"
                else:
                    # If location doesn't indicate remote, but we're searching remote, mark as remote
                    location = f"{location} (Remote)"
            else:
                location = "Remote"
        
        # Enhanced Description extraction with multiple selectors
        description_selectors = [
            'p[class*="description"]',
            'div[class*="description"]',
            'span[class*="description"]',
            '[class*="summary"]',
            '[class*="excerpt"]',
            '[class*="preview"]',
            '[class*="teaser"]',
            'p[class*="summary"]',
            'div[class*="summary"]',
            'span[class*="summary"]'
        ]
        
        for selector in description_selectors:
            try:
                elements = card.select(selector)
                for element in elements:
                    text = element.get_text(strip=True)
                    if text and len(text) > 20:  # Substantial description
                        description = text
                        break
                if description:
                    break
            except Exception:
                continue
        
        # Fallback: extract any meaningful text that might be description
        if not description:
            # Look for any paragraph or div with substantial text
            text_elements = card.find_all(['p', 'div', 'span'])
            for element in text_elements:
                text = element.get_text(strip=True)
                # Skip if it's the title, company, or location
                if (text and len(text) > 30 and 
                    text != title and text != company and text != location and
                    not any(skip in text.lower() for skip in ['seite neu laden', 'weiter', 'zurück', 'finde deinen job'])):
                    description = text
                    break
            
        job_data = {
            'title': title,
            'company': company,
            'location': location,
            'url': job_url,
            'description': description,
            'posted_date': ''
        }
        
        # Debug logging
        if self.debug:
            print(f"   🔍 Parsed job card:")
            print(f"     - Title: {title}")
            print(f"     - Company: {company}")
            print(f"     - Location: {location}")
            print(f"     - URL: {job_url}")
            print(f"     - Description length: {len(description)}")
        
        return job_data

    def fetch_job_details(self, job_url: str) -> Optional[Dict[str, Any]]:
        """Fetch detailed information for a single job from its URL."""
        try:
            # Import cache service
            try:
                from ..services.job_details_cache import job_details_cache
            except ImportError:
                from services.job_details_cache import job_details_cache
            
            # Enhanced cache check with better retry mechanism for Stellenanzeigen
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
            
            # Enhanced Stellenanzeigen-specific headers and timeout
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'de-DE,de;q=0.8,en-US;q=0.5,en;q=0.3',
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
                    response = self.get_page(job_url, headers=headers, timeout=45)  # Increased timeout for Stellenanzeigen
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
                soup = self.get_soup(html_content)
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
            title = self._extract_with_multiple_selectors(soup, title_selectors) or "Unknown Title"
            
            # Company extraction
            company_selectors = [
                'span[class*="company"]',
                'div[class*="company"]',
                '[data-testid*="company"]',
                '[data-at*="company"]',
                '[class*="employer"]',
                '[class*="organization"]',
                'p[class*="company"]',
                '[class*="firma"]',
                '[class*="unternehmen"]'
            ]
            company = self._extract_with_multiple_selectors(soup, company_selectors) or "Unknown Company"
            
            # Location extraction with Stellenanzeigen-specific selectors
            location_selectors = [
                # Stellenanzeigen-specific selectors
                'span[class*="location"]',
                'div[class*="location"]',
                '[data-testid*="location"]',
                '[data-at*="location"]',
                '[class*="address"]',
                '[class*="place"]',
                '[class*="city"]',
                '[class*="ort"]',
                '[class*="standort"]',
                # Additional Stellenanzeigen-specific patterns
                '[class*="job-location"]',
                '[class*="position-location"]',
                '[class*="vacancy-location"]',
                '[class*="arbeitsort"]',
                '[class*="arbeitsplatz"]',
                '[class*="standort"]',
                '[class*="region"]',
                '[class*="gebiet"]',
                # German-specific location patterns
                '[class*="wohnort"]',
                '[class*="anschrift"]',
                '[class*="adresse"]',
                # Generic location indicators
                'span[class*="geo"]',
                'div[class*="geo"]',
                '[itemprop="addressLocality"]',
                '[itemprop="addressRegion"]',
                '[itemprop="addressCountry"]'
            ]
            location = self._extract_with_multiple_selectors(soup, location_selectors)
            
            # Fallback: Extract location from URL if not found in HTML
            if not location or location == "Unknown Location":
                location = self._extract_location_from_url(job_url)
            
            # Final fallback
            if not location:
                location = "Unknown Location"
            
            # Salary extraction
            salary_selectors = [
                'span[class*="salary"]',
                'div[class*="salary"]',
                '[data-testid*="salary"]',
                '[data-at*="salary"]',
                '[class*="gehalt"]',
                '[class*="vergütung"]',
                '[class*="compensation"]'
            ]
            salary = self._extract_with_multiple_selectors(soup, salary_selectors) or ""
            
            # Enhanced description extraction
            description = self._extract_comprehensive_description(soup)
            
            # Content validation for Stellenanzeigen
            if not title or title == "Unknown Title":
                print(f"   ⚠️ Warning: Could not extract title for: {job_url}")
            
            if not company or company == "Unknown Company":
                print(f"   ⚠️ Warning: Could not extract company for: {job_url}")
            
            if not description or len(description.strip()) < 50:
                print(f"   ⚠️ Warning: Description too short for: {job_url} ({len(description)} chars)")
            
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
                print(f"   ⚠️ Error fetching Stellenanzeigen job details for {job_url}: {e}")
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

    def _extract_location_from_url(self, job_url: str) -> str:
        """Extract location information from Stellenanzeigen job URL."""
        try:
            # Parse URL to extract location information
            from urllib.parse import urlparse, parse_qs
            
            # Check if URL contains location information
            if 'stellenanzeigen.de' in job_url:
                # Extract location from URL path or query parameters
                parsed_url = urlparse(job_url)
                
                # Look for location in URL path
                path_parts = parsed_url.path.split('/')
                for part in path_parts:
                    # Check for German city names in URL
                    german_cities = [
                        'berlin', 'hamburg', 'münchen', 'munich', 'köln', 'cologne', 
                        'frankfurt', 'stuttgart', 'düsseldorf', 'dortmund', 'essen',
                        'leipzig', 'bremen', 'dresden', 'hannover', 'nürnberg', 
                        'nuremberg', 'duisburg', 'bochum', 'wuppertal', 'bielefeld',
                        'bonn', 'münster', 'karlsruhe', 'mannheim', 'augsburg',
                        'wiesbaden', 'gelsenkirchen', 'mönchengladbach', 'braunschweig',
                        'chemnitz', 'kiel', 'aachen', 'halle', 'magdeburg', 'freiburg',
                        'krefeld', 'lübeck', 'oberhausen', 'erfurt', 'mainz', 'rostock',
                        'kassel', 'hagen', 'potsdam', 'saarbrücken', 'hamm', 'mülheim',
                        'ludwigshafen', 'leverkusen', 'oldenburg', 'osnabrück', 'solingen',
                        'heidelberg', 'herne', 'neuss', 'darmstadt', 'paderborn',
                        'regensburg', 'ingolstadt', 'würzburg', 'fürth', 'wolfsburg',
                        'offenbach', 'ulm', 'heilbronn', 'pforzheim', 'göttingen',
                        'bottrop', 'trier', 'recklinghausen', 'reutlingen',
                        'bremerhaven', 'koblenz', 'bergisch', 'gladbach', 'jena',
                        'remscheid', 'erlangen', 'moers', 'siegen', 'hildesheim',
                        'salzgitter', 'castrop-rauxel', 'muelheim', 'herxheim'
                    ]
                    
                    if part.lower() in german_cities:
                        return part.title()
                
                # Check query parameters for location IDs
                query_params = parse_qs(parsed_url.query)
                if 'locationIds' in query_params:
                    location_id = query_params['locationIds'][0]
                    # Map location ID back to city name
                    reverse_location_map = {v: k for k, v in self.location_map.items()}
                    if location_id in reverse_location_map:
                        return reverse_location_map[location_id].title()
                
                # Look for location patterns in the URL
                url_lower = job_url.lower()
                for city in german_cities:
                    if city in url_lower:
                        return city.title()
        
        except Exception as e:
            if self.debug:
                print(f"   ⚠️ Error extracting location from URL {job_url}: {e}")
        
        return ""

    def _extract_comprehensive_description(self, soup: BeautifulSoup) -> str:
        """Extract job description using comprehensive HTML pattern matching."""
        
        # Stellenanzeigen-specific description containers
        description_selectors = [
            # Stellenanzeigen-specific selectors
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
            
            # German-specific patterns
            'div[class*="stellenbeschreibung"]',
            'div[class*="aufgabenbereich"]',
            'div[class*="anforderungen"]',
            
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
            'div[class*="stellenbeschreibung"]',
            'div[class*="aufgabenbereich"]',
            'div[class*="anforderungen"]',
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