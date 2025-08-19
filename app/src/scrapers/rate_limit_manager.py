"""
Rate Limiting Manager

Provides centralized rate limiting functionality for all scrapers.
Optimized for FlareSolverr usage.
"""

import time
import random
from collections import defaultdict
from typing import Dict, List, Optional, Callable
import requests


class RateLimitManager:
    """Centralized rate limiting manager for all scrapers with FlareSolverr optimization."""
    
    def __init__(self):
        """Initialize the rate limit manager."""
        # Track request timestamps per domain
        self._request_timestamps = defaultdict(list)
        
        # Rate limit delays per domain (optimized for FlareSolverr)
        self._rate_limit_delays = {
            'jobrapido.com': 2.0,      # Reduced since FlareSolverr handles Cloudflare
            'indeed.com': 1.5,         # Reduced with FlareSolverr
            'linkedin.com': 5.0,       # Keep higher for LinkedIn's strict protection
            'stepstone.de': 1.5,       # Reduced with FlareSolverr
            'xing.com': 1.5,           # Reduced with FlareSolverr
        
            'stellenanzeigen.de': 1.5,
            'meinestadt.de': 1.5,
            'default': 1.5             # Default reduced with FlareSolverr
        }
        
        # Retry configuration (optimized for FlareSolverr)
        self._max_retries = 2          # Reduced since FlareSolverr handles retries internally
        self._backoff_multiplier = 1.3  # Reduced since FlareSolverr is more reliable
        self._max_backoff = 20.0        # Reduced since FlareSolverr handles challenges
        
        # Adaptive rate limiting
        self._consecutive_429_errors = defaultdict(int)
        self._last_429_time = defaultdict(float)
        self._adaptive_delay_multipliers = defaultdict(lambda: 1.0)
        
        # Enhanced domain-specific settings for FlareSolverr
        self._domain_settings = {
            'jobrapido.com': {
                'base_delay': 2.0,          # Optimized for FlareSolverr with Cloudflare bypass
                'max_retries': 2,           # Reduced since FlareSolverr handles internally
                'backoff_multiplier': 1.2,  # Gentle backoff with FlareSolverr
                'max_backoff': 20.0,        # Shorter max backoff
                'cloudflare_protected': True,
                'stealth_mode': False       # FlareSolverr handles stealth automatically
            },
            'linkedin.com': {
                'base_delay': 5.0,          # Keep higher for LinkedIn
                'max_retries': 3,
                'backoff_multiplier': 1.5,
                'max_backoff': 60.0,
                'cloudflare_protected': False,
                'stealth_mode': False
            },

            'indeed.com': {
                'base_delay': 1.5,          # Reduced with FlareSolverr
                'max_retries': 2,
                'backoff_multiplier': 1.2,
                'max_backoff': 15.0,
                'cloudflare_protected': True,
                'stealth_mode': False       # Indeed less aggressive with FlareSolverr
            },
            'stepstone.de': {
                'base_delay': 1.5,
                'max_retries': 2,
                'backoff_multiplier': 1.2,
                'max_backoff': 15.0,
                'cloudflare_protected': False,
                'stealth_mode': False
            },
            'xing.com': {
                'base_delay': 1.5,
                'max_retries': 2,
                'backoff_multiplier': 1.2,
                'max_backoff': 15.0,
                'cloudflare_protected': False,
                'stealth_mode': False
            },
            'stellenanzeigen.de': {
                'base_delay': 1.5,
                'max_retries': 2,
                'backoff_multiplier': 1.2,
                'max_backoff': 15.0,
                'cloudflare_protected': False,
                'stealth_mode': False
            },
            'meinestadt.de': {
                'base_delay': 1.5,
                'max_retries': 2,
                'backoff_multiplier': 1.2,
                'max_backoff': 15.0,
                'cloudflare_protected': False,
                'stealth_mode': False
            }
        }
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        if not url:
            return 'default'
        
        # Extract domain from URL
        if 'jobrapido.com' in url:
            return 'jobrapido.com'
        elif 'indeed.com' in url:
            return 'indeed.com'
        elif 'linkedin.com' in url:
            return 'linkedin.com'
        elif 'stepstone.de' in url:
            return 'stepstone.de'
        elif 'xing.com' in url:
            return 'xing.com'

        elif 'stellenanzeigen.de' in url:
            return 'stellenanzeigen.de'
        elif 'meinestadt.de' in url:
            return 'meinestadt.de'
        else:
            return 'default'
    
    def _get_domain_settings(self, domain: str) -> Dict:
        """Get domain-specific settings."""
        return self._domain_settings.get(domain, {
            'base_delay': self._rate_limit_delays.get(domain, self._rate_limit_delays['default']),
            'max_retries': self._max_retries,
            'backoff_multiplier': self._backoff_multiplier,
            'max_backoff': self._max_backoff,
            'cloudflare_protected': False,
            'stealth_mode': False
        })
    
    def _get_rate_limit_delay(self, url: str) -> float:
        """Get the appropriate rate limit delay for a URL."""
        domain = self._extract_domain(url)
        settings = self._get_domain_settings(domain)
        base_delay = settings['base_delay']
        
        # Apply stealth mode multiplier if enabled
        if settings.get('stealth_mode', False):
            base_delay *= random.uniform(1.2, 1.8)  # Add randomization for stealth
        
        # Apply adaptive delay multiplier if we've had recent 429 errors
        if self._consecutive_429_errors[domain] > 0:
            time_since_last_429 = time.time() - self._last_429_time[domain]
            if time_since_last_429 < 300:  # Within 5 minutes of last 429
                adaptive_delay = base_delay * self._adaptive_delay_multipliers[domain]
                return adaptive_delay
        
        return base_delay
    
    def enforce_rate_limit(self, url: str, debug: bool = False):
        """Enforce rate limiting for a specific URL with FlareSolverr optimization."""
        delay = self._get_rate_limit_delay(url)
        domain = self._extract_domain(url)
        settings = self._get_domain_settings(domain)
        
        # Check if we need to wait based on recent requests
        recent_requests = self._request_timestamps[domain]
        current_time = time.time()
        
        # Remove old timestamps (older than 2 minutes)
        recent_requests = [t for t in recent_requests if current_time - t < 120]
        self._request_timestamps[domain] = recent_requests
        
        # If we've made requests recently, wait
        if recent_requests:
            time_since_last = current_time - recent_requests[-1]
            if time_since_last < delay:
                wait_time = delay - time_since_last
                
                # Add extra message for Cloudflare-protected domains
                if settings.get('cloudflare_protected', False) and debug:
                    print(f"   🛡️ Cloudflare-protected domain: {domain}")
                    print(f"   ⏳ Enhanced rate limiting: waiting {wait_time:.1f}s")
                elif debug:
                    print(f"   ⏳ Rate limiting: waiting {wait_time:.1f}s before next request to {domain}")
                    
                time.sleep(wait_time)
        
        # Record this request
        self._request_timestamps[domain].append(time.time())
    
    def handle_429_error(self, url: str, attempt: int, debug: bool = False) -> bool:
        """Handle 429 error with exponential backoff optimized for FlareSolverr."""
        domain = self._extract_domain(url)
        settings = self._get_domain_settings(domain)
        
        self._consecutive_429_errors[domain] += 1
        self._last_429_time[domain] = time.time()
        
        # Increase adaptive delay multiplier (more conservative with FlareSolverr)
        self._adaptive_delay_multipliers[domain] = min(
            4.0, self._adaptive_delay_multipliers[domain] * 1.3  # Reduced multiplier
        )
        
        if attempt < settings['max_retries']:
            # Exponential backoff (more conservative with FlareSolverr)
            base_delay = self._get_rate_limit_delay(url)
            backoff_delay = min(
                base_delay * (settings['backoff_multiplier'] ** attempt),
                settings['max_backoff']
            )
            
            if debug:
                print(f"   ⚠️ 429 Error for {domain} (attempt {attempt + 1}/{settings['max_retries'] + 1})")
                if settings.get('cloudflare_protected', False):
                    print(f"   🛡️ Cloudflare domain - using optimized backoff")
                print(f"   🐌 Waiting {backoff_delay:.1f}s before retry...")
            
            time.sleep(backoff_delay)
            return True  # Retry
        else:
            if debug:
                print(f"   💥 Max retries reached for {domain}")
            return False  # Don't retry

    def handle_403_error(self, url: str, attempt: int, debug: bool = False) -> bool:
        """Handle 403 Cloudflare protection errors with FlareSolverr optimization."""
        domain = self._extract_domain(url)
        settings = self._get_domain_settings(domain)
        
        if debug:
            print(f"   🚫 HTTP 403 Forbidden for {domain}")
            if settings.get('cloudflare_protected', False):
                print(f"   🛡️ Cloudflare protection detected - FlareSolverr handling...")
        
        # For Cloudflare-protected domains, use shorter backoff since 
        # FlareSolverr should handle the challenge automatically
        if settings.get('cloudflare_protected', False):
            if attempt < settings['max_retries']:
                backoff_delay = min(5.0 * (attempt + 1), 15.0)  # Shorter delays
                if debug:
                    print(f"   🔄 Cloudflare retry in {backoff_delay:.1f}s...")
                time.sleep(backoff_delay)
                return True
        else:
            # Regular 403 handling for non-Cloudflare domains
            if attempt < settings['max_retries']:
                backoff_delay = min(
                    settings['base_delay'] * (settings['backoff_multiplier'] ** (attempt + 1)),
                    settings['max_backoff']
                )
                if debug:
                    print(f"   🐌 Waiting {backoff_delay:.1f}s before retry after 403...")
                time.sleep(backoff_delay)
                return True
        
        return False  # Don't retry
    
    def make_request_with_retry(self, session: requests.Session, url: str, 
                               method: str = 'GET', debug: bool = False, **kwargs) -> Optional[requests.Response]:
        """Make a request with retry logic and rate limiting optimized for FlareSolverr."""
        domain = self._extract_domain(url)
        settings = self._get_domain_settings(domain)
        
        for attempt in range(settings['max_retries'] + 1):
            try:
                # Enforce rate limiting
                self.enforce_rate_limit(url, debug)
                
                # Make the request
                if method.upper() == 'GET':
                    response = session.get(url, **kwargs)
                else:
                    response = session.request(method, url, **kwargs)
                
                # If successful, reset error tracking
                if response.status_code == 200:
                    self._consecutive_429_errors[domain] = 0
                    self._adaptive_delay_multipliers[domain] = max(
                        1.0, self._adaptive_delay_multipliers[domain] * 0.9
                    )
                    return response
                
                # Handle 429 errors
                if response.status_code == 429:
                    if not self.handle_429_error(url, attempt, debug):
                        return response  # Return the response even if it's 429
                    continue
                
                # Handle 403 errors (Cloudflare protection)
                if response.status_code == 403:
                    if not self.handle_403_error(url, attempt, debug):
                        return response  # Return the 403 response
                    continue
                
                # For other errors, raise the exception
                response.raise_for_status()
                return response
                
            except requests.exceptions.RequestException as e:
                if attempt < settings['max_retries']:
                    if debug:
                        print(f"   ⚠️ Request error for {domain} (attempt {attempt + 1}/{settings['max_retries'] + 1}): {e}")
                    time.sleep(random.uniform(1, 3))
                    continue
                else:
                    if debug:
                        print(f"   💥 Max retries reached for {domain}: {e}")
                    raise
        
        return None

    def get_domain_info(self, url: str) -> Dict:
        """Get information about domain settings for debugging."""
        domain = self._extract_domain(url)
        settings = self._get_domain_settings(domain)
        
        return {
            'domain': domain,
            'base_delay': settings['base_delay'],
            'cloudflare_protected': settings.get('cloudflare_protected', False),
            'stealth_mode': settings.get('stealth_mode', False),
            'consecutive_429_errors': self._consecutive_429_errors[domain],
            'adaptive_multiplier': self._adaptive_delay_multipliers[domain]
        }


# Global instance
rate_limit_manager = RateLimitManager() 