"""
Base Scraper Class

Contains common functionality shared across all job scrapers.
"""

import logging
import requests
import time
import random
import os
import re
from datetime import datetime, timedelta
from urllib.parse import quote_plus, urlencode, unquote, urljoin, urlparse
from typing import List, Dict, Set, Optional, Any
import pandas as pd
from bs4 import BeautifulSoup
import json
from collections import Counter
from abc import ABC, abstractmethod

try:
    from constants import SESSION_403_WINDOW_SECS, SESSION_MAX_AGE_SECS
except ImportError:
    SESSION_403_WINDOW_SECS = 300
    SESSION_MAX_AGE_SECS = 1800

class BaseScraper(ABC):
    """Base class for all job scrapers with common functionality."""
    
    def __init__(self, debug: bool = False, use_flaresolverr: bool = True):
        """
        Initialize base scraper.
        
        Args:
            debug: Enable debug logging
            use_flaresolverr: Use FlareSolverr for requests (default: True)
        """
        self.debug = debug
        self.logger = logging.getLogger(__name__)
        self.use_flaresolverr = use_flaresolverr
        self.session = None
        self._session_start_time = None
        self._consecutive_403_errors = 0
        self._last_403_time = None
        self._session_refresh_threshold = SESSION_403_WINDOW_SECS
        self._init_scraper_session()

    def _init_scraper_session(self):
        """Initialize scraper session based on configuration."""
        if self.use_flaresolverr:
            self.logger.info("🔧 Using FlareSolverr session")
            # FlareSolverr is handled in get_page_flaresolverr
            self.session = requests.Session() 
        else:
            self.logger.info("🔧 Using standard requests session")
            self.session = requests.Session()
            self._session_start_time = time.time()

    def _should_refresh_session(self) -> bool:
        """Check if session should be refreshed based on health indicators."""
        if not self._session_start_time:
            return False
            
        current_time = time.time()
        
        # Refresh if we've had consecutive 403 errors recently
        if (self._consecutive_403_errors >= 3 and 
            self._last_403_time and 
            current_time - self._last_403_time < self._session_refresh_threshold):
            return True
            
        # Refresh session every 30 minutes as preventive measure
        if current_time - self._session_start_time > SESSION_MAX_AGE_SECS:
            return True
            
        return False

    def _refresh_session(self):
        """Refresh the session."""
        if self.debug:
            self.logger.info("🔄 Refreshing session...")
            
        try:
            # Close existing session if it exists
            if self.session and hasattr(self.session, 'close'):
                self.session.close()
                
            # Create new session
            self._init_scraper_session()
            
            # Reset error counters
            self._consecutive_403_errors = 0
            self._last_403_time = None
            
            if self.debug:
                self.logger.info("✅ Session refreshed successfully")
                
        except Exception as e:
            self.logger.error(f"❌ Error refreshing session: {e}")

    def get_page(self, url: str, **kwargs) -> Optional[requests.Response]:
        """
        Get a webpage using the configured session with enhanced error handling.
        
        Args:
            url: URL to fetch
            **kwargs: Additional arguments for the request
            
        Returns:
            Response object or None if an error occurs
        """
        if self.use_flaresolverr:
            return self._get_page_flaresolverr(url, **kwargs)

        # Check if session needs refreshing
        if self._should_refresh_session():
            self._refresh_session()

        if not self.session:
            self._init_scraper_session()
            if not self.session:
                return None
        
        try:
            # Standard request
            response = self.session.get(url, **kwargs)
            
            # Handle different response codes
            if response.status_code == 200:
                # Reset error counters on success
                self._consecutive_403_errors = 0
                return response
                
            elif response.status_code == 403:
                # Handle protection
                self._consecutive_403_errors += 1
                self._last_403_time = time.time()
                
                if self.debug:
                    self.logger.info(f"🚫 HTTP 403 detected for {url}")
                    self.logger.info(f"   Consecutive 403 errors: {self._consecutive_403_errors}")
                
                # Try session refresh if we have multiple 403s
                if self._consecutive_403_errors >= 2:
                    self._refresh_session()
                    # Retry with fresh session
                    try:
                        response = self.session.get(url, **kwargs)
                        if response.status_code == 200:
                            self._consecutive_403_errors = 0
                            return response
                    except Exception as retry_e:
                        if self.debug:
                            self.logger.warning(f"   ⚠️ Retry after refresh failed: {retry_e}")
                
                return response
                
            elif response.status_code == 429:
                # Rate limiting
                if self.debug:
                    self.logger.warning(f"⚠️ HTTP 429 (Rate Limited) for {url}")
                return response
                
            else:
                # Other status codes
                response.raise_for_status()
                return response
                
        except Exception as e:
            if self.debug:
                self.logger.error(f"❌ Error fetching {url}: {e}")
            return None

    def _get_page_flaresolverr(self, url: str, **kwargs) -> Optional[requests.Response]:
        """Get a webpage using FlareSolverr."""
        flaresolverr_url = os.getenv("FLARESOLVERR_URL")
        if not flaresolverr_url:
            self.logger.error("❌ FLARESOLVERR_URL not set, cannot use FlareSolverr.")
            return None
            
        payload = {
            'cmd': 'request.get',
            'url': url,
            'maxTimeout': kwargs.get('max_timeout', 60000)
        }
        
        try:
            response = requests.post(flaresolverr_url, json=payload, timeout=120)
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') == 'ok':
                solution = data.get('solution', {})
                if not solution:
                    self.logger.error(f"❌ FlareSolverr returned empty solution for URL: {url}")
                    return None
                
                # Create a mock response object
                mock_response = requests.Response()
                mock_response.status_code = solution.get('status', 200)
                
                # Handle case where response content might be None
                response_content = solution.get('response', '')
                if response_content is None:
                    self.logger.warning(f"⚠️ FlareSolverr returned None response content for URL: {url}")
                    response_content = ''
                mock_response._content = response_content.encode('utf-8')
                
                # Handle headers safely
                headers = solution.get('headers', {})
                if headers:
                    mock_response.headers.update(headers)
                
                return mock_response
            else:
                error_msg = data.get('message', 'Unknown error')
                self.logger.error(f"❌ FlareSolverr error for URL {url}: {error_msg}")
                return None
                
        except requests.exceptions.Timeout:
            self.logger.error(f"❌ FlareSolverr request timeout for URL: {url}")
            return None
        except requests.exceptions.RequestException as e:
            self.logger.error(f"❌ FlareSolverr request failed for URL {url}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"❌ FlareSolverr unexpected error for URL {url}: {e}")
            return None

    def get_soup(self, html_content: str) -> Optional[BeautifulSoup]:
        """Get BeautifulSoup object from HTML content."""
        if not html_content:
            return None
        try:
            return BeautifulSoup(html_content, 'html.parser')
        except Exception as e:
            if self.debug:
                self.logger.error(f"   ❌ Error creating BeautifulSoup object: {e}")
            return None

    def get_page_with_fallback(self, url: str, **kwargs) -> Optional[requests.Response]:
        """
        Get a webpage with fallback strategies.
        
        Args:
            url: URL to fetch
            **kwargs: Additional arguments for the request
            
        Returns:
            Response object or None if all strategies fail
        """
        # Try FlareSolverr first if enabled
        if self.use_flaresolverr:
            if self.debug:
                self.logger.info(f"🌐 Trying FlareSolverr for: {url}")
            
            response = self._get_page_flaresolverr(url, **kwargs)
            if response and response.status_code == 200:
                if self.debug:
                    self.logger.info(f"✅ FlareSolverr success for: {url}")
                return response
            elif self.debug:
                self.logger.error(f"❌ FlareSolverr failed for: {url}")
        
        # Fallback to standard session
        if self.debug:
            self.logger.info(f"🔄 Falling back to standard session for: {url}")
        
        return self.get_page(url, **kwargs)

    @abstractmethod
    def search_jobs(self, keywords: str, location: str, max_pages: int = 1, english_only: bool = False) -> List[Dict[str, Any]]:
        """Search for jobs with the given keywords and location."""
        pass

    def fetch_job_details(self, job_url: str) -> Optional[Dict[str, Any]]:
        """Fetch detailed information for a specific job."""
        pass

    @abstractmethod
    def get_platform_name(self) -> str:
        """Get the name of the job platform."""
        pass

    def close(self):
        """Close the scraper session."""
        if self.session:
            self.session.close() 