"""
StepStone Job Scraper

Handles all StepStone-specific job scraping functionality.
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


class StepStoneScraper(BaseScraper):
    """StepStone-specific job scraper with enhanced extraction."""
    
    def __init__(self, debug: bool = False, use_flaresolverr: bool = False):
        """
        Initialize StepStone scraper.
        
        Args:
            debug: Enable debug logging
            use_flaresolverr: Use FlareSolverr for requests
        """
        super().__init__(debug, use_flaresolverr=use_flaresolverr)
        self.base_url = 'https://www.stepstone.de'
        self._current_search_location = ""
    
    def get_platform_name(self) -> str:
        """Return the platform name."""
        return "StepStone"
    
    def search_jobs(self, keywords: str, location: str = "", max_pages: int = 3, 
                   english_only: bool = False, **kwargs) -> List[Dict]:
        """
        Search StepStone for jobs using enhanced web scraping.
        
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
                print(f"\n--- Searching StepStone.com for: '{keyword}' ---")
                # Store current search location for fallback in parsing
                self._current_search_location = location
                
                for page in range(1, max_pages + 1):
                    # Build StepStone search URL using new format
                    # Convert keyword to URL-friendly format (replace spaces with hyphens)
                    keyword_slug = keyword.replace(' ', '-').lower()
                    
                    # Base URL with keyword slug
                    base_search_url = f"{self.base_url}/jobs/{keyword_slug}"
                    
                    # Add sorting and action parameters
                    params = {
                        'sort': '2',
                        'action': 'sort_publish'
                    }
                    
                    # Handle remote jobs specially for StepStone
                    if location and location.lower() == "remote":
                        # For remote jobs, use Germany as location but add remote filter
                        params['location'] = "germany"
                        params['wfh'] = '1'  # Work from home filter
                        params['radius'] = '30'
                        if english_only:
                            params['fdl'] = 'en'
                            # Use raw string for action parameter to avoid double encoding
                            search_url = f"{base_search_url}?sort=2&action=sort_publish&location=germany&wfh=1&radius=30&action=facet_selected%3bdetectedLanguages%3ben&fdl=en"
                        else:
                            # Use raw string for action parameter to avoid double encoding
                            search_url = f"{base_search_url}?sort=2&action=sort_publish&location=germany&wfh=1&radius=30&action=facet_selected%3bworkFromHome%3b1"
                    else:
                        if location:
                            params['location'] = location
                        if english_only:
                            params['fdl'] = 'en'
                        
                        # Add pagination if not first page
                        if page > 1:
                            params['page'] = page
                        
                        search_url = f"{base_search_url}?{urlencode(params)}"
                    
                    print(f"📄 Fetching StepStone page {page} for '{keyword}'")
                    
                    response = self.get_page(search_url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'}, timeout=30)
                    
                    page_jobs = []
                    if response and response.status_code == 200:
                        soup = self.get_soup(response.text)
                        if soup:
                            page_jobs = self._extract_stepstone_jobs(soup, search_url)
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
            print(f"❌ Error during StepStone search: {e}")
        
        # Deduplicate results
        seen_urls = set()
        unique_jobs = []
        for job in all_jobs:
            if (job_url := job.get('url')) and job_url not in seen_urls:
                unique_jobs.append(job)
                seen_urls.add(job_url)

        print(f"\n🎯 Total unique StepStone jobs found: {len(unique_jobs)}")
        return unique_jobs

    def _extract_stepstone_jobs(self, soup: BeautifulSoup, page_url: str) -> List[Dict]:
        """Extract job listings from StepStone search results with enhanced selectors."""
        jobs = []
        
        try:
            # Enhanced StepStone job cards selectors - try multiple patterns
            job_cards = []
            
            # Try specific StepStone selectors first
            patterns = [
                {'tag': ['article'], 'attr': 'data-testid', 'value': 'job-item'},
                {'tag': ['div'], 'class': ['job-element', 'job-item', 'listing']},
                {'tag': ['article', 'div'], 'class': lambda x: x and any(term in x.lower() for term in ['job', 'result', 'listing', 'card'])},
                {'tag': ['li'], 'class': lambda x: x and 'job' in x.lower()},
                # Fallback: look for any element with job-related attributes
                {'tag': ['*'], 'attr': lambda name, value: name and 'job' in name.lower()},
            ]
            
            for pattern in patterns:
                if 'attr' in pattern and pattern['attr'] != 'class':
                    if callable(pattern['attr']):
                        # Custom attribute search
                        cards = soup.find_all(lambda tag: any(pattern['attr'](attr, value) for attr, value in tag.attrs.items() if attr and value))
                    else:
                        # Specific attribute search
                        cards = soup.find_all(pattern['tag'], attrs={pattern['attr']: pattern['value']})
                else:
                    # Class-based search
                    cards = soup.find_all(pattern['tag'], class_=pattern['class'])
                
                if cards:
                    job_cards = cards
                    if self.debug:
                        print(f"   🎯 Found {len(cards)} job cards using pattern: {pattern}")
                    break
            
            if not job_cards and self.debug:
                print("   ⚠️ No job cards found with any pattern, trying emergency fallback")
                # Emergency fallback: look for any elements with job-related text
                all_elements = soup.find_all(['div', 'article', 'li'])
                job_cards = [elem for elem in all_elements if elem.get_text() and any(keyword in elem.get_text().lower() for keyword in ['developer', 'engineer', 'administrator', 'manager', 'analyst'])]
            
            for card in job_cards:
                try:
                    if isinstance(card, Tag):
                        job_data = self._parse_stepstone_job_card(card, page_url)
                        if job_data and job_data.get('title'):
                            jobs.append(job_data)
                except Exception as e:
                    if self.debug:
                        print(f"   ⚠️ Error parsing StepStone job card: {e}")
                    continue
                    
        except Exception as e:
            print(f"❌ Error extracting StepStone jobs: {e}")
        
        return jobs

    def _parse_stepstone_job_card(self, card: Tag, page_url: str) -> Dict:
        """
        Parse individual StepStone job card with a resilient, multi-strategy approach.
        """
        try:
            job_data = {}
            
            # --- 1. Resilient URL and Title Extraction ---
            job_url = ""
            title = ""
        
            # Strategy A: The most specific selector
            link_element = card.find('a', attrs={'data-testid': 'job-item-title'})
        
            # Strategy B: Find the title heading and get its parent link
            if not link_element:
                title_heading = card.find(['h2', 'h3'])
                if title_heading:
                    link_element = title_heading.find_parent('a')

            # Strategy C: Find any link that looks like a job link (fallback)
            if not link_element:
                # Look for StepStone job URLs (stellenangebote pattern)
                link_element = card.find('a', href=re.compile(r'/stellenangebote'))
                
            # Strategy D: Find any link that looks like a job link (general fallback)
            if not link_element:
                link_element = card.find('a', href=re.compile(r'/jobs/'))

            # Process the found link_element
            if link_element and isinstance(link_element, Tag):
                title = link_element.get_text(strip=True)
                href = link_element.get('href', '')
                if href and isinstance(href, str):
                     job_url = urljoin(self.base_url, href)

            # --- 2. Company Extraction (URL-First Strategy) ---
            company = ""
            
            # Primary Strategy: Extract company directly from the URL slug.
            if job_url:
                match = re.search(r'/cmp/de/([^/?]+)', job_url)
                if match:
                    company_slug = match.group(1)
                    company_slug_cleaned = re.sub(r'-\d+$', '', company_slug)
                    company_name = company_slug_cleaned.replace('-', ' ').replace('_', ' ')
                    company = ' '.join(word.capitalize() for word in company_name.split())

            # Fallback Strategy: If URL parsing fails, search the HTML.
            if not company:
                # Try multiple selectors for company name
                company_selectors = [
                    {'span': {'data-testid': 'job-item-company-name'}},
                    {'span': {'data-at': 'job-item-company-name'}},
                    {'span': {'data-genesis-element': 'TEXT'}},  # Look for text elements
                ]
                
                for selector in company_selectors:
                    for tag, attrs in selector.items():
                        company_element = card.find(tag, attrs=attrs)
                        if company_element:
                            company_text = company_element.get_text(strip=True)
                            # Check if this looks like a company name (not empty, reasonable length)
                            if company_text and len(company_text) > 2 and len(company_text) < 100:
                                company = company_text
                                break
                    if company:
                        break
                
                # Additional company extraction with class-based search
                if not company:
                    company_elements = card.find_all('span', class_=True)
                    for element in company_elements:
                        classes = element.get('class', [])
                        if any('company' in str(cls).lower() for cls in classes):
                            company_text = element.get_text(strip=True)
                            if company_text and len(company_text) > 2 and len(company_text) < 100:
                                company = company_text
                                break

                # --- 3. Other Details (Location, Salary, etc.) ---
                location = ""
                salary = ""
                description = ""
                
                # Extract location
                location_selectors = [
                    {'span': {'data-at': 'job-item-location'}},
                    {'span': {'data-testid': 'job-item-location'}},
                ]
                
                for selector in location_selectors:
                    for tag, attrs in selector.items():
                        location_element = card.find(tag, attrs=attrs)
                        if location_element:
                            location_text = location_element.get_text(strip=True)
                            if location_text and len(location_text) > 1:
                                location = location_text
                                break
                    if location:
                        break
                
                # Additional location extraction with class-based search
                if not location:
                    location_elements = card.find_all('span', class_=True)
                    for element in location_elements:
                        classes = element.get('class', [])
                        if any('location' in str(cls).lower() for cls in classes):
                            location_text = element.get_text(strip=True)
                            if location_text and len(location_text) > 1:
                                location = location_text
                                break
                
                # --- PRIORITY 1: Enhanced Salary Extraction from Job Card ---
                salary = ""
                
                # Strategy 1: Find elements specifically marked for salary
                salary_element = card.find(attrs={'data-testid': 'job-item-salary-info'})
                
                # Strategy 2: Find any element that contains a euro sign and looks like a salary
                if not salary_element:
                    # This regex looks for a number followed by a space and the euro symbol
                    salary_element = card.find(text=re.compile(r'\d+\s*€'))
                
                # Strategy 3: Look for salary button with dynamic class names
                if not salary_element:
                    salary_button = card.find('button', {'data-at': 'login-registration-salary-popover-on-jobItem'})
                    if salary_button:
                        # Look for the text inside the button
                        salary_text_span = salary_button.find('span', class_=True)
                        if salary_text_span:
                            classes = salary_text_span.get('class', [])
                            if any('kyg8or' in str(cls) for cls in classes):
                                salary = salary_text_span.get_text(strip=True)
                
                # Strategy 4: Use multiple selectors for salary
                if not salary_element:
                    salary_selectors = [
                        {'button': {'data-at': 'login-registration-salary-popover-on-jobItem'}},
                        {'span': {'data-at': 'job-item-salary'}},
                        {'span': {'data-testid': 'job-item-salary'}},
                    ]
                    
                    for selector in salary_selectors:
                        for tag, attrs in selector.items():
                            salary_element = card.find(tag, attrs=attrs)
                            if salary_element:
                                salary_text = salary_element.get_text(strip=True)
                                if salary_text and len(salary_text) > 1:
                                    salary = salary_text
                                    break
                        if salary:
                            break
                
                # Strategy 5: Additional salary extraction with class-based search
                if not salary_element:
                    salary_elements = card.find_all('span', class_=True)
                    for element in salary_elements:
                        classes = element.get('class', [])
                        if any('kyg8or' in str(cls) for cls in classes):
                            salary_text = element.get_text(strip=True)
                            if salary_text and len(salary_text) > 1:
                                salary = salary_text
                                break
                
                # Clean up the extracted salary to remove extra text if necessary
                if salary:
                    if "bis zu" in salary.lower() or "up to" in salary.lower():
                        # Example: "Bis zu 65.000 €" -> "65.000 €"
                        match = re.search(r'(\d[\d.,]*\s*€)', salary)
                        if match:
                            salary = match.group(1)
                    elif "ab" in salary.lower() or "from" in salary.lower():
                        # Example: "Ab 45.000 €" -> "45.000 €"
                        match = re.search(r'(\d[\d.,]*\s*€)', salary)
                        if match:
                            salary = match.group(1)
                
                if salary and self.debug:
                    print(f"   💰 Found salary in job card: '{salary}'")

                # Enhanced description extraction from job card
                description = self._extract_description_from_card(card)

                return {
                    'title': title,
                    'company': company,
                    'location': location,
                    'salary': salary,
                    'url': job_url,
                    'source': 'StepStone',
                    'description': description,
                    'scraped_date': datetime.now(),
                    'posted_date': "",
                    'language': self._detect_language_sophisticated(title, description)
                }
                
        except Exception as e:
            if self.debug:
                print(f"   ⚠️ Error parsing StepStone job card: {e}")
            return {}

    def _extract_with_selectors(self, card: BeautifulSoup, selectors: List[Dict]) -> str:
        """Extract text using multiple selector strategies."""
        for selector in selectors:
            try:
                if 'tags' in selector:
                    element = card.find(selector['tags'], class_=selector.get('class'))
                elif 'attrs' in selector:
                    for attr_name, attr_value in selector['attrs'].items():
                        if callable(attr_value):
                            element = card.find(attrs={attr_name: attr_value})
                        else:
                            element = card.find(attrs={attr_name: attr_value})
                        if element:
                            break
                    else:
                        continue
                else:
                    continue
                
                if element:
                    return element.get_text(strip=True)
            except:
                continue
        
        return ""

    def _extract_text_by_priority(self, card: BeautifulSoup, tags: List[str]) -> str:
        """Extract text from first available tag in priority order."""
        for tag in tags:
            element = card.find(tag)
            if element:
                return element.get_text(strip=True)
        return ""

    def _extract_description_from_card(self, card: BeautifulSoup) -> str:
        """Extract description from job card during search results parsing."""
        
        # StepStone job card description selectors
        description_selectors = [
            # StepStone-specific card selectors
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
            
            # Data attributes
            '[data-testid*="description"]',
            '[data-at*="description"]',
            '[data-genesis-element="TEXT"]',
            
            # Generic content
            'p',
            'div'
        ]
        
        best_description = ""
        max_length = 0
        
        for selector in description_selectors:
            try:
                elements = card.select(selector)
                for element in elements:
                    # Skip navigation and unwanted elements
                    if self._is_content_element(element):
                        text = self._clean_description_text(element.get_text(separator='\n', strip=True))
                        if text and len(text) > 20:  # Reasonable length for card descriptions
                            if len(text) > max_length:
                                best_description = text
                                max_length = len(text)
            except Exception:
                continue
        
        return best_description or ""

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
        
        # Priority 1: JSON-LD structured data (already handled above)
        # Priority 2: Common StepStone description containers
        description_selectors = [
            # StepStone-specific selectors
            'div[class*="job-description"]',
            'div[class*="listing-content"]',
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
            
            # Specific StepStone patterns
            'div[class*="kyg8or"]',  # StepStone's dynamic class
            'div[class*="css-"]',    # CSS modules
            'div[class*="sc-"]',     # Styled components
            
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

    def fetch_job_details(self, job_url: str) -> Optional[Dict[str, Any]]:
        """Fetch detailed information for a single job from its URL."""
        try:
            # Import cache service
            try:
                from ..services.job_details_cache import job_details_cache
            except ImportError:
                from services.job_details_cache import job_details_cache
            
            # Check cache first
            cached_details = job_details_cache.get_job_details_with_retry(job_url, max_retries=2, retry_delay=0.5)
            if cached_details:
                print(f"   📋 Using cached job details for: {job_url}")
                return cached_details
            
            # If not in cache, fetch fresh data
            print(f"   🔄 Fetching fresh job details for: {job_url}")
            
            html_content = None
            
            # Enhanced headers for StepStone to avoid blocking
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
            
            response = self.get_page(job_url, headers=headers, timeout=30)
            if response and response.status_code == 200:
                html_content = response.text
            else:
                status_code = response.status_code if response else 'N/A'
                error_msg = f"HTTP {status_code} error for job details: {job_url}"
                print(f"   ❌ {error_msg}")
                
                # For StepStone, we'll skip deep scraping and use search result data
                # since many job detail pages are blocked
                print(f"   ⚠️ StepStone job details often blocked - using search result data")
                
                # Cache the failure with comprehensive details
                error_details = {
                    "title": f"Error - HTTP {status_code}",
                    "company": "Unknown",
                    "location": "Unknown",
                    "salary": "",
                    "description": f"Failed to fetch job details: HTTP {status_code} error. StepStone job detail pages are often blocked by anti-bot protection.",
                    "requirements": "",
                    "benefits": "",
                    "contact_info": "",
                    "application_url": "",
                    "external_url": job_url,
                    "html_content": "",
                    "scraped_date": datetime.now(),
                    "last_accessed": datetime.now()
                }
                
                success = job_details_cache.cache_job_details(job_url, error_details, is_valid=False, error_message=error_msg)
                if success:
                    print(f"   💾 Cached HTTP error for: {job_url}")
                else:
                    print(f"   ❌ Failed to cache HTTP error for: {job_url}")
                    
                return None

            if not html_content:
                error_msg = "No HTML content received for job details"
                print(f"   ❌ {error_msg}")
                
                # Cache the failure with comprehensive details
                error_details = {
                    "title": "Error - No Content",
                    "company": "Unknown",
                    "location": "Unknown",
                    "salary": "",
                    "description": "Failed to fetch job details: No HTML content received",
                    "requirements": "",
                    "benefits": "",
                    "contact_info": "",
                    "application_url": "",
                    "external_url": job_url,
                    "html_content": "",
                    "scraped_date": datetime.now(),
                    "last_accessed": datetime.now()
                }
                
                success = job_details_cache.cache_job_details(job_url, error_details, is_valid=False, error_message=error_msg)
                if success:
                    print(f"   💾 Cached no-content error for: {job_url}")
                else:
                    print(f"   ❌ Failed to cache no-content error for: {job_url}")
                
                return None

            soup = BeautifulSoup(html_content, 'html.parser')

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
            
            # StepStone uses a script tag with JSON-LD, which is a good source
            script_tag = soup.find('script', type='application/ld+json')
            if script_tag:
                import json
                try:
                    json_data = json.loads(script_tag.string)
                    title = json_data.get('title', '')
                    company = json_data.get('hiringOrganization', {}).get('name', '')
                    location = json_data.get('jobLocation', {}).get('address', {}).get('addressLocality', '')
                    description_html = json_data.get('description', '')
                    # Convert HTML description to plain text
                    desc_soup = self.get_soup(description_html)
                    description = desc_soup.get_text(separator='\\n', strip=True) if desc_soup else ''
                    
                    # --- PRIORITY 2: Enhanced Salary Extraction from JSON-LD ---
                    base_salary_info = json_data.get('baseSalary', {})
                    if base_salary_info:
                        value_info = base_salary_info.get('value', {})
                        min_value = value_info.get('minValue')
                        max_value = value_info.get('maxValue')
                        unit = value_info.get('unitText', 'year').lower() # Default to 'year'

                        if min_value and max_value:
                            salary = f"{min_value} - {max_value} € per {unit}"
                        elif max_value:
                            salary = f"Up to {max_value} € per {unit}"
                        elif min_value:
                            salary = f"From {min_value} € per {unit}"
                    
                    print(f"   ✅ Extracted data from JSON-LD: title='{title[:50]}...', company='{company}', location='{location}', salary='{salary}'")
                    if salary and self.debug:
                        print(f"   💰 Found salary in JSON-LD: '{salary}'")
                except json.JSONDecodeError as e:
                    print(f"   ⚠️ Failed to parse JSON-LD: {e}")
            
            # Enhanced fallback extraction with comprehensive HTML pattern matching
            if not title:
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
            
            # --- PRIORITY 3: Fallback Salary Extraction from HTML ---
            if not salary:
                # Look for salary information in the HTML content
                salary_selectors = [
                    '[data-testid*="salary"]',
                    '[data-at*="salary"]',
                    '[class*="salary"]',
                    '[class*="compensation"]',
                    'span:contains("€")',
                    'div:contains("€")',
                    'p:contains("€")'
                ]
                
                for selector in salary_selectors:
                    try:
                        elements = soup.select(selector)
                        for element in elements:
                            text = element.get_text(strip=True)
                            # Look for patterns that indicate salary information
                            if re.search(r'\d[\d.,]*\s*€', text):
                                salary = text
                                break
                        if salary:
                            break
                    except Exception:
                        continue
                
                # Additional regex-based salary extraction
                if not salary:
                    # Search for salary patterns in the entire HTML
                    salary_patterns = [
                        r'\d[\d.,]*\s*€\s*pro\s*jahr',  # German: per year
                        r'\d[\d.,]*\s*€\s*per\s*year',   # English: per year
                        r'\d[\d.,]*\s*€\s*pro\s*monat',  # German: per month
                        r'\d[\d.,]*\s*€\s*per\s*month',  # English: per month
                        r'\d[\d.,]*\s*€',                # Just euro amounts
                        r'bis zu\s*\d[\d.,]*\s*€',       # Up to amount
                        r'ab\s*\d[\d.,]*\s*€',           # From amount
                    ]
                    
                    html_text = soup.get_text()
                    for pattern in salary_patterns:
                        match = re.search(pattern, html_text, re.IGNORECASE)
                        if match:
                            salary = match.group(0)
                            break
                
                if salary and self.debug:
                    print(f"   💰 Found salary in HTML fallback: '{salary}'")
            
            if not company:
                company_selectors = [
                    'span[class*="company"]',
                    'div[class*="company"]',
                    '[data-testid*="company"]',
                    '[data-at*="company"]',
                    '[class*="employer"]',
                    '[class*="organization"]',
                    'a[href*="/company/"]',
                    'a[href*="/cmp/"]'
                ]
                company = self._extract_with_multiple_selectors(soup, company_selectors) or "Unknown Company"
            
            if not location:
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
            
            # Enhanced description extraction with comprehensive HTML pattern matching
            if not description:
                description = self._extract_comprehensive_description(soup)
            
            # Create comprehensive details dictionary with all required fields
            details = {
                "title": title or "Unknown Title",
                "company": company or "Unknown Company", 
                "location": location or "Unknown Location",
                "salary": salary or "",
                "description": description or "No description available",
                "requirements": requirements or "",
                "benefits": benefits or "",
                "contact_info": contact_info or "",
                "application_url": application_url or "",
                "external_url": external_url or job_url,
                "html_content": html_content,
                "scraped_date": datetime.now(),
                "last_accessed": datetime.now()
            }
            
            # Cache the details with comprehensive information
            print(f"   💾 Caching comprehensive job details for: {job_url}")
            print(f"   📋 Title: {title[:50]}...")
            print(f"   🏭 Company: {company}")
            print(f"   📍 Location: {location}")
            
            success = job_details_cache.cache_job_details(job_url, details)
            if success:
                print(f"   ✅ Successfully cached job details")
            else:
                print(f"   ❌ Failed to cache job details")
            
            return details

        except Exception as e:
            error_msg = f"Error fetching StepStone job details for {job_url}: {e}"
            if self.debug:
                print(f"   ❌ {error_msg}")
            
            # Cache the error with comprehensive details
            try:
                try:
                    from ..services.job_details_cache import job_details_cache
                except ImportError:
                    from services.job_details_cache import job_details_cache
                error_details = {
                    "title": "Error - Job Unavailable",
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
                
                # Cache as invalid with error message
                success = job_details_cache.cache_job_details(job_url, error_details, is_valid=False, error_message=error_msg)
                if success:
                    print(f"   💾 Cached error details for: {job_url}")
                else:
                    print(f"   ❌ Failed to cache error details for: {job_url}")
                    
            except Exception as cache_error:
                print(f"   ❌ Failed to cache error: {cache_error}")
            
            return None 