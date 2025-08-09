"""
MeineStadt.de Job Scraper

Handles all MeineStadt.de-specific job scraping functionality.
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


class MeinestadtScraper(BaseScraper):
    """MeineStadt.de-specific job scraper with local job focus."""
    
    def __init__(self, debug: bool = False, use_flaresolverr: bool = False):
        """
        Initialize MeineStadt.de scraper.
        
        Args:
            debug: Enable debug logging
            use_flaresolverr: Use FlareSolverr for requests
        """
        super().__init__(debug, use_flaresolverr=use_flaresolverr)
        self.base_url = 'https://jobs.meinestadt.de'
        self._current_search_location = ""
    
    def get_platform_name(self) -> str:
        """Return the platform name."""
        return "MeineStadt.de"
    
    def search_jobs(self, keywords: str, location: str = "", max_pages: int = 3, 
                   english_only: bool = False, **kwargs) -> List[Dict]:
        """
        Search MeineStadt.de for jobs using web scraping with advanced anti-bot techniques.
        
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
                print(f"\n--- Searching MeineStadt.de for: '{keyword}' ---")
                # Store current search location for fallback in parsing
                self._current_search_location = location
                
                # Advanced anti-bot headers with randomization
                def generate_headers():
                    """Generate sophisticated, randomized headers"""
                    user_agents = [
                        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
                        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
                        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
                    ]
                    
                    return {
                        'User-Agent': random.choice(user_agents),
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                        'Accept-Language': 'de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7',
                        'Accept-Encoding': 'gzip, deflate, br, zstd',
                        'Referer': 'https://jobs.meinestadt.de/',
                        'DNT': '1',
                        'Sec-Fetch-Dest': 'document',
                        'Sec-Fetch-Mode': 'navigate',
                        'Sec-Fetch-Site': 'same-origin',
                        'Sec-Fetch-User': '?1',
                        'Upgrade-Insecure-Requests': '1',
                        'Connection': 'keep-alive',
                        'Cache-Control': 'max-age=0',
                        'X-Requested-With': 'XMLHttpRequest',
                        'Pragma': 'no-cache',
                        'Sec-Ch-Ua': '"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"',
                        'Sec-Ch-Ua-Mobile': '?0',
                        'Sec-Ch-Ua-Platform': '"Windows"'
                    }
                
                for page in range(1, max_pages + 1):
                    # Build MeineStadt.de search URL
                    params = {
                        'was': keyword,
                        'seite': page
                    }
                    if location:
                        params['wo'] = location
                    
                    search_url = f"{self.base_url}/jobs?" + urlencode(params)
                    
                    print(f"📄 Fetching MeineStadt page {page} for '{keyword}'")
                    
                    headers = generate_headers()
                    response = self.get_page(search_url, headers=headers, timeout=30, allow_redirects=True)
                    
                    page_jobs = []
                    if response and response.status_code == 200:
                        soup = self.get_soup(response.text)
                        if soup:
                            page_jobs = self._extract_meinestadt_jobs(soup, search_url)
                    elif response and response.status_code == 403:
                        print(f"   ❌ HTTP 403 Forbidden. Anti-bot protection detected.")
                        break
                    else:
                        status_code = response.status_code if response else 'N/A'
                        print(f"   ❌ HTTP {status_code} for page {page}")
                        break

                    if page_jobs:
                        filtered_jobs = [job for job in page_jobs if self._is_valid_job_listing(job)]
                        all_jobs.extend(filtered_jobs)
                        print(f"   Found {len(filtered_jobs)} valid jobs on page {page} for '{keyword}'")

                    # Break if no jobs found (likely end of results)
                    if page > 1 and not page_jobs:
                        print("   ℹ️ No more jobs found for this keyword")
                        break
                    
                    # Randomized delay to mimic human browsing
                    time.sleep(random.uniform(1.5, 3.5))
                
        except Exception as e:
            print(f"❌ Error during MeineStadt search: {e}")
        
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
        
        print(f"\n🎯 Total unique MeineStadt jobs found: {len(unique_jobs)}")
        return unique_jobs

    def _extract_meinestadt_jobs(self, soup: BeautifulSoup, page_url: str) -> List[Dict]:
        """
        Extract job listings from MeineStadt.de search results with advanced validation.
        
        Args:
            soup (BeautifulSoup): Parsed HTML content
            page_url (str): URL of the search page
        
        Returns:
            List[Dict]: Validated job listings
        """
        jobs = []
        
        try:
            # Advanced job detection strategies
            job_detection_strategies = [
                {
                    'selectors': [
                        # Specific job-related HTML elements and classes
                        {'tag': 'div', 'class_filter': lambda x: x and any(term in x.lower() for term in [
                            'job-item', 'job-result', 'job-card', 'job-listing', 
                            'stellenanzeige', 'job-entry', 'job-preview'
                        ])},
                        {'tag': 'article', 'class_filter': lambda x: x and any(term in x.lower() for term in [
                            'job', 'stelle', 'position', 'anzeige'
                        ])},
                        {'tag': 'li', 'class_filter': lambda x: x and any(term in x.lower() for term in [
                            'job', 'stelle', 'position'
                        ])}
                    ],
                    'validators': [
                        # Strong job-related keyword validation
                        lambda text: sum(
                            text.lower().count(keyword) for keyword in [
                                'entwickler', 'developer', 'engineer', 'programmierer', 
                                'it', 'software', 'job', 'stelle', 'position', 
                                'mitarbeiter', 'vollzeit', 'teilzeit', 'remote',
                                'softwareentwickler', 'ingenieur', 'projektleiter',
                                'recruiter', 'consultant', 'analyst', 'administrator'
                            ]
                        ) >= 2,
                        
                        # Exclude navigation and non-job content
                        lambda text: not any(nav_term in text.lower() for nav_term in [
                            'seite', 'weiter', 'zurück', 'navigation', 'filter', 
                            'sortieren', 'vorschläge', 'jobs suchen', 
                            'alle anzeigen', 'mehr anzeigen', 'finde deinen job',
                            'mitarbeiterrabatte', 'mitarbeiterangebote', 
                            'sorgfältige einarbeitung', 'mitarbeiter-events',
                            'vereinbarkeit', 'mobiles arbeiten', 'job-rad'
                        ]),
                        
                        # Meaningful content length and structure
                        lambda text: (
                            100 < len(text) < 1000 and  # Reasonable text length
                            any(marker in text.lower() for marker in ['(m/w/d)', '(w/m/d)'])  # Job posting markers
                        )
                    ]
                }
            ]
            
            # Comprehensive job card detection
            job_cards = []
            for strategy in job_detection_strategies:
                for selector in strategy['selectors']:
                    potential_cards = soup.find_all(
                        selector['tag'], 
                        class_=selector.get('class_filter')
                    )
                    
                    # Apply validation
                    valid_cards = [
                        card for card in potential_cards 
                        if all(
                            validator(card.get_text(strip=True)) 
                            for validator in strategy['validators']
                        )
                    ]
                    
                    if valid_cards:
                        job_cards = valid_cards
                        if self.debug:
                            print(f"   🎯 Found {len(valid_cards)} job cards using strategy")
                        break
                if job_cards:
                    break
            
            # Fallback for simpler structures
            if not job_cards:
                all_elements = soup.find_all(['div', 'article', 'li'])
                job_cards = [elem for elem in all_elements if elem.get_text() and any(keyword in elem.get_text().lower() for keyword in ['developer', 'engineer', 'administrator', 'manager', 'analyst'])]
                if self.debug:
                    print(f"   ⚠️ Using fallback extraction, found {len(job_cards)} potential job elements")

            for card in job_cards:
                try:
                    if isinstance(card, Tag):
                        job_data = self._parse_meinestadt_job_card(card, page_url)
                        if job_data:
                            jobs.append(job_data)
                except Exception as e:
                    if self.debug:
                        print(f"   ⚠️ Error parsing Meinestadt job card: {e}")
                    continue
                    
        except Exception as e:
            print(f"❌ Error extracting Meinestadt jobs: {e}")
        
        return jobs

    def _get_clean_text(self, element: Optional[Tag]) -> str:
        """Get clean text from a BeautifulSoup element."""
        return element.get_text(strip=True) if element else ""

    def _parse_meinestadt_job_card(self, card: Tag, page_url: str) -> Dict:
        """Parse individual MeineStadt.de job card."""
        
        title = self._get_clean_text(card.find(class_=lambda x: x and 'job-title' in x))
        company = self._get_clean_text(card.find(class_=lambda x: x and 'company' in x))
        location = self._get_clean_text(card.find(class_=lambda x: x and 'location' in x))
        
        link_element = card.find('a', href=True)
        job_url = ""
        if link_element and isinstance(link_element.get('href'), str):
            href = link_element.get('href', "")
            if href:
                job_url = urljoin(self.base_url, href)
        
        description = self._get_clean_text(card.find(class_=lambda x: x and 'job-description' in x))
        
        return {
            'title': title,
            'company': company,
            'location': location,
            'url': job_url,
            'description': description,
            'posted_date': ''
        }

    def fetch_job_details(self, job_url: str) -> Optional[Dict[str, Any]]:
        """Fetch detailed information for a single job from its URL."""
        try:
            # Import cache service
            try:
                from ..services.job_details_cache import job_details_cache
            except ImportError:
                from services.job_details_cache import job_details_cache

            # Try to get from cache first
            cached_details = job_details_cache.get_job_details_with_retry(job_url, max_retries=2, retry_delay=0.5)
            if cached_details:
                print(f"   ✅ Found cached job details for: {job_url}")
                return cached_details

            # Fetch from MeineStadt
            html_content = None
            error_info = None
            
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
                }
                response = self.get_page(job_url, headers=headers, timeout=30)
                if response and response.status_code == 200:
                    html_content = response.text
                else:
                    error_info = f"HTTP {response.status_code}" if response else 'No response'
                    print(f"   ❌ Failed to fetch MeineStadt job details: {job_url} (Status: {response.status_code})")

            except Exception as e:
                error_info = f"Request error: {str(e)}"
                print(f"   ❌ Error fetching MeineStadt job details for {job_url}: {e}")

            # Parse and extract details
            job_details = {}
            
            if html_content:
                try:
                    soup = BeautifulSoup(html_content, 'html.parser')
                    
                    # Extract job title
                    title_elem = soup.find('h1') or soup.find('title')
                    if title_elem:
                        job_details['title'] = title_elem.get_text(strip=True)
                    
                    # Extract company name
                    company_selectors = [
                        '.company-name',
                        '.employer-name',
                        'span[class*="company"]',
                        'div[class*="company"]'
                    ]
                    for selector in company_selectors:
                        company_elem = soup.select_one(selector)
                        if company_elem:
                            job_details['company'] = company_elem.get_text(strip=True)
                            break
                    
                    # Extract location
                    location_selectors = [
                        '.job-location',
                        '.location',
                        'span[class*="location"]',
                        'div[class*="location"]'
                    ]
                    for selector in location_selectors:
                        location_elem = soup.select_one(selector)
                        if location_elem:
                            job_details['location'] = location_elem.get_text(strip=True)
                            break
                    
                    # Extract job description
                    description_container = soup.find('div', id='job-description')
                    if description_container:
                        raw_description = description_container.get_text('\n').strip()
                        job_details['description'] = self._clean_text(raw_description)
                    
                    # Extract salary if available
                    salary_selectors = [
                        '.salary',
                        '.compensation',
                        'span[class*="salary"]',
                        'div[class*="salary"]'
                    ]
                    for selector in salary_selectors:
                        salary_elem = soup.select_one(selector)
                        if salary_elem:
                            job_details['salary'] = salary_elem.get_text(strip=True)
                            break
                    
                    # Add metadata
                    job_details['source'] = 'MeineStadt.de'
                    job_details['scraped_date'] = datetime.now()
                    job_details['url'] = job_url
                    
                    print(f"   ✅ Successfully extracted job details from MeineStadt")
                    
                except Exception as e:
                    error_info = f"Parsing error: {str(e)}"
                    print(f"   ❌ Error parsing MeineStadt job details: {e}")
            
            # Always cache the result (success or error)
            try:
                if job_details:
                    # Cache successful result
                    job_details_cache.cache_job_details(job_url, job_details)
                    print(f"   💾 Cached job details for: {job_url}")
                else:
                    # Cache error information
                    error_details = {
                        'error': True,
                        'error_message': error_info or 'Unknown error',
                        'source': 'MeineStadt.de',
                        'scraped_date': datetime.now(),
                        'url': job_url
                    }
                    job_details_cache.cache_job_details(job_url, error_details)
                    print(f"   💾 Cached error details for: {job_url}")
            except Exception as e:
                print(f"   ⚠️ Failed to cache job details: {e}")
            
            return job_details if job_details else None

        except Exception as e:
            print(f"   ⚠️ Unexpected error in fetch_job_details for {job_url}: {e}")
            return None 

    def _is_valid_job_listing(self, job: Dict) -> bool:
        """Validate if a scraped item is a valid job listing."""
        # Basic validation: must have a title and URL
        if not job.get('title') or not job.get('url'):
            return False
            
        # Add more sophisticated checks if needed
        # e.g., check for keywords, filter out ads, etc.
        
        return True 