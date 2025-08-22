"""
Job Scraper Orchestrator

Main class that coordinates all job scrapers and provides the unified interface.
"""

import pandas as pd
import time
import random
from typing import List, Dict, Optional, Set, Union, Any
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import os

try:
    from .indeed_scraper import IndeedScraper
    from .linkedin_scraper import LinkedInScraper
    from .stepstone_scraper import StepStoneScraper
    from .xing_scraper import XingScraper
    from .stellenanzeigen_scraper import StellenanzeigenScraper
    from .meinestadt_scraper import MeinestadtScraper
    from .jobrapido_scraper import JobrapidoScraper
    from .base_scraper import BaseScraper
    from .utils import JobFilters
except ImportError:
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from indeed_scraper import IndeedScraper
    from linkedin_scraper import LinkedInScraper
    from stepstone_scraper import StepStoneScraper
    from xing_scraper import XingScraper
    from stellenanzeigen_scraper import StellenanzeigenScraper
    from meinestadt_scraper import MeinestadtScraper
    from jobrapido_scraper import JobrapidoScraper
    from base_scraper import BaseScraper
    from utils import JobFilters

try:
    from src.database.database_manager import get_db_manager
except ImportError:
    # Fallback for when these modules are not available
    def get_db_manager() -> Any:
        return None
    

class JobScraperOrchestrator:
    """
    Main orchestrator class that coordinates all job scrapers.
    """
    
    def __init__(self, debug: bool = False, config: Optional[Dict] = None, use_flaresolverr: bool = False):
        """
        Initialize the job scraper orchestrator.
        
        Args:
            debug: Enable debug logging
            config: Configuration dictionary
            use_flaresolverr: Enable FlareSolverr for bypassing bot detection
        """
        self.debug = debug
        self.config = config or self._load_default_config()
        self.use_flaresolverr = use_flaresolverr
        
        # Initialize scrapers
        self.scrapers = self._initialize_scrapers()
        

        
        # Initialize Ollama client for LLM assessment
        try:
            from src.ollama_client import ollama_client
            self.ollama_client = ollama_client
            if self.ollama_client.available:
                print(f"🤖 LLM Assessment: Enabled (Ollama available)")
            else:
                print(f"⚠️ LLM Assessment: Disabled (Ollama not available)")
        except Exception as e:
            print(f"⚠️ LLM Assessment: Disabled (Error initializing Ollama: {e})")
            self.ollama_client = None
        
        # Store current search keywords for LLM assessment
        self.current_search_keywords = []
        self.searched_location = ""  # Track the searched location for filtering
        
        print(f"🚀 Job Scraper Orchestrator initialized with {len(self.scrapers)} platforms")
        for scraper_name in self.scrapers.keys():
            print(f"   ✅ {scraper_name}")
    
    def _load_default_config(self) -> Dict:
        """Load default configuration."""
        return {
            'job_search': {
                'enable_indeed': True,
                'enable_linkedin': True,
                'enable_stepstone': True,
                'enable_xing': True,
                'enable_stellenanzeigen': True,
                'enable_meinestadt': True,
                'enable_jobrapido': True,
            },
            'search_settings': {
                'max_pages_per_platform': 3,
                'delay_between_requests': 2,
                'timeout': 30,
                'max_workers': 4
            }
        }
    
    def _initialize_scrapers(self) -> Dict[str, BaseScraper]:
        """Initialize all available scrapers."""
        scrapers = {}
        
        # Initialize each scraper based on configuration with platform-specific settings
        if self.config['job_search'].get('enable_indeed', True):
            indeed_use_flaresolverr = self.config.get('platform_settings', {}).get('indeed', {}).get('use_flaresolverr', self.use_flaresolverr)
            indeed_args = {'debug': self.debug, 'use_flaresolverr': indeed_use_flaresolverr}
            scrapers['Indeed'] = IndeedScraper(**indeed_args)
        
        if self.config['job_search'].get('enable_linkedin', True):
            linkedin_use_flaresolverr = self.config.get('platform_settings', {}).get('linkedin', {}).get('use_flaresolverr', self.use_flaresolverr)
            linkedin_args = {'debug': self.debug, 'use_flaresolverr': linkedin_use_flaresolverr}
            scrapers['LinkedIn'] = LinkedInScraper(**linkedin_args)
        
        if self.config['job_search'].get('enable_stepstone', True):
            stepstone_use_flaresolverr = self.config.get('platform_settings', {}).get('stepstone', {}).get('use_flaresolverr', self.use_flaresolverr)
            stepstone_args = {'debug': self.debug, 'use_flaresolverr': stepstone_use_flaresolverr}
            scrapers['StepStone'] = StepStoneScraper(**stepstone_args)
        
        if self.config['job_search'].get('enable_xing', True):
            xing_use_flaresolverr = self.config.get('platform_settings', {}).get('xing', {}).get('use_flaresolverr', self.use_flaresolverr)
            xing_args = {'debug': self.debug, 'use_flaresolverr': xing_use_flaresolverr}
            scrapers['Xing'] = XingScraper(**xing_args)
        
        if self.config['job_search'].get('enable_stellenanzeigen', True):
            stellenanzeigen_use_flaresolverr = self.config.get('platform_settings', {}).get('stellenanzeigen', {}).get('use_flaresolverr', self.use_flaresolverr)
            stellenanzeigen_args = {'debug': self.debug, 'use_flaresolverr': stellenanzeigen_use_flaresolverr}
            scrapers['Stellenanzeigen'] = StellenanzeigenScraper(**stellenanzeigen_args)
        
        if self.config['job_search'].get('enable_meinestadt', True):
            meinestadt_use_flaresolverr = self.config.get('platform_settings', {}).get('meinestadt', {}).get('use_flaresolverr', self.use_flaresolverr)
            meinestadt_args = {'debug': self.debug, 'use_flaresolverr': meinestadt_use_flaresolverr}
            scrapers['MeineStadt'] = MeinestadtScraper(**meinestadt_args)
        
        if self.config['job_search'].get('enable_jobrapido', True):
            jobrapido_use_flaresolverr = self.config.get('platform_settings', {}).get('jobrapido', {}).get('use_flaresolverr', self.use_flaresolverr)
            jobrapido_args = {'debug': self.debug, 'use_flaresolverr': jobrapido_use_flaresolverr}
            scrapers['Jobrapido'] = JobrapidoScraper(**jobrapido_args)
        
        return scrapers
    

    
    def search_all_platforms(self, keywords: Union[str, List[str]], location: str = "", 
                           max_pages: int = 2, english_only: bool = False, 
                           deep_scrape: bool = True) -> pd.DataFrame:
        """
        Search all enabled platforms for jobs.
        
        Args:
            keywords: Job search keywords (single string or list of job titles)
            location: Job location
            max_pages: Maximum pages per platform
            english_only: Only return English language jobs
            deep_scrape: Fetch full job details from each URL
            
        Returns:
            DataFrame with all found jobs
        """
        all_jobs = []
        
        # Ensure keywords is a list
        if isinstance(keywords, str):
            keywords = [keywords]
        
        # Store current search keywords for LLM assessment
        self.current_search_keywords = keywords
        
        # Set relevance threshold from config if available
        self.relevance_threshold = getattr(self, 'relevance_threshold', 5)
        
        print(f"🔍 Starting comprehensive job search...")
        print(f"   📝 Keywords: {keywords}")
        print(f"   📍 Location: {location or 'anywhere'}")
        print(f"   📄 Max pages per platform: {max_pages}")
        print(f"   🌐 Platforms: {len(self.scrapers)}")
        
        # Search each platform for each job title individually
        for job_title in keywords:
            print(f"\n🔍 Searching for job title: {job_title}")
            
            # Search each platform
            for platform_name, scraper in self.scrapers.items():
                try:
                    print(f"   🔍 Searching {platform_name}...")
                    start_time = time.time()
                    
                    # Search with individual job title
                    jobs = scraper.search_jobs(
                        keywords=job_title,
                        location=location,
                        max_pages=max_pages,
                        english_only=english_only
                    )
                    
                    # Add platform and search metadata
                    for job in jobs:
                        job['search_platform'] = platform_name
                        job['search_title'] = job_title
                    
                    # Extend all jobs list
                    all_jobs.extend(jobs)
                    
                    # Log search results
                    print(f"   ✅ Found {len(jobs)} jobs on {platform_name}")
                    print(f"   ⏱️ Search time: {time.time() - start_time:.2f} seconds")
                    
                except Exception as e:
                    print(f"   ❌ Error searching {platform_name}: {e}")
                    continue
        
        # Convert to DataFrame
        if not all_jobs:
            print("⚠️ No jobs found across all platforms.")
            return pd.DataFrame()
        
        # Create DataFrame
        df = pd.DataFrame(all_jobs)
        
        # Optional deep scraping
        if deep_scrape:
            print("\n🔍 Starting deep job details scraping...")
            df = self._process_jobs_dataframe(df, keywords)
        
        return df
    
    def search_selected_platforms(self, keywords: Union[str, List[str]], location: str = "", 
                                max_pages: int = 2, selected_platforms: Optional[List[str]] = None,
                                english_only: bool = False, deep_scrape: bool = True) -> pd.DataFrame:
        """
        Search only selected platforms for jobs.
        
        Args:
            keywords: Job search keywords
            location: Job location
            max_pages: Maximum pages per platform
            selected_platforms: List of platform names to search
            english_only: Only return English language jobs
            deep_scrape: Fetch full job details from each URL
            
        Returns:
            DataFrame with found jobs
        """
        if not selected_platforms:
            selected_platforms = list(self.scrapers.keys())
        
        # Store current search keywords for LLM assessment
        self.current_search_keywords = keywords if isinstance(keywords, list) else [keywords]
        
        all_jobs = []
        
        print(f"🔍 Starting targeted job search...")
        print(f"   📝 Keywords: {keywords}")
        print(f"   📍 Location: {location or 'anywhere'}")
        print(f"   📄 Max pages per platform: {max_pages}")
        print(f"   🎯 Selected platforms: {', '.join(selected_platforms)}")
        print(f"   🔍 English only: {english_only}")
        print(f"   🔍 Deep scrape: {deep_scrape}")

        print(f"   🔍 Scrapers: {self.scrapers}")
        print(f"   🔍 Job found: {all_jobs}")
        
        # Search selected platforms
        for platform_name in selected_platforms:
            # Handle case-insensitive platform matching
            scraper_key = None
            for key in self.scrapers.keys():
                if key.lower() == platform_name.lower():
                    scraper_key = key
                    break
            
            if scraper_key is None:
                print(f"⚠️ Platform '{platform_name}' not available")
                continue
            
            try:
                scraper = self.scrapers[scraper_key]
                print(f"\n🔍 Searching {scraper_key}...")
                start_time = time.time()
                
                platform_jobs = []
                
                # Convert keywords to list if it's a string
                keywords_list = keywords if isinstance(keywords, list) else [keywords]
                
                # Search title by title for better results
                for i, keyword in enumerate(keywords_list):
                    print(f"   📝 Searching for: '{keyword}' ({i+1}/{len(keywords_list)})")
                    
                    # Calculate pages per keyword to stay within max_pages limit
                    pages_per_keyword = max(1, max_pages // len(keywords_list))
                    
                    keyword_jobs = scraper.search_jobs(
                        keywords=keyword,
                        location=location,
                        max_pages=pages_per_keyword,
                        english_only=english_only
                    )
                    
                    # Add keyword info to jobs
                    for job in keyword_jobs:
                        job['search_keyword'] = keyword
                        job['platform'] = scraper_key.lower()  # Use lowercase for consistency
                    
                    platform_jobs.extend(keyword_jobs)
                    print(f"   ✅ Found {len(keyword_jobs)} jobs for '{keyword}'")
                    
                    # Add small delay between keywords to be respectful
                    if i < len(keywords_list) - 1:  # Don't delay after the last keyword
                        time.sleep(random.uniform(0.5, 1.5))
                
                elapsed_time = time.time() - start_time
                print(f"✅ {scraper_key}: {len(platform_jobs)} total jobs found in {elapsed_time:.1f}s")
                
                all_jobs.extend(platform_jobs)
                
                if deep_scrape:
                    self._fetch_details_for_jobs(platform_jobs, scraper)
                
                # Add delay between platforms
                delay = random.uniform(1, 3)
                time.sleep(delay)
                
            except Exception as e:
                print(f"❌ Error searching {scraper_key}: {e}")
                continue
        
        print(f"\n🎯 Total jobs found: {len(all_jobs)}")
        
        # Convert to DataFrame and process
        if all_jobs:
            df = pd.DataFrame(all_jobs)
            df = self._process_jobs_dataframe(df, keywords)
            
            # Debug: Search completion summary
            print(f"\n🎉 Targeted job search completed successfully!")
            print(f"   📊 Total jobs processed: {len(df)}")
            print(f"   📝 Search keywords: {keywords}")
            print(f"   📍 Search location: {location or 'anywhere'}")
            print(f"   🎯 Selected platforms: {', '.join(selected_platforms)}")
            print(f"   📄 Pages per platform: {max_pages}")
            print(f"   🔍 Deep scrape enabled: {deep_scrape}")
            print(f"   🌍 English only: {english_only}")
            
            # Platform breakdown
            if 'platform' in df.columns:
                platform_counts = df['platform'].value_counts()
                print(f"   📈 Jobs by platform:")
                for platform, count in platform_counts.items():
                    print(f"      - {platform}: {count} jobs")
            
            return df
        else:
            print(f"\n⚠️ Targeted job search completed - no jobs found")
            print(f"   📝 Search keywords: {keywords}")
            print(f"   📍 Search location: {location or 'anywhere'}")
            print(f"   🎯 Selected platforms: {', '.join(selected_platforms)}")
            return pd.DataFrame()
    
    def search_parallel(self, keywords: Union[str, List[str]], location: str = "", 
                       max_pages: int = 2, selected_platforms: Optional[List[str]] = None,
                       english_only: bool = False, max_workers: int = 4,
                       deep_scrape: bool = True) -> pd.DataFrame:
        """
        Search platforms in parallel for faster results.
        
        Args:
            keywords: Job search keywords
            location: Job location
            max_pages: Maximum pages per platform
            selected_platforms: List of platform names to search
            english_only: Only return English language jobs
            max_workers: Maximum number of parallel workers
            deep_scrape: Fetch full job details from each URL
            
        Returns:
            DataFrame with found jobs
        """
        if not selected_platforms:
            selected_platforms = list(self.scrapers.keys())
        
        # Store current search keywords for LLM assessment
        self.current_search_keywords = keywords if isinstance(keywords, list) else [keywords]
        
        all_jobs = []
        
        print(f"🔍 Starting parallel job search...")
        print(f"   📝 Keywords: {keywords}")
        print(f"   📍 Location: {location or 'anywhere'}")
        print(f"   📄 Max pages per platform: {max_pages}")
        print(f"   🎯 Selected platforms: {', '.join(selected_platforms)}")
        print(f"   ⚡ Parallel workers: {max_workers}")
        
        def search_platform(platform_name: str) -> List[Dict]:
            """Search a single platform."""
            scraper_key = None
            for key in self.scrapers.keys():
                if key.lower() == platform_name.lower():
                    scraper_key = key
                    break
            
            if not scraper_key:
                print(f"⚠️ Platform '{platform_name}' not available")
                return []

            try:
                print(f"\n🔍 Searching {scraper_key}...")
                start_time = time.time()
                
                platform_jobs = []
                
                # Convert keywords to list if it's a string
                keywords_list = keywords if isinstance(keywords, list) else [keywords]
                
                # Search title by title for better results
                for i, keyword in enumerate(keywords_list):
                    print(f"   📝 Searching for: '{keyword}' ({i+1}/{len(keywords_list)})")
                    
                    # Calculate pages per keyword to stay within max_pages limit
                    pages_per_keyword = max(1, max_pages // len(keywords_list))
                    
                    keyword_jobs = self.scrapers[scraper_key].search_jobs(
                        keywords=keyword,
                        location=location,
                        max_pages=pages_per_keyword,
                        english_only=english_only
                    )
                    
                    # Add keyword and platform info to jobs
                    for job in keyword_jobs:
                        job['search_keyword'] = keyword
                        job['platform'] = scraper_key
                    
                    platform_jobs.extend(keyword_jobs)
                    print(f"   ✅ Found {len(keyword_jobs)} jobs for '{keyword}'")
                    
                    # Add small delay between keywords to be respectful
                    if i < len(keywords_list) - 1:  # Don't delay after the last keyword
                        time.sleep(random.uniform(0.5, 1.5))
                
                elapsed_time = time.time() - start_time
                print(f"✅ {scraper_key}: {len(platform_jobs)} total jobs found in {elapsed_time:.1f}s")
                
                if deep_scrape:
                    self._fetch_details_for_jobs(platform_jobs, self.scrapers[scraper_key])

                return platform_jobs
                
            except Exception as e:
                print(f"❌ Error searching {scraper_key}: {e}")
                return []
        
        # Execute searches in parallel
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_platform = {
                executor.submit(search_platform, platform): platform 
                for platform in selected_platforms
            }
            
            for future in as_completed(future_to_platform):
                platform = future_to_platform[future]
                try:
                    jobs = future.result()
                    all_jobs.extend(jobs)
                except Exception as e:
                    print(f"❌ Platform {platform} generated an exception: {e}")
        
        print(f"\n🎯 Total jobs found: {len(all_jobs)}")
        
        # Convert to DataFrame and process
        if all_jobs:
            df = pd.DataFrame(all_jobs)
            df = self._process_jobs_dataframe(df, keywords)
            return df
        else:
            return pd.DataFrame()
    
    def search_optimized(self, keywords: Union[str, List[str]], location: str = "", 
                        max_pages: int = 2, selected_platforms: Optional[List[str]] = None,
                        english_only: bool = False, max_workers: int = 8,
                        deep_scrape: bool = False) -> pd.DataFrame:
        # Store the searched location for filtering
        self.searched_location = location
        """
        Optimized job search with parallel processing and separated deep scraping.
        
        Args:
            keywords: Job search keywords
            location: Job location
            max_pages: Maximum pages per platform
            selected_platforms: List of platform names to search
            english_only: Only return English language jobs
            max_workers: Maximum number of parallel workers
            deep_scrape: Whether to fetch full job details (separated from search)
            
        Returns:
            DataFrame with found jobs
        """
        if not selected_platforms:
            selected_platforms = list(self.scrapers.keys())
        
        # Store current search keywords for LLM assessment
        self.current_search_keywords = keywords if isinstance(keywords, list) else [keywords]
        
        print(f"🚀 Starting optimized parallel job search...")
        print(f"   📝 Keywords: {keywords}")
        print(f"   📍 Location: {location or 'anywhere'}")
        print(f"   📄 Max pages per platform: {max_pages}")
        print(f"   🎯 Selected platforms: {', '.join(selected_platforms)}")
        print(f"   ⚡ Parallel workers: {max_workers}")
        print(f"   🔍 Deep scrape: {deep_scrape}")
        
        def search_platform_optimized(platform_name: str) -> List[Dict]:
            """Search a single platform with optimized approach."""
            scraper_key = None
            for key in self.scrapers.keys():
                if key.lower() == platform_name.lower():
                    scraper_key = key
                    break
            
            if not scraper_key:
                print(f"⚠️ Platform '{platform_name}' not available")
                return []

            try:
                print(f"🔍 Searching {scraper_key}...")
                start_time = time.time()
                
                platform_jobs = []
                
                # Convert keywords to list if it's a string
                keywords_list = keywords if isinstance(keywords, list) else [keywords]
                
                # Search all keywords at once for better efficiency
                all_keywords = " OR ".join(keywords_list)
                
                keyword_jobs = self.scrapers[scraper_key].search_jobs(
                    keywords=all_keywords,
                    location=location,
                    max_pages=max_pages,
                    english_only=english_only
                )
                
                # Add platform info to jobs
                for job in keyword_jobs:
                    job['platform'] = scraper_key.lower()
                    job['search_keywords'] = keywords_list
                
                platform_jobs.extend(keyword_jobs)
                
                elapsed_time = time.time() - start_time
                print(f"✅ {scraper_key}: {len(platform_jobs)} jobs found in {elapsed_time:.1f}s")
                
                return platform_jobs
                
            except Exception as e:
                print(f"❌ Error searching {scraper_key}: {e}")
                return []
        
        # Execute searches in parallel with optimized worker count
        all_jobs = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_platform = {
                executor.submit(search_platform_optimized, platform): platform 
                for platform in selected_platforms
            }
            
            for future in as_completed(future_to_platform):
                platform = future_to_platform[future]
                try:
                    jobs = future.result()
                    all_jobs.extend(jobs)
                except Exception as e:
                    print(f"❌ Platform {platform} generated an exception: {e}")
        
        print(f"\n🎯 Total jobs found: {len(all_jobs)}")
        
        # Convert to DataFrame
        if all_jobs:
            df = pd.DataFrame(all_jobs)
            
            # Only do basic processing, skip deep scraping during search
            df = self._process_jobs_dataframe_basic(df, keywords)
            
            return df
        else:
            return pd.DataFrame()
    
    def _fetch_details_for_jobs(self, jobs: List[Dict], scraper: BaseScraper):
        """Fetch detailed descriptions for a list of jobs."""
        print(f"  -> Starting deep scrape for {len(jobs)} jobs...")
        
        # Skip deep scraping for StepStone jobs since they often get blocked
        if scraper.get_platform_name() == "StepStone":
            print(f"    - Skipping deep scrape for StepStone (job detail pages often blocked)")
            return
        
        for i, job in enumerate(jobs):
            if 'url' in job and job['url']:
                # Skip internal network URLs that can't be accessed
                if 'internal.tjgprod.io' in job['url'] or 'searchcore.internal' in job['url']:
                    print(f"    - Skipping job {i+1} due to internal URL: {job['url']}")
                    continue
                
                # Skip fallback URLs that point to search pages (not individual job pages)
                if job['url'] and 'jobs?' in job['url'] and 'q=' in job['url']:
                    print(f"    - Skipping job {i+1} due to search page URL: {job['url']}")
                    continue
                
                print(f"    - Scraping details for job {i+1}/{len(jobs)}...")
                try:
                    # Add timeout protection for deep scraping using threading
                    import threading
                    import queue
                    
                    result_queue = queue.Queue()
                    error_queue = queue.Queue()
                    
                    def fetch_with_timeout():
                        try:
                            details = scraper.fetch_job_details(job['url'])
                            result_queue.put(details)
                        except Exception as e:
                            error_queue.put(e)
                    
                    # Start the fetch in a separate thread
                    fetch_thread = threading.Thread(target=fetch_with_timeout)
                    fetch_thread.daemon = True
                    fetch_thread.start()
                    
                    # Wait for result with timeout (30 seconds)
                    fetch_thread.join(timeout=30)
                    
                    if fetch_thread.is_alive():
                        print(f"    - ⏰ Timeout scraping details for job {i+1} ({job.get('title', 'Unknown')})")
                    else:
                        # Check for errors first
                        try:
                            error = error_queue.get_nowait()
                            print(f"    - Error scraping details for {job.get('title')}: {error}")
                        except queue.Empty:
                            # No error, check for result
                            try:
                                details = result_queue.get_nowait()
                                if details and 'description' in details:
                                    job['description'] = details['description']
                            except queue.Empty:
                                print(f"    - No result received for job {i+1}")
                    
                    time.sleep(random.uniform(1, 2))  # Respectful delay
                except Exception as e:
                    print(f"    - Error scraping details for {job.get('title')}: {e}")
            else:
                print(f"    - Skipping job {i+1} due to missing URL.")

    def _process_jobs_dataframe(self, df: pd.DataFrame, keywords: Union[str, List[str]]) -> pd.DataFrame:
        """Process the combined jobs DataFrame."""
        if df.empty:
            return df
        
        # Standardize columns
        df = df.where(pd.notna(df), None)
        
        # Add search keywords
        if isinstance(keywords, list):
            keywords_str = ', '.join(keywords)
        else:
            keywords_str = keywords
        df['search_keywords'] = keywords_str
        
        # Add search date
        df['search_date'] = datetime.now().strftime("%Y-%m-%d")
        
        # Ensure correct data types
        if 'post_date' in df.columns:
            df['post_date'] = pd.to_datetime(df['post_date'], errors='coerce')
        else:
            df['post_date'] = pd.NaT
        
        # Add a unique ID for each job
        df['unique_id'] = df.apply(lambda row: f"{row.get('platform', 'na')}_{row.get('company', 'na')}_{row.get('title', 'na')}", axis=1)


        
        return df
    
    def _process_jobs_dataframe_basic(self, df: pd.DataFrame, keywords: Union[str, List[str]]) -> pd.DataFrame:
        """Basic processing without deep scraping or LLM analysis."""
        if df.empty:
            return df
        
        # Standardize columns
        df = df.where(pd.notna(df), None)
        
        # Add search keywords
        if isinstance(keywords, list):
            keywords_str = ', '.join(keywords)
        else:
            keywords_str = keywords
        df['search_keywords'] = keywords_str
        
        # Add search date
        df['search_date'] = datetime.now().strftime("%Y-%m-%d")
        
        # Ensure correct data types
        if 'post_date' in df.columns:
            df['post_date'] = pd.to_datetime(df['post_date'], errors='coerce')
        else:
            df['post_date'] = pd.NaT
        
        # Add a unique ID for each job
        df['unique_id'] = df.apply(lambda row: f"{row.get('platform', 'na')}_{row.get('company', 'na')}_{row.get('title', 'na')}", axis=1)
        
        return df
    
    def deep_scrape_jobs_async(self, jobs_df: pd.DataFrame, max_workers: int = 4) -> pd.DataFrame:
        """
        Perform deep scraping on jobs asynchronously after initial search.
        This should be called separately from the search to improve performance.
        Uses caching to avoid repeated requests.
        """
        if jobs_df.empty:
            return jobs_df
        
        print(f"🔍 Starting async deep scraping for {len(jobs_df)} jobs...")
        
        # Import cache service
        from ..services.job_details_cache import job_details_cache
        
        # Clear any stale processing flags
        job_details_cache.clear_processing_flags()
        
        # Get cache stats before starting
        cache_stats = job_details_cache.get_cache_stats()
        processing_status = job_details_cache.get_processing_status()
        print(f"   📊 Cache stats before scraping: {cache_stats.get('cache_hits', 0)} hits, {cache_stats.get('cache_misses', 0)} misses")
        print(f"   🔍 Cache service ID: {id(job_details_cache)}")
        print(f"   📊 Cache service available: {hasattr(job_details_cache, 'db_manager')}")
        print(f"   🔄 URLs currently being processed: {processing_status.get('processing_count', 0)}")
        print(f"   💾 Memory cache size: {processing_status.get('memory_cache_size', 0)}")
        
        jobs_list = jobs_df.to_dict('records')
        
        # Deduplicate jobs by URL to prevent race conditions in parallel processing
        # Keep track of all jobs with the same URL for later merging
        url_to_jobs = {}
        unique_jobs = {}
        duplicate_count = 0
        
        for job in jobs_list:
            url = job.get('url', '')
            if url:
                if url not in url_to_jobs:
                    url_to_jobs[url] = []
                    unique_jobs[url] = job  # Keep the first occurrence
                url_to_jobs[url].append(job)
                if len(url_to_jobs[url]) > 1:
                    duplicate_count += 1
        
        if duplicate_count > 0:
            print(f"   🔄 Found {duplicate_count} duplicate URLs, processing unique URLs only")
        
        jobs_list = list(unique_jobs.values())
        print(f"   📊 Processing {len(jobs_list)} unique jobs (down from {len(jobs_df)} total)")
        
        # Pre-check cache for all URLs to avoid unnecessary processing
        cached_urls = set()
        uncached_jobs = []
        
        for job in jobs_list:
            url = job.get('url', '')
            if url:
                # Check if already cached with retry mechanism
                cached_details = job_details_cache.get_job_details_with_retry(url, max_retries=2, retry_delay=0.5)
                if cached_details:
                    cached_urls.add(url)
                    # Update job with cached details
                    job.update(cached_details)
                    print(f"   📋 Using cached details for: {job.get('title', 'Unknown')}")
                else:
                    uncached_jobs.append(job)
        
        print(f"   📊 Found {len(cached_urls)} jobs already cached, {len(uncached_jobs)} need processing")
        
        # Only process jobs that aren't cached
        if not uncached_jobs:
            print("   ✅ All jobs already cached, no processing needed")
            return jobs_df
        
        processed_jobs = []
        
        def process_job_with_details(job: Dict) -> Dict:
            """Process a single job with deep scraping."""
            try:
                platform = (job.get('platform', '') or '').lower()
                scraper = None
                
                # Find the appropriate scraper
                for scraper_name, scraper_instance in self.scrapers.items():
                    if scraper_name.lower() == platform:
                        scraper = scraper_instance
                        break
                
                if scraper and job.get('url'):
                    # Skip internal network URLs
                    if 'internal.tjgprod.io' in job['url'] or 'searchcore.internal' in job['url']:
                        return job
                    
                    # Skip fallback URLs that point to search pages
                    if job['url'] and 'jobs?' in job['url'] and 'q=' in job['url']:
                        return job
                    
                    try:
                        # Fetch detailed description (cache is checked internally)
                        print(f"   🔄 Fetching details for: {job.get('title', 'Unknown')}")
                        details = scraper.fetch_job_details(job['url'])
                        if details:
                            job.update(details)
                    except Exception as e:
                        print(f"⚠️ Error fetching details for {job.get('title', 'Unknown')}: {e}")
                
                return job
                
            except Exception as e:
                print(f"❌ Error processing job {job.get('title', 'Unknown')}: {e}")
                return job
        
        # Process uncached jobs in parallel
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_job = {
                executor.submit(process_job_with_details, job): job 
                for job in uncached_jobs
            }
            
            for future in as_completed(future_to_job):
                try:
                    processed_job = future.result(timeout=30)
                    processed_jobs.append(processed_job)
                except Exception as e:
                    original_job = future_to_job[future]
                    print(f"❌ Error processing job {original_job.get('title', 'Unknown')}: {e}")
                    processed_jobs.append(original_job)
        
        # Get cache stats after completion
        final_cache_stats = job_details_cache.get_cache_stats()
        final_processing_status = job_details_cache.get_processing_status()
        print(f"   📊 Cache stats after scraping: {final_cache_stats.get('cache_hits', 0)} hits, {final_cache_stats.get('cache_misses', 0)} misses")
        print(f"   📈 Cache hit rate: {final_cache_stats.get('hit_rate', 0):.1%}")
        print(f"   🔄 URLs still being processed: {final_processing_status.get('processing_count', 0)}")
        print(f"   💾 Final memory cache size: {final_processing_status.get('memory_cache_size', 0)}")
        
        # Combine processed jobs with already cached jobs
        all_processed_jobs = []
        
        # Add jobs that were already cached
        for job in jobs_list:
            if job.get('url') in cached_urls:
                all_processed_jobs.append(job)
        
        # Add newly processed jobs
        all_processed_jobs.extend(processed_jobs)
        
        # Merge processed results back with original jobs that had duplicate URLs
        if duplicate_count > 0:
            print(f"   🔄 Merging processed details back to {len(jobs_df)} original jobs...")
            
            # Create a mapping of URL to processed details
            url_to_processed = {}
            for processed_job in all_processed_jobs:
                url = processed_job.get('url', '')
                if url:
                    url_to_processed[url] = processed_job
            
            # Apply processed details to all original jobs
            final_jobs = []
            for job in jobs_df.to_dict('records'):
                url = job.get('url', '')
                if url and url in url_to_processed:
                    # Merge the processed details with the original job
                    processed_details = url_to_processed[url]
                    job.update(processed_details)
                final_jobs.append(job)
            
            print(f"   ✅ Merged details for {len(final_jobs)} jobs")
            
            # Re-detect language for jobs that now have full descriptions
            print(f"   🌍 Re-detecting language for jobs with full descriptions...")
            final_jobs = self._redetect_language_for_full_descriptions(final_jobs)
            
            return pd.DataFrame(final_jobs)
        else:
            print(f"✅ Deep scraping completed for {len(all_processed_jobs)} jobs")
            
            # Re-detect language for jobs that now have full descriptions
            print(f"   🌍 Re-detecting language for jobs with full descriptions...")
            all_processed_jobs = self._redetect_language_for_full_descriptions(all_processed_jobs)
            
            return pd.DataFrame(all_processed_jobs)
    

    
    def save_to_database(self, df: pd.DataFrame, db_path: Optional[str] = None):
        """Save jobs to database."""
        if df.empty:
            print("⚠️ No jobs to save to database")
            return
        
        try:
            db_manager = get_db_manager()
            if not db_manager:
                print("⚠️ Database manager not available")
                return
            
            # Convert DataFrame to list of dictionaries
            jobs_data = df.to_dict('records')
            
            # Apply pre-save safeguards
            jobs_data = self._apply_pre_save_safeguards(jobs_data, db_manager)
            
            # Prepare jobs data for database with proper field mapping
            processed_jobs = []
            for job in jobs_data:
                processed_job = {
                    'title': job.get('title', ''),
                    'company': job.get('company', ''),
                    'location': job.get('location', ''),
                    'salary': job.get('salary', ''),
                    'url': job.get('url', ''),
                    'source': job.get('platform', job.get('source', '')),
                    'scraped_date': datetime.now(),
                    'posted_date': job.get('posted_date', ''),
                    'description': job.get('description', ''),
                    'language': job.get('language', ''),
                    'job_snippet': job.get('job_snippet', ''),
                    'llm_assessment': job.get('llm_assessment', ''),
                    'llm_filtered': job.get('llm_filtered', False),
                    'llm_quality_score': job.get('llm_quality_score', 0),
                    'llm_relevance_score': job.get('llm_relevance_score', 0),
                    'llm_reasoning': job.get('llm_reasoning', '')
                }
                processed_jobs.append(processed_job)
            
            # Use database manager's batch insert method
            if processed_jobs:
                saved_count = db_manager.batch_insert_jobs(processed_jobs)
                print(f"💾 Saved {saved_count} new jobs to database")
                
                # Ensure filtered jobs are properly separated from ignored jobs
                cleaned_count = db_manager.cleanup_filtered_jobs_from_ignored()
                if cleaned_count > 0:
                    print(f"🧹 Cleaned up {cleaned_count} filtered jobs from ignored list to maintain proper separation")
            else:
                print("⚠️ No valid jobs to save after filtering")
            
        except Exception as e:
            print(f"❌ Error saving to database: {e}")
    
    def _apply_pre_save_safeguards(self, jobs_data: List[Dict], db_manager) -> List[Dict]:
        """Apply LLM-powered safeguards and duplicate detection before saving."""
        try:
            # Ollama client is already initialized in constructor
            
            validated_jobs = []
            duplicate_count = 0
            db_duplicate_count = 0
            
            # Get existing jobs from database for duplicate checking
            existing_jobs = self._get_existing_jobs_for_duplicate_check(db_manager)
            print(f"🔍 Checking against {len(existing_jobs)} existing jobs in database for duplicates")
            
            for job in jobs_data:
                # Debug logging for each job
                print(f"🔬 Job Pre-Save Analysis: {job.get('title', 'Unknown')} at {job.get('company', 'Unknown')}")
                print(f"   🌐 URL: {job.get('url', 'N/A')}")
                print(f"   📊 Initial Validation:")
                print(f"     - Title Present: {bool(job.get('title'))}")
                print(f"     - Company Present: {bool(job.get('company'))}")
                print(f"     - URL Present: {bool(job.get('url'))}")
                
                # Validate required fields first - make more lenient to allow jobs without company
                if not job.get('title') or not job.get('url'):
                    print("   ❌ Job skipped: Missing required fields (title or URL)")
                    continue
                
                # Company is preferred but not required for now
                if not job.get('company'):
                    print("   ⚠️ Job missing company information - will proceed anyway")
                    # Set a placeholder company name to avoid database issues
                    job['company'] = 'Company Not Specified'
                
                # Check for URL duplicates in database first (fastest check)
                if self._is_url_duplicate_in_db(job, db_manager):
                    db_duplicate_count += 1
                    print(f"   🚫 URL Duplicate in Database: {job.get('title')} at {job.get('company')}")
                    continue
                
                # Check for exact duplicates by title and company
                if self._is_exact_duplicate_in_db(job, db_manager):
                    db_duplicate_count += 1
                    print(f"   🚫 Exact Duplicate in Database: {job.get('title')} at {job.get('company')}")
                    continue
                
                # Check for description-based duplicates
                if self._is_description_duplicate_in_db(job, db_manager):
                    db_duplicate_count += 1
                    print(f"   🚫 Description Duplicate in Database: {job.get('title')} at {job.get('company')}")
                    continue
                
                # Check for semantic duplicates against existing database jobs
                if self._is_semantic_duplicate_in_db(job, existing_jobs):
                    db_duplicate_count += 1
                    print(f"   🚫 Semantic Duplicate in Database: {job.get('title')} at {job.get('company')}")
                    continue
                
                # Check for semantic duplicates within the current batch
                is_duplicate = False
                for validated_job in validated_jobs:
                    if self._is_semantic_duplicate(job, validated_job):
                        is_duplicate = True
                        duplicate_count += 1
                        print(f"   🚫 Semantic Duplicate in Batch: {job.get('title')} at {job.get('company')}")
                        break
                
                if is_duplicate:
                    continue
                
                # Apply enhanced location filtering using JobFilters
                # Check if location filtering is enabled in config
                location_filter_enabled = getattr(self, 'config', {}).get('filters', {}).get('location_filter_enabled', True)
                
                if location_filter_enabled:
                    try:
                        # Check if this is an Indeed job
                        job_url = (job.get('url', '') or '').lower()
                        job_platform = (job.get('platform', '') or '').lower()
                        job_source = (job.get('source', '') or '').lower()
                        is_indeed_job = ('indeed.com' in job_url or 
                                       job_platform == 'indeed' or 
                                       job_source == 'indeed')
                        
                        if is_indeed_job:
                            print(f"   ✅ Skipping location filter for Indeed job: {job.get('title')} at {job.get('location', 'Unknown')}")
                            # Indeed jobs are already location-filtered by the search, so keep them
                        else:
                            # Convert single job to list for JobFilters
                            job_list = [job]
                            
                            # Use the searched location for filtering instead of hardcoded Essen
                            searched_locations = [self.searched_location] if hasattr(self, 'searched_location') and self.searched_location else None
                            
                            filtered_jobs = JobFilters.filter_by_location(
                                job_list, 
                                searched_locations=searched_locations,
                                platform_name="Pre-Save Validation",
                                use_enhanced_filtering=True,
                                max_distance_km=50.0
                            )
                            
                            if not filtered_jobs:
                                print(f"   🚫 Location Filtered (50km from {self.searched_location if hasattr(self, 'searched_location') else 'Essen'}): {job.get('title')} at {job.get('location', 'Unknown')}")
                                continue
                            
                            # Update job with filtered version
                            job = filtered_jobs[0]
                    except Exception as e:
                        print(f"   ⚠️ Location filtering error: {e}")
                        # Continue with original job if filtering fails
                else:
                    print(f"   ✅ Location filtering disabled - keeping job: {job.get('title')} at {job.get('location', 'Unknown')}")
                
                # Use LLM to make filtering decision
                llm_assessment = self._llm_job_assessment(job)
                
                # Add LLM assessment to job data
                job['llm_assessment'] = llm_assessment
                job['llm_filtered'] = llm_assessment.get('should_filter', False)
                job['llm_quality_score'] = llm_assessment.get('quality_score', 0)
                job['llm_relevance_score'] = llm_assessment.get('relevance_score', 0)
                job['llm_reasoning'] = llm_assessment.get('reasoning', '')
                
                # Debug logging for LLM assessment
                print(f"   🤖 LLM Assessment:")
                print(f"     - Quality Score: {job['llm_quality_score']}/10")
                print(f"     - Relevance Score: {job['llm_relevance_score']}/10")
                print(f"     - Filtering Threshold: {getattr(self, 'relevance_threshold', 5)}")
                print(f"     - Filtered: {job['llm_filtered']}")
                print(f"     - Reasoning: {job['llm_reasoning']}")
                
                # Add language detection and job snippet
                # Always attempt language detection using available content
                description = job.get('description', '') or ''  # Ensure it's a string, not None
                job_title = job.get('title', '') or ''
                job_url = job.get('url', '')
                
                # LinkedIn-specific language detection with lower threshold
                is_linkedin_job = 'linkedin.com' in job_url.lower() if job_url else False
                has_full_description = len(description.strip()) > 100
                has_minimal_description = len(description.strip()) > 30
                has_title = len(job_title.strip()) > 0
                
                if has_full_description:
                    # Use LLM for full descriptions
                    job['language'] = self._llm_detect_language(description)
                    print(f"   🌍 Language detected: {job['language']} (full description: {len(description)} chars)")
                elif is_linkedin_job and has_minimal_description:
                    # For LinkedIn jobs with minimal description, use LinkedIn-specific detection
                    job['language'] = self._detect_linkedin_language(description, job_title)
                    print(f"   🌍 LinkedIn language detected: {job['language']} (minimal description: {len(description)} chars)")
                elif has_title:
                    # Prioritize title-based detection when description is insufficient
                    if has_minimal_description:
                        # Use combined title + description for better accuracy
                        combined_text = f"{job_title} {description}".strip()
                        job['language'] = self._fallback_language_detection(combined_text)
                        print(f"   🌍 Title + description language detected: {job['language']} (combined: {len(combined_text)} chars)")
                    else:
                        # Use title-only detection when description is too short
                        job['language'] = self._fallback_language_detection(job_title)
                        print(f"   🌍 Title-only language detected: {job['language']} (title: {len(job_title)} chars)")
                else:
                    job['language'] = 'unknown'
                    print(f"   ⚠️ No content for language detection - title: {len(job_title)} chars, description: {len(description)} chars")
                
                job['job_snippet'] = llm_assessment.get('job_snippet', '')
                
                # Lower relevance threshold for jobs without descriptions
                relevance_threshold = getattr(self, 'relevance_threshold', 5)  # Default to 5
                has_description = bool((job.get('description', '') or '').strip())
                
                # Use lower threshold for jobs without descriptions (LinkedIn issue)
                effective_threshold = 3 if not has_description else relevance_threshold
                
                should_keep = (
                    not job['llm_filtered'] and 
                    job['llm_relevance_score'] >= effective_threshold
                )
                
                if should_keep:
                    validated_jobs.append(job)
                    if not has_description:
                        print(f"   ⚠️ Saved job without description: {job.get('title', 'Unknown')} - Relevance: {job['llm_relevance_score']}/10")
                else:
                    print(f"   🚫 Filtered out: {job.get('title', 'Unknown')} - Relevance: {job['llm_relevance_score']}/10")
            
            if duplicate_count > 0:
                print(f"🧬 Removed {duplicate_count} semantic duplicates from this batch.")
            if db_duplicate_count > 0:
                print(f"🗄️ Removed {db_duplicate_count} duplicates already in database.")
            
            return validated_jobs
            
        except Exception as e:
            print(f"⚠️ Error in LLM safeguards, falling back to basic validation: {e}")
            # Fallback to basic validation - more lenient
            validated_jobs = []
            for job in jobs_data:
                if job.get('title') and job.get('url'):
                    # Set placeholder company if missing
                    if not job.get('company'):
                        job['company'] = 'Company Not Specified'
                    validated_jobs.append(job)
            return validated_jobs

    def _get_existing_jobs_for_duplicate_check(self, db_manager) -> List[Dict]:
        """Get existing jobs from database for duplicate checking (last 90 days with better coverage)."""
        try:
            # First, get jobs with same company names to improve duplicate detection
            query = """
                SELECT title, company, url, description, scraped_date, llm_quality_score, llm_relevance_score
                FROM job_listings 
                WHERE scraped_date >= NOW() - INTERVAL '90 days'
                AND llm_filtered = FALSE
                ORDER BY scraped_date DESC
                LIMIT 5000
            """
            results = db_manager.execute_query(query, fetch='all')
            
            existing_jobs = []
            for row in results:
                existing_jobs.append({
                    'title': row[0],
                    'company': row[1], 
                    'url': row[2],
                    'description': row[3] if row[3] else '',
                    'scraped_date': row[4],
                    'quality_score': row[5] if row[5] else 0,
                    'relevance_score': row[6] if row[6] else 0
                })
            
            print(f"📊 Loaded {len(existing_jobs)} existing jobs for duplicate checking")
            return existing_jobs
            
        except Exception as e:
            print(f"⚠️ Error fetching existing jobs for duplicate check: {e}")
            return []

    def _is_url_duplicate_in_db(self, job: Dict, db_manager) -> bool:
        """Check if job URL already exists in database."""
        try:
            if not job.get('url'):
                return False
                
            query = "SELECT 1 FROM job_listings WHERE url = %s LIMIT 1"
            result = db_manager.execute_query(query, (job['url'],), fetch='one')
            return result is not None
            
        except Exception as e:
            print(f"⚠️ Error checking URL duplicate: {e}")
            return False

    def _is_exact_duplicate_in_db(self, job: Dict, db_manager) -> bool:
        """Check for exact duplicates by title and company in database."""
        try:
            if not job.get('title'):
                return False
            
            # If company is missing or placeholder, only check by title
            if not job.get('company') or job.get('company') == 'Company Not Specified':
                # Check for exact title match only
                query = """
                    SELECT id, url, scraped_date 
                    FROM job_listings 
                    WHERE LOWER(title) = LOWER(%s)
                    AND llm_filtered = FALSE
                    ORDER BY scraped_date DESC
                    LIMIT 5
                """
                results = db_manager.execute_query(query, (job['title'],), fetch='all')
                
                if results:
                    print(f"   🚫 Exact duplicate found (title only): '{job.get('title')}'")
                    for result in results:
                        print(f"      - Existing ID: {result[0]}, URL: {result[1]}, Date: {result[2]}")
                    return True
                
                return False
                
            # Check for exact title and company match
            query = """
                SELECT id, url, scraped_date 
                FROM job_listings 
                WHERE LOWER(title) = LOWER(%s) 
                AND LOWER(company) = LOWER(%s)
                AND llm_filtered = FALSE
                ORDER BY scraped_date DESC
                LIMIT 5
            """
            results = db_manager.execute_query(query, (job['title'], job['company']), fetch='all')
            
            if results:
                print(f"   🚫 Exact duplicate found: '{job.get('title')}' at {job.get('company')}")
                for result in results:
                    print(f"      - Existing ID: {result[0]}, URL: {result[1]}, Date: {result[2]}")
                return True
            
            return False
            
        except Exception as e:
            print(f"⚠️ Error checking exact duplicate: {e}")
            return False

    def _is_semantic_duplicate_in_db(self, job: Dict, existing_jobs: List[Dict]) -> bool:
        """Check if job is semantically duplicate of any existing job in database."""
        try:
            job_company = (job.get('company', '') or '').lower().strip()
            job_title = (job.get('title', '') or '').lower().strip()
            
            # Quick company name check first
            for existing_job in existing_jobs:
                existing_company = (existing_job.get('company', '') or '').lower().strip()
                
                # If companies don't match, skip LLM check
                if job_company != existing_company:
                    continue
                
                # For same company, check if titles are very similar
                existing_title = (existing_job.get('title', '') or '').lower().strip()
                
                # Simple similarity check first (faster than LLM)
                if self._are_titles_similar(job_title, existing_title):
                    print(f"   🔍 Potential duplicate detected: '{job_title}' vs '{existing_title}' at {job_company}")
                    
                    # Use LLM for final confirmation if available
                    if hasattr(self, 'ollama_client') and self.ollama_client and self.ollama_client.available:
                        return self._is_semantic_duplicate(job, existing_job)
                    else:
                        # Fallback: if titles are very similar and same company, consider duplicate
                        return True
            
            return False
            
        except Exception as e:
            print(f"⚠️ Error in semantic duplicate check: {e}")
            return False

    def _is_description_duplicate_in_db(self, job: Dict, db_manager) -> bool:
        """Check for duplicates based on description similarity."""
        try:
            if not job.get('description') or len(job.get('description', '')) < 100:
                return False  # Skip jobs with short descriptions
                
            # Get jobs with similar descriptions from the same company
            query = """
                SELECT id, title, url, scraped_date 
                FROM job_listings 
                WHERE LOWER(company) = LOWER(%s)
                AND description IS NOT NULL 
                AND LENGTH(description) > 100
                AND llm_filtered = FALSE
                ORDER BY scraped_date DESC
                LIMIT 10
            """
            results = db_manager.execute_query(query, (job['company'],), fetch='all')
            
            if not results:
                return False
            
            job_desc = (job.get('description', '') or '').lower()
            
            for result in results:
                existing_desc = result[2] if result[2] else ''
                if existing_desc and len(existing_desc) > 100:
                    # Calculate description similarity
                    similarity = self._calculate_description_similarity(job_desc, existing_desc.lower())
                    if similarity > 0.85:  # 85% similarity threshold
                        print(f"   🚫 Description duplicate found: '{job.get('title')}' at {job.get('company')} (similarity: {similarity:.2f})")
                        return True
            
            return False
            
        except Exception as e:
            print(f"⚠️ Error checking description duplicate: {e}")
            return False

    def _calculate_description_similarity(self, desc1: str, desc2: str) -> float:
        """Calculate similarity between two job descriptions."""
        try:
            if not desc1 or not desc2:
                return 0.0
            
            # Extract key words (remove common words)
            import re
            from collections import Counter
            
            # Remove common words and punctuation
            common_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them', 'my', 'your', 'his', 'her', 'its', 'our', 'their', 'mine', 'yours', 'hers', 'ours', 'theirs'}
            
            def extract_words(text):
                words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
                return [w for w in words if w not in common_words]
            
            words1 = Counter(extract_words(desc1))
            words2 = Counter(extract_words(desc2))
            
            if not words1 or not words2:
                return 0.0
            
            # Calculate Jaccard similarity
            intersection = sum((words1 & words2).values())
            union = sum((words1 | words2).values())
            
            if union == 0:
                return 0.0
            
            return intersection / union
            
        except Exception as e:
            print(f"⚠️ Error calculating description similarity: {e}")
            return 0.0

    def _are_titles_similar(self, title1: str, title2: str) -> bool:
        """Check if two job titles are similar using enhanced text analysis."""
        try:
            # Normalize titles - ensure they are strings, not None
            t1 = (title1 or '').lower().strip()
            t2 = (title2 or '').lower().strip()
            
            # Exact match
            if t1 == t2:
                return True
            
            # Remove common variations and normalize
            variations_to_remove = [
                'senior', 'junior', 'lead', 'principal', 'staff', 'sr', 'jr',
                '(m/w/d)', '(w/m/d)', '(d/m/w)', '(m/f/d)', '(f/m/d)',
                '(m/w)', '(w/m)', '(d/m)', '(m/f)', '(f/m)',
                'm/w/d', 'w/m/d', 'd/m/w', 'm/f/d', 'f/m/d',
                'm/w', 'w/m', 'd/m', 'm/f', 'f/m',
                'all genders', 'all genders welcome', 'diversity welcome',
                'remote', 'hybrid', 'onsite', 'full-time', 'part-time',
                'temporary', 'permanent', 'contract', 'freelance'
            ]
            
            t1_clean = t1
            t2_clean = t2
            
            for variation in variations_to_remove:
                t1_clean = t1_clean.replace(variation, '').strip()
                t2_clean = t2_clean.replace(variation, '').strip()
            
            # Check if cleaned titles are exactly the same
            if t1_clean == t2_clean and t1_clean:
                return True
            
            # Check for high word overlap (85% or more for stricter matching)
            words1 = set(t1_clean.split())
            words2 = set(t2_clean.split())
            
            if len(words1) > 0 and len(words2) > 0:
                overlap = len(words1.intersection(words2))
                total_unique = len(words1.union(words2))
                similarity = overlap / total_unique if total_unique > 0 else 0
                
                # Require at least 2 common words and 85% similarity
                if overlap >= 2 and similarity >= 0.85:
                    return True
            
            # Check for key role variations
            role_variations = {
                'developer': ['engineer', 'programmer', 'coder'],
                'engineer': ['developer', 'programmer'],
                'administrator': ['admin', 'manager'],
                'admin': ['administrator', 'manager'],
                'specialist': ['expert', 'analyst'],
                'analyst': ['specialist', 'expert'],
                'manager': ['lead', 'director', 'head'],
                'lead': ['manager', 'senior'],
                'senior': ['lead', 'principal'],
                'junior': ['entry', 'associate'],
            }
            
            # Check if titles contain similar roles
            for role, variations in role_variations.items():
                if role in t1_clean and any(var in t2_clean for var in variations):
                    # Additional check: ensure other key words match
                    other_words1 = [w for w in t1_clean.split() if w not in [role] + variations]
                    other_words2 = [w for w in t2_clean.split() if w not in [role] + variations]
                    if other_words1 and other_words2:
                        common_other = set(other_words1).intersection(set(other_words2))
                        if len(common_other) >= 1:  # At least one other word matches
                            return True
            
            return False
            
        except Exception as e:
            print(f"⚠️ Error in title similarity check: {e}")
            return False

    def _is_semantic_duplicate(self, job1: Dict, job2: Dict) -> bool:
        """Use LLM to check if two jobs are semantically the same role."""
        # Quick check for company name
        if (job1.get('company', '') or '').lower() != (job2.get('company', '') or '').lower():
            return False
            
        try:
            if not hasattr(self, 'ollama_client') or not self.ollama_client or not self.ollama_client.available:
                # Fallback to simple title match if LLM is not available
                return (job1.get('title', '') or '').lower() == (job2.get('title', '') or '').lower()

            job1_title = job1.get('title', '')
            job1_desc = job1.get('description', '')[:500]
            job2_title = job2.get('title', '')
            job2_desc = job2.get('description', '')[:500]
            
            system_prompt = """You are an expert job analyst. Your task is to determine if two job postings are for the same role, even if they are in different locations.
            Respond ONLY with a JSON object with a single key "is_duplicate" (true/false)."""
            
            prompt = f"""
            Are these two jobs for the same role?
            
            Job 1:
            Title: {job1_title}
            Description: {job1_desc}
            
            Job 2:
            Title: {job2_title}
            Description: {job2_desc}
            
            Respond with JSON: {{"is_duplicate": true}} or {{"is_duplicate": false}}
            """
            
            response = self.ollama_client.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=50,
                temperature=0.0
            )
            
            if response:
                import json
                try:
                    assessment = json.loads(response)
                    return assessment.get('is_duplicate', False)
                except json.JSONDecodeError:
                    # Handle cases where response is not perfect JSON
                    return "true" in response.lower()
            
            return False
        except Exception as e:
            print(f"⚠️ LLM duplicate check error: {e}")
            # Fallback to simple title match on error
            return (job1.get('title', '') or '').lower() == (job2.get('title', '') or '').lower()

    def _llm_detect_language(self, text: str) -> str:
        """Use LLM to detect the language of a given text."""
        try:
            # Early return for empty text
            if not text or not text.strip():
                return 'unknown'
                
            if not hasattr(self, 'ollama_client') or not self.ollama_client or not self.ollama_client.available:
                return self._fallback_language_detection(text)

            system_prompt = """You are a language detection expert specialized in German and English job postings. 
            Focus ONLY on the job description content, NOT on location information.
            Respond ONLY with a JSON object containing the key "language" and the two-letter ISO 639-1 code in lowercase.
            Example: {{"language": "en"}} for English, {{"language": "de"}} for German."""

            prompt = f"""
            Detect the language of this job posting description. Focus on the actual job content, not location.
            Look for these specific indicators:

            GERMAN indicators:
            - German words: wir, unser, für, mit, von, zu, bei, der, die, das, und
            - German job terms: Mitarbeiter, Entwickler, Stelle, Aufgaben, Kenntnisse, Qualifikationen
            - German phrases: "Wir suchen", "Für unser Team", "Ihre Aufgaben", "Ihre Qualifikationen"

            ENGLISH indicators:
            - Standard English grammar and vocabulary
            - English phrases: we are, you will, experience in, skills required, responsibilities
            - English job terms: developer, engineer, manager, analyst, requirements

            IMPORTANT: Ignore location information and focus on the actual job description content.
            
            Text to analyze:
            ---
            {text[:3000]}
            ---
            
            Respond with JSON format: {{"language": "de"}} or {{"language": "en"}}
            """

            response = self.ollama_client.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=50,
                temperature=0.0
            )

            if response and isinstance(response, str):
                import json
                try:
                    # Clean response
                    clean_response = response.strip().replace("'", '"')
                    if clean_response.startswith("```json"):
                        clean_response = clean_response[7:]
                    if clean_response.startswith("```"):
                        clean_response = clean_response[3:]
                    if clean_response.endswith("```"):
                        clean_response = clean_response[:-3]

                    assessment = json.loads(clean_response.strip())
                    lang = assessment.get('language', 'unknown')
                    
                    # Ensure lowercase and validate
                    if isinstance(lang, str) and len(lang) == 2:
                        return lang.lower()
                    
                except (json.JSONDecodeError, TypeError) as json_error:
                    # Fallback to simple regex
                    try:
                        import re
                        # Clean the response first to avoid regex issues
                        clean_response = str(response).strip()
                        match = re.search(r'"language":\s*"(\w{2})"', clean_response)
                        if match:
                            return match.group(1).lower()
                    except Exception as regex_error:
                        print(f"⚠️ Regex language detection error: {regex_error}")
                        pass

            # If LLM fails, use fallback detection
            if hasattr(self, 'debug') and self.debug:
                print(f"   🔄 Using fallback language detection for text: {text[:100] if text else 'None'}...")
            return self._fallback_language_detection(text)
            
        except Exception as e:
            print(f"⚠️ LLM language detection error: {e}")
            if hasattr(self, 'debug') and self.debug:
                print(f"   📍 Error occurred in _llm_detect_language for text: {text[:100] if text else 'None'}...")
            return self._fallback_language_detection(text)

    def _fallback_language_detection(self, text: str) -> str:
        """Fallback language detection using rule-based approach."""
        if not text:
            return 'unknown'
        
        text_lower = text.lower()
        
        # Strong German indicators with weighted scoring (includes titles and short descriptions)
        german_indicators = {
            # Very strong German indicators (common in job titles)
            '(m/w/d)': 20, '(w/m/d)': 20, '(d/m/w)': 20, '(m/w/x)': 20, '(w/m/x)': 20, '(d/m/x)': 20,
            'gmbh': 15, ' ag ': 15, ' kg ': 12, ' e.v.': 12,
            # Job title specific German terms (higher weights for titles)
            'entwickler': 10, 'ingenieur': 10, 'mitarbeiter': 8, 'experte': 8, 'spezialist': 8,
            'berater': 8, 'manager': 6, 'administrator': 6, 'betreuer': 6, 'koordinator': 6,
            'assistent': 6, 'sachbearbeiter': 6, 'fachkraft': 6, 'fachinformatiker': 8,
            # Job-specific German terms
            'wir suchen': 8, 'für unser': 8, 'stellenausschreibung': 8,
            'aufgaben': 5, 'kenntnisse': 5, 'erfahrung': 5, 'qualifikation': 5, 'anforderungen': 5, 'bewerbung': 5,
            'ihre aufgaben': 7, 'ihre qualifikationen': 7, 'für unser team': 6,
            'arbeitsplatz': 5, 'stelle': 5, 'bereich': 5, 'unternehmen': 4,
            # Common German words
            ' der ': 3, ' die ': 3, ' das ': 3, ' und ': 3, ' mit ': 3, ' für ': 3, ' bei ': 3, ' von ': 3
        }
        
        # Strong English indicators (includes titles and short descriptions)
        english_indicators = {
            # Company types
            ' ltd': 15, ' inc': 15, ' corp': 12, ' llc': 12,
            # Job title specific English terms (higher weights for titles)
            'developer': 10, 'engineer': 10, 'specialist': 8, 'expert': 8, 'analyst': 8,
            'manager': 8, 'administrator': 6, 'coordinator': 6, 'assistant': 6, 'consultant': 6,
            'architect': 8, 'lead': 6, 'senior': 4, 'junior': 4, 'principal': 6,
            # Job-specific English terms
            'we are looking': 8, 'you will': 6, 'experience in': 6, 'for our': 6,
            'skills required': 6, 'responsibilities': 5, 'requirements': 5, 'job posting': 6,
            'opportunity': 5, 'position': 5, 'team': 4, 'company': 4, 'role': 4,
            'you should': 5, 'you must': 5, 'we offer': 5, 'we provide': 5,
            # Common English words
            ' the ': 3, ' and ': 3, ' with ': 3, ' for ': 3, ' from ': 3, ' at ': 3, ' in ': 3, ' to ': 3
        }
        
        # Calculate scores
        german_score = sum(weight for indicator, weight in german_indicators.items() if indicator in text_lower)
        english_score = sum(weight for indicator, weight in english_indicators.items() if indicator in text_lower)
        
        # Determine language (lowered thresholds for better sensitivity to short content)
        if german_score > english_score and german_score >= 1:
            return 'de'
        elif english_score > german_score and english_score >= 1:
            return 'en'
        else:
            # If unclear, check for explicit language mentions
            if any(phrase in text_lower for phrase in ['deutsch', 'german', 'deutschland', 'germany']):
                return 'de'
            elif any(phrase in text_lower for phrase in ['english', 'international', 'global']):
                return 'en'
            
            # If still unclear, try to detect by common job title patterns
            if any(term in text_lower for term in ['entwickler', 'mitarbeiter', 'ingenieur', 'experte', 'spezialist', 'berater', 'fachinformatiker']):
                return 'de'
            elif any(term in text_lower for term in ['developer', 'employee', 'engineer', 'expert', 'specialist', 'consultant', 'analyst']):
                return 'en'
            
        return 'unknown'

    def _llm_job_assessment(self, job: Dict) -> Dict:
        """Use LLM to assess job quality, detect language, and extract key responsibilities."""
        try:
            if not hasattr(self, 'ollama_client') or not self.ollama_client or not self.ollama_client.available:
                if hasattr(self, 'debug') and self.debug:
                    print(f"   🔄 LLM not available, using fallback assessment for: {job.get('title', 'Unknown')}")
                return self._fallback_assessment(job)
            
            # Prepare job data for LLM analysis
            job_title = job.get('title', '')
            company = job.get('company', '')
            location = job.get('location', '')
            salary = job.get('salary', '')
            description = (job.get('description', '') or '')[:90000]  # Ensure it's a string, not None
            
            # Create prompt for LLM assessment
            # Check if job has description
            has_description = bool(description.strip())
            
            # Get the searched location for context
            searched_location = getattr(self, 'searched_location', 'Essen')
            
            system_prompt = f"""You are an expert job market analyst specializing in IT and technical roles in GERMANY ONLY. 
            Your task is to analyze job postings for quality, relevance, and extract key information.
            
            CRITICAL GUIDELINES:
            - ONLY analyze jobs located in Germany or remote jobs for living in Germany.
            - IMMEDIATELY REJECT any jobs located in USA, United States, Canada, UK, or other non-German countries
            - For LinkedIn jobs without descriptions: Be more lenient and base assessment on title and company
            - Give higher relevance scores to clear IT/technical job titles even without descriptions
            - Focus on technical skills, programming languages, frameworks, and IT infrastructure
            - Pay attention to salary information when available
            - Assess company legitimacy and location validity
              
            - Location validation: If location contains USA, United States, America, Canadian cities, UK cities, London, New York, California, Texas, etc. → REJECT immediately
            - SEARCHED LOCATION: {searched_location} - Use this as the reference location for distance filtering
            - IMPORTANT: If job location contains "{searched_location}" or is very close to it, KEEP the job regardless of other factors
            
            Respond ONLY with valid JSON, no additional text or explanations."""
            
            prompt = f"""
            Analyze this job posting and provide comprehensive assessment in JSON format:
            {{
                "should_filter": true/false,
                "quality_score": 0-10,
                "relevance_score": 0-10,
                "reasoning": "brief explanation of decision",
                "job_snippet": "4-5 key responsibilities or requirements (max 250 chars)",
                "concerns": ["concern1", "concern2"] or [],
                "positive_aspects": ["aspect1", "aspect2"] or [],
                "location_valid": true/false,
                "company_legitimate": true/false,
                "job_type_clear": true/false,
                "technical_skills": ["skill1", "skill2"] or [],
                "experience_level": "entry/mid/senior/lead",
                "remote_friendly": true/false
            }}
            
            SEARCH KEYWORDS: {', '.join(self.current_search_keywords) if hasattr(self, 'current_search_keywords') else 'Not specified'}
            SEARCHED LOCATION: {searched_location}
            
            ASSESSMENT CRITERIA:
            
            CRITICAL: JOB TITLE RELEVANCE IS THE PRIMARY FILTER
            
            IMMEDIATELY FILTER OUT (should_filter: true) jobs with titles that are:
            - Sales roles: "Sales Representative", "Account Manager", "Business Development", "Sales Manager", "Sales Engineer"
            - Marketing roles: "Marketing Manager", "Content Creator", "Social Media Manager", "Marketing Specialist"
            - Design roles: "Graphic Designer", "UI/UX Designer", "Web Designer", "Creative Director"
            - Non-technical management: "Project Manager" (unless explicitly IT/technical), "Operations Manager", "General Manager"
            - Customer service: "Customer Support", "Help Desk", "Customer Success", "Support Specialist"
            - HR/Finance: "Human Resources", "Recruiter", "Accountant", "Finance Manager"
            - Administrative: "Office Administrator", "Secretary", "Assistant", "Coordinator"
            - Construction/Manufacturing: "Construction Manager", "Factory Worker", "Maintenance Technician"
            - Healthcare/Education: "Nurse", "Teacher", "Doctor", "Therapist"
            - Retail/Hospitality: "Store Manager", "Waiter", "Chef", "Cashier"
            
            FILTER OUT (should_filter: true) jobs that are:
            - Clearly spam, fake, or MLM/pyramid schemes
            - Irrelevant to professional IT/technical work (BE VERY STRICT HERE)
            - Incomplete or very low quality descriptions
            - Obviously scams or suspicious companies
            - NOT closely related to the search keywords (REQUIRE STRONG KEYWORD MATCH)
            - Too broad or generic job titles without IT/System specificity
            - Different job categories than IT/Systems/Engineering
            - Job titles without IT/System/Technical keywords when searching for IT roles
            - Location more than 50km from {searched_location}, Germany (unless remote) - BE LENIENT with location filtering
            - ANY jobs located in USA, United States, Canada, UK, or other non-German countries
            - Jobs with locations containing: USA, United States, America, Canadian cities, UK cities, London, New York, California, Texas, etc.
            
            ONLY KEEP (should_filter: false) jobs that have titles containing:
            - "System Administrator", "Systems Administrator", "System Admin", "IT Admin"
            - "IT Engineer", "Systems Engineer", "Infrastructure Engineer", "Platform Engineer"
            - "DevOps Engineer", "Site Reliability Engineer", "Cloud Engineer"
            - "Network Administrator", "Network Engineer", "Security Engineer"
            - "IT Integration", "Systems Integration", "Integration Specialist"
            - "Technical Lead", "IT Manager", "Systems Manager" (technical management only)
            - "Software Engineer", "Software Developer" (if relevant to systems/infrastructure)
            - Other IT/technical roles directly related to system administration, infrastructure, or integration
            
            Additional requirements for KEEPING jobs:
            - Legitimate professional IT/technical opportunities
            - Clear job descriptions or relevant technical titles
            - From real companies with proper structure
            - Relevant to IT infrastructure, systems administration, or integration work
            - STRONG match to search keywords (not just tangential)
            - Specific technical job titles that match the search intent
            - Within 50km of {searched_location} or remote work or in major German cities - BE LENIENT with location
            - ONLY German locations: Berlin, Hamburg, Munich, Cologne, Frankfurt, Stuttgart, Düsseldorf, Dortmund, Essen, Leipzig, Bremen, Dresden, Hannover, Nuremberg, and other German cities
            - Remote jobs that specify Germany or living in Germany
            
            RELEVANCE SCORING (0-10) - BE VERY STRICT:
            - 9-10: Perfect match to search keywords (exact title/role match like "Senior System Administrator", "IT Systems Integration")
            - 7-8: Very close match (similar IT role with minor variations like "Systems Engineer" for "IT Engineer")
            - 5-6: Related IT role but different focus (like "Network Admin" when searching for "System Admin")
            - 3-4: Tangentially IT-related but wrong category (like "IT Support" when searching for "System Admin")
            - 1-2: Non-IT roles or completely unrelated (Sales, Marketing, Design, etc.)
            - 0: Must filter out - non-technical roles should get 0 and be filtered
            
            QUALITY SCORING (0-10):
            - 9-10: Excellent job posting with detailed description, clear requirements, good company
            - 7-8: Good job posting with adequate information and legitimate company
            - 5-6: Average job posting with basic information
            - 3-4: Poor job posting with limited information
            - 1-2: Very poor job posting with minimal information
            
            SPECIAL HANDLING for jobs without descriptions:
            - Focus on job title and company name for assessment
            - Give benefit of doubt to clear IT/tech job titles
            - Score 6-8 for relevant titles even without description
            - Only filter if title is clearly unrelated or spam
            
            TECHNICAL ANALYSIS:
            - Extract technical skills mentioned (programming languages, frameworks, tools)
            - Assess experience level based on title and requirements
            - Determine if remote work is mentioned or possible
            - Consider salary information when available for quality assessment
            
            Job Details:
            Title: {job_title}
            Company: {company}
            Location: {location}
            Salary: {salary if salary else "Not specified"}
            Description: {description if has_description else "No description available (LinkedIn limitation - assess based on title/company)"}
            """
            
            response = self.ollama_client.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=500,
                temperature=0.1
            )
            
            if response:
                try:
                    # Try to parse JSON response
                    import json
                    assessment = json.loads(response)
                    
                    # Validate required fields
                    if all(key in assessment for key in ['should_filter', 'quality_score', 'relevance_score']):
                        return assessment
                    
                except json.JSONDecodeError:
                    # Try to extract JSON from response
                    try:
                        import re
                        json_match = re.search(r'\{.*\}', response, re.DOTALL)
                        if json_match:
                            assessment = json.loads(json_match.group())
                            if all(key in assessment for key in ['should_filter', 'quality_score', 'relevance_score']):
                                return assessment
                    except:
                        pass
            
            # If LLM fails, use fallback
            return self._fallback_assessment(job)
            
        except Exception as e:
            print(f"⚠️ LLM assessment error for {job.get('title', 'Unknown')}: {e}")
            if hasattr(self, 'debug') and self.debug:
                print(f"   📍 Error occurred in _llm_job_assessment")
                print(f"   🔍 Job title: {job.get('title', 'N/A')}")
                print(f"   🔍 Company: {job.get('company', 'N/A')}")
                print(f"   🔍 Location: {job.get('location', 'N/A')}")
                print(f"   🔍 Has description: {bool((job.get('description', '') or '').strip())}")
                print(f"   🔍 Description length: {len(job.get('description', '') or '')}")
            return self._fallback_assessment(job)

    def _fallback_assessment(self, job: Dict) -> Dict:
        """Fallback assessment when LLM is not available."""
        # Basic quality assessment based on job data completeness
        quality_score = 5  # Default medium quality
        
        # Increase score for complete data
        if job.get('description') and len(job.get('description', '')) > 100:
            quality_score += 2
        if job.get('location'):
            quality_score += 1
        if job.get('salary'):
            quality_score += 1
        if job.get('company') and len(job.get('company', '')) > 3:
            quality_score += 1
        
        # Basic spam detection
        title = (job.get('title', '') or '').lower()
        company = (job.get('company', '') or '').lower()
        description = (job.get('description', '') or '').lower()
        
        spam_keywords = ['earn money', 'work from home guaranteed', 'no experience needed', 
                        'make money fast', 'mlm', 'pyramid', 'get rich', 'easy money']
        
        should_filter = any(keyword in title + ' ' + company + ' ' + description 
                           for keyword in spam_keywords)
        
        # Basic language detection (fallback)
        language = 'en'  # Default to English
        if any(word in description for word in ['der', 'die', 'das', 'und', 'mit', 'für']):
            language = 'de'
        
        # Basic job snippet extraction (fallback)
        job_snippet = job.get('title', '')[:100] + "..." if len(job.get('title', '')) > 100 else job.get('title', '')
        
        return {
            'should_filter': should_filter,
            'quality_score': min(quality_score, 10),
            'relevance_score': 7,  # Default assumption of relevance
            'reasoning': 'Basic rule-based assessment (LLM not available)',
            'language': language,
            'job_snippet': job_snippet,
            'concerns': ['LLM analysis not available'] if should_filter else [],
            'positive_aspects': ['Passed basic validation'],
            'location_valid': bool(job.get('location')),
            'company_legitimate': True,
            'job_type_clear': bool(job.get('title'))
        }
    
    def _is_duplicate_job(self, job: Dict, db_manager) -> bool:
        """Check if job already exists in database."""
        try:
            query = "SELECT COUNT(*) FROM job_listings WHERE url = %s"
            result = db_manager.execute_query(query, (job.get('url'),), fetch='one')
            return result[0] > 0 if result else False
        except Exception:
            return False
    
    def _is_german_location(self, location: str) -> bool:
        """Check if location is in Germany."""
        if not location:
            return False
        
        location_lower = location.lower()
        
        # German indicators
        german_indicators = [
            'deutschland', 'germany', 'berlin', 'hamburg', 'münchen', 'munich',
            'köln', 'cologne', 'frankfurt', 'stuttgart', 'düsseldorf', 'dortmund',
            'essen', 'leipzig', 'bremen', 'dresden', 'hannover', 'nürnberg'
        ]
        
        return any(indicator in location_lower for indicator in german_indicators)
    
    def set_relevance_threshold(self, threshold: int):
        """Set the relevance threshold for job filtering."""
        self.relevance_threshold = max(1, min(10, threshold))  # Ensure it's between 1-10
    
    def get_available_platforms(self) -> List[str]:
        """Get list of available platforms."""
        return list(self.scrapers.keys())
    
    def close(self):
        """Clean up resources."""
        for scraper in self.scrapers.values():
            try:
                scraper.close()
            except Exception as e:
                if self.debug:
                    print(f"❌ Error closing scraper: {e}")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close() 

    def _redetect_language_for_full_descriptions(self, jobs_data: List[Dict]) -> List[Dict]:
        """
        Re-detect language for jobs that now have full descriptions after deep scraping.
        This ensures accurate language detection using the complete job data.
        """
        updated_count = 0
        skipped_count = 0
        
        for job in jobs_data:
            description = job.get('description', '') or ''  # Ensure it's a string, not None
            current_language = job.get('language', 'unknown')
            
            # Check if we have substantial description content
            has_full_description = len(description.strip()) > 100
            
            if has_full_description:
                # Re-detect language with full description
                new_language = self._llm_detect_language(description)
                
                if new_language != current_language:
                    job['language'] = new_language
                    updated_count += 1
                    print(f"   🔄 Updated language for '{job.get('title', 'Unknown')}': {current_language} → {new_language}")
                else:
                    print(f"   ✅ Language confirmed for '{job.get('title', 'Unknown')}': {new_language}")
            else:
                skipped_count += 1
                if current_language == 'unknown':
                    print(f"   ⚠️ Still no full description for '{job.get('title', 'Unknown')}' ({len(description)} chars)")
        
        if updated_count > 0:
            print(f"   🌍 Language detection: {updated_count} jobs updated, {skipped_count} skipped")
        
        return jobs_data

    def _detect_linkedin_language(self, description: str, title: str = "") -> str:
        """LinkedIn-specific language detection that works with shorter descriptions."""
        try:
            # Combine title and description for better detection
            text_to_analyze = f"{title} {description}".lower()
            
            if not text_to_analyze.strip():
                return 'unknown'
            
            # Strong German indicators for LinkedIn job postings
            german_indicators = {
                '(m/w/d)': 15, '(w/m/d)': 15, '(d/m/w)': 15, '(m/w/x)': 15, '(w/m/x)': 15, '(d/m/x)': 15,
                'gmbh': 10, ' ag ': 10, ' kg ': 8, ' e.v.': 8,
                'wir suchen': 8, 'für unser': 8, 'mitarbeiter': 6, 'unternehmen': 6,
                'entwickler': 6, 'ingenieur': 6, 'aufgaben': 5, 'kenntnisse': 5,
                'erfahrung': 5, 'qualifikation': 5, 'anforderungen': 5,
                'ihre aufgaben': 7, 'ihre qualifikationen': 7, 'für unser team': 6,
                'bewerbung': 5, 'arbeitsplatz': 5, 'stelle': 5, 'bereich': 5,
                ' der ': 3, ' die ': 3, ' das ': 3, ' und ': 3, ' mit ': 3, ' für ': 3
            }
            
            # Strong English indicators for LinkedIn job postings
            english_indicators = {
                ' ltd': 10, ' inc': 10, ' corp': 8, ' llc': 8,
                'we are looking': 8, 'you will': 6, 'experience in': 6, 'for our': 6,
                'skills required': 6, 'responsibilities': 5, 'requirements': 5,
                'developer': 6, 'engineer': 6, 'manager': 5, 'analyst': 5,
                'opportunity': 5, 'position': 5, 'team': 5, 'company': 5,
                'you should': 5, 'you must': 5, 'we offer': 5, 'we provide': 5,
                ' the ': 3, ' and ': 3, ' with ': 3, ' for ': 3, ' from ': 3, ' to ': 3
            }
            
            # Calculate scores
            german_score = sum(weight for indicator, weight in german_indicators.items() if indicator in text_to_analyze)
            english_score = sum(weight for indicator, weight in english_indicators.items() if indicator in text_to_analyze)
            
            # LinkedIn-specific patterns
            linkedin_german_patterns = [
                r'\bder\b', r'\bdie\b', r'\bdas\b', r'\bund\b', r'\bmit\b', r'\bfür\b',
                r'\bvon\b', r'\bzu\b', r'\bbei\b', r'\bnach\b', r'\büber\b', r'\bauf\b'
            ]
            linkedin_english_patterns = [
                r'\bthe\b', r'\band\b', r'\bwith\b', r'\bfor\b', r'\bfrom\b',
                r'\bto\b', r'\bat\b', r'\bafter\b', r'\bover\b', r'\bon\b'
            ]
            
            # Count pattern matches
            import re
            german_pattern_count = sum(len(re.findall(pattern, text_to_analyze)) for pattern in linkedin_german_patterns)
            english_pattern_count = sum(len(re.findall(pattern, text_to_analyze)) for pattern in linkedin_english_patterns)
            
            # Weighted scoring for LinkedIn
            total_german_score = german_score + german_pattern_count * 0.5
            total_english_score = english_score + english_pattern_count * 0.5
            
            # Determine language with LinkedIn-specific thresholds
            if total_german_score > total_english_score and total_german_score >= 1.5:
                return 'de'
            elif total_english_score > total_german_score and total_english_score >= 1.5:
                return 'en'
            else:
                # If scores are close or low, check for explicit language mentions
                if any(phrase in text_to_analyze for phrase in ['deutsch', 'german', 'deutschland']):
                    return 'de'
                elif any(phrase in text_to_analyze for phrase in ['english', 'international', 'global']):
                    return 'en'
                else:
                    # For LinkedIn, default to English if unclear (most LinkedIn jobs are international)
                    return 'en'
                    
        except Exception as e:
            print(f"⚠️ LinkedIn language detection error: {e}")
            return 'unknown'