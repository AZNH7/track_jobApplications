"""
Monster.de Job Scraper

Handles all Monster.de-specific job scraping functionality.
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
    from .browser_automation import BrowserAutomation
except ImportError:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from base_scraper import BaseScraper


class MonsterScraper(BaseScraper):
    """Monster.de-specific job scraper with international reach."""
    
    def __init__(self, debug: bool = False, use_flaresolverr: bool = False):
        """
        Initialize Monster.de scraper.
        
        Args:
            debug: Enable debug logging
            use_flaresolverr: Use FlareSolverr for requests
        """
        super().__init__(debug, use_flaresolverr)
        self.base_url = 'https://www.monster.de'
        self._current_search_location = ""
        
        # Enhanced stealth headers
        self._stealth_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7',
        }
        
        # Browser automation for DataDome CAPTCHA
        self.browser_automation = None
        self.use_browser_automation = True
    
    def _initialize_session(self):
        """Initialize session with stealth features."""
        # This method is now handled by the BaseScraper's cloudscraper session
        pass

    def get_soup(self, html_content: str) -> Optional[BeautifulSoup]:
        """Get BeautifulSoup object from HTML content."""
        if not html_content:
            return None
        try:
            return BeautifulSoup(html_content, 'html.parser')
        except Exception as e:
            if self.debug:
                print(f"   ❌ Error creating BeautifulSoup object: {e}")
            return None

    def get_platform_name(self) -> str:
        """Return the platform name."""
        return "Monster.de"

    def _get_random_delay(self, base_delay: float = 15.0) -> float:
        """Get a random delay with human-like variation."""
        return base_delay * random.uniform(0.8, 1.2)

    def search_jobs(self, keywords: str, location: str = "", max_pages: int = 3, 
                   english_only: bool = False, **kwargs) -> List[Dict]:
        """
        Search Monster.de for jobs using web scraping with cloudscraper support.
        
        Args:
            keywords: Job search keywords
            location: Job location
            max_pages: Maximum number of pages to scrape
            english_only: Only return English language jobs
            
        Returns:
            List of job dictionaries
        """
        all_jobs = []
        
        keyword_list = [k.strip() for k in keywords.split(',') if k.strip()]
        if not keyword_list:
            keyword_list = [keywords]

        try:
            for keyword in keyword_list:
                print(f"\n--- Searching Monster.de for: '{keyword}' ---")
                self._current_search_location = location
                
                for page in range(1, max_pages + 1):
                    params = {
                        'q': keyword,
                        'where': location,
                        'page': page,
                        'lang': 'de' if not english_only else 'en'
                    }
                    
                    search_url = f"{self.base_url}/jobs/search?" + urlencode(params)
                    print(f"📄 Fetching Monster page {page} for '{keyword}'")
                    
                    page_jobs = []
                    response = self.get_page(search_url, headers=self._stealth_headers, timeout=30)

                    if response and response.status_code == 200:
                        soup = self.get_soup(response.text)
                        if soup:
                            page_jobs = self._extract_monster_jobs(soup, search_url)
                        else:
                            print(f"   ❌ Failed to parse HTML for page {page}")
                    elif response:
                        print(f"   ❌ HTTP {response.status_code} for page {page}")
                        if "datadome" in response.text.lower() or "captcha" in response.text.lower():
                            print(f"   🚫 DataDome CAPTCHA detected, trying browser automation...")
                            page_jobs = self._try_browser_automation(search_url)
                    else:
                        print(f"   ❌ Failed to fetch page {page}")


                    if page_jobs:
                        all_jobs.extend(page_jobs)
                        print(f"   Found {len(page_jobs)} jobs on page {page} for '{keyword}'")
                    else:
                        print("   ℹ️ No jobs found on this page, moving to next keyword or finishing.")
                        break
                    
                    time.sleep(self._get_random_delay())
        except Exception as e:
            print(f"❌ Error during Monster search: {e}")

        return all_jobs

    def _try_browser_automation(self, search_url: str) -> List[Dict]:
        """Try browser automation as a fallback for DataDome CAPTCHA."""
        if not self.use_browser_automation:
            print("   ⚠️ Browser automation disabled")
            return []
        
        try:
            if not self.browser_automation:
                # Set headless=False to allow manual CAPTCHA solving
                self.browser_automation = BrowserAutomation(debug=self.debug, headless=False)
            
            result = self.browser_automation.get_page_with_browser(search_url, max_wait=60)
            
            if result and result.get("status") == "ok":
                html_content = result.get("solution", {}).get("response", "")
                soup = self.get_soup(html_content)
                if soup:
                    return self._extract_monster_jobs(soup, search_url)
            else:
                print(f"   ❌ Browser automation failed: {result.get('message', 'Unknown error') if result else 'No response'}")
                
        except Exception as e:
            print(f"   ❌ Browser automation error: {e}")
        return []

    def _extract_monster_jobs(self, soup: BeautifulSoup, page_url: str) -> List[Dict]:
        """Extract job details from a Monster.de search results page."""
        job_cards = soup.select('div.job-cardstyle__JobCardComponent-sc-1mbmxes-0')
        jobs = []
        for card in job_cards:
            job = self._parse_monster_job_card(card, page_url)
            if job:
                jobs.append(job)
        return jobs

    def _detect_language_sophisticated(self, title: str, description: str) -> str:
        """Detect language with a more sophisticated approach, defaulting to German for Monster.de."""
        if not description: return "de"
        
        german_keywords = ['stellenbeschreibung', 'profil', 'wir bieten', 'aufgaben']
        english_keywords = ['description', 'profile', 'we offer', 'responsibilities']
        
        desc_lower = description.lower()
        
        german_score = sum(1 for keyword in german_keywords if keyword in desc_lower)
        english_score = sum(1 for keyword in english_keywords if keyword in desc_lower)
        
        if english_score > german_score:
            return "en"
        return "de"

    def _parse_monster_job_card(self, card: Tag, page_url: str) -> Optional[Dict]:
        """Parse a single job card from Monster.de search results."""
        try:
            title_element = card.select_one('h2.job-cardstyle__JobCardTitle-sc-1mbmxes-3')
            company_element = card.select_one('div.job-cardstyle__JobCardCompany-sc-1mbmxes-4')
            location_element = card.select_one('div.job-cardstyle__JobCardLocation-sc-1mbmxes-5')
            
            title = title_element.text.strip() if title_element else "N/A"
            company = company_element.text.strip() if company_element else "N/A"
            location = location_element.text.strip() if location_element else "N/A"
            
            link_element = card.select_one('a.job-cardstyle__JobCardTitleLink-sc-1mbmxes-7')
            job_url_raw = link_element['href'] if link_element else None
            job_url = None
            
            if isinstance(job_url_raw, str):
                job_url = urljoin(self.base_url, job_url_raw)

            description = "Description fetched separately"
            language = self._detect_language_sophisticated(title, "")

            return {
                'title': title,
                'company': company,
                'location': location,
                'job_url': job_url,
                'platform': self.get_platform_name(),
                'description': description,
                'language': language,
                'posted_date': datetime.now().strftime('%Y-%m-%d'),
                'salary': 'Not specified',
                'job_type': 'Not specified'
            }
        except Exception as e:
            if self.debug:
                print(f"   ❌ Error parsing Monster job card: {e}")
            return None

    def fetch_job_details(self, job_url: str) -> Optional[Dict[str, Any]]:
        """Fetch detailed job information from a specific job URL."""
        if not job_url:
            return None
        
        print(f"   ↪️ Fetching details for: {job_url}")

        try:
            response = self.get_page(job_url, headers=self._stealth_headers, timeout=30)

            if response and response.status_code == 200:
                soup = self.get_soup(response.text)
                if soup:
                    description_container = soup.select_one('div.jobview-container') or \
                                            soup.select_one('div#JobDescription') or \
                                            soup.select_one('section#job-description')

                    if description_container:
                        description = description_container.get_text(separator='\n', strip=True)
                        language = self._detect_language_sophisticated("", description)
                        return {'description': description, 'language': language}
                    else:
                        print(f"      ⚠️ Description container not found on {job_url}. Structure may have changed.")
                        return {'description': "Could not parse description.", 'language': 'de'}
            elif response:
                print(f"      ❌ Failed to fetch job details. Status code: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Error fetching Monster job details for {job_url}: {e}")
            
        return None

    def close(self):
        """Close any open resources, like the browser instance."""
        if self.browser_automation:
            self.browser_automation.close() 