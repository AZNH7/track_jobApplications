"""
Smart CloudFlare Client - Better handling of Indeed CloudFlare challenges
Implements intelligent retry strategies and session management
"""

import requests
import time
import random
import logging
from typing import Dict, List, Optional, Tuple
import json
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

class SmartCloudFlareClient:
    """
    Intelligent client for handling CloudFlare challenges with better retry logic
    """
    
    def __init__(self, flaresolverr_urls: List[str]):
        self.flaresolverr_urls = flaresolverr_urls
        self.session_pools = {url: {} for url in flaresolverr_urls}  # Track sessions per instance
        self.instance_health = {url: True for url in flaresolverr_urls}  # Track instance health
        self.last_health_check = {url: 0 for url in flaresolverr_urls}
        self.request_counts = {url: 0 for url in flaresolverr_urls}  # Load balancing
        
        # Smart retry configuration
        self.max_retries = 3
        self.base_timeout = 300  # 5 minutes
        self.max_timeout = 900   # 15 minutes
        self.backoff_multiplier = 1.5
        self.health_check_interval = 300  # 5 minutes
        
    def _check_instance_health(self, url: str) -> bool:
        """Check if a FlareSolverr instance is healthy"""
        current_time = time.time()
        
        # Skip if recently checked
        if current_time - self.last_health_check[url] < self.health_check_interval:
            return self.instance_health[url]
            
        try:
            response = requests.get(f"{url}/v1", timeout=10)
            healthy = response.status_code in [405, 200]  # 405 is expected for GET
            self.instance_health[url] = healthy
            self.last_health_check[url] = current_time
            
            if healthy:
                logger.info(f"Instance {url} is healthy")
            else:
                logger.warning(f"Instance {url} health check failed: {response.status_code}")
                
            return healthy
            
        except Exception as e:
            logger.error(f"Health check failed for {url}: {e}")
            self.instance_health[url] = False
            self.last_health_check[url] = current_time
            return False
    
    def _get_best_instance(self) -> Optional[str]:
        """Get the best available FlareSolverr instance based on health and load"""
        healthy_instances = []
        
        for url in self.flaresolverr_urls:
            if self._check_instance_health(url):
                healthy_instances.append(url)
                
        if not healthy_instances:
            logger.error("No healthy FlareSolverr instances available!")
            return None
            
        # Choose instance with lowest request count (load balancing)
        best_instance = min(healthy_instances, key=lambda url: self.request_counts[url])
        logger.debug(f"Selected instance: {best_instance} (load: {self.request_counts[best_instance]})")
        
        return best_instance
    
    def _create_session(self, instance_url: str, session_id: str) -> bool:
        """Create a new session on the specified instance"""
        try:
            payload = {
                "cmd": "sessions.create",
                "session": session_id
            }
            
            response = requests.post(
                f"{instance_url}/v1",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("status") == "ok":
                    logger.info(f"Created session {session_id} on {instance_url}")
                    self.session_pools[instance_url][session_id] = time.time()
                    return True
                    
            logger.warning(f"Failed to create session {session_id}: {response.text}")
            return False
            
        except Exception as e:
            logger.error(f"Error creating session {session_id}: {e}")
            return False
    
    def _cleanup_old_sessions(self, instance_url: str):
        """Clean up old sessions to prevent memory leaks"""
        current_time = time.time()
        session_max_age = 3600  # 1 hour
        
        old_sessions = [
            session_id for session_id, created_time in self.session_pools[instance_url].items()
            if current_time - created_time > session_max_age
        ]
        
        for session_id in old_sessions:
            try:
                payload = {
                    "cmd": "sessions.destroy",
                    "session": session_id
                }
                
                requests.post(f"{instance_url}/v1", json=payload, timeout=10)
                del self.session_pools[instance_url][session_id]
                logger.info(f"Cleaned up old session {session_id}")
                
            except Exception as e:
                logger.warning(f"Error cleaning up session {session_id}: {e}")
    
    def smart_request(self, url: str, session_prefix: str = "smart_session") -> Tuple[bool, Optional[Dict]]:
        """
        Make a smart request with intelligent retry and session management
        """
        session_id = f"{session_prefix}_{int(time.time())}_{random.randint(1000, 9999)}"
        
        for attempt in range(self.max_retries):
            instance_url = self._get_best_instance()
            if not instance_url:
                logger.error("No healthy instances available for request")
                time.sleep(30)  # Wait before retrying
                continue
                
            # Clean up old sessions periodically
            if random.random() < 0.1:  # 10% chance
                self._cleanup_old_sessions(instance_url)
            
            # Create session
            if not self._create_session(instance_url, session_id):
                logger.warning(f"Failed to create session on {instance_url}, trying next instance")
                continue
            
            # Calculate timeout based on attempt
            timeout = min(
                self.base_timeout * (self.backoff_multiplier ** attempt),
                self.max_timeout
            )
            
            try:
                logger.info(f"Attempt {attempt + 1}/{self.max_retries}: Requesting {url} with {timeout}s timeout")
                
                # Make the actual request
                payload = {
                    "cmd": "request.get",
                    "url": url,
                    "session": session_id,
                    "maxTimeout": int(timeout * 1000)  # Convert to milliseconds
                }
                
                response = requests.post(
                    f"{instance_url}/v1",
                    json=payload,
                    timeout=timeout + 30  # Add buffer for network overhead
                )
                
                self.request_counts[instance_url] += 1
                
                if response.status_code == 200:
                    result = response.json()
                    
                    if result.get("status") == "ok":
                        solution = result.get("solution", {})
                        if solution.get("status") == 200:
                            logger.info(f"✅ Successfully handled CloudFlare challenge for {url}")
                            
                            # Clean up session
                            try:
                                cleanup_payload = {
                                    "cmd": "sessions.destroy",
                                    "session": session_id
                                }
                                requests.post(f"{instance_url}/v1", json=cleanup_payload, timeout=10)
                            except Exception:
                                pass  # Ignore cleanup errors
                                
                            return True, result
                        else:
                            logger.warning(f"Request failed with status: {solution.get('status')}")
                    else:
                        logger.warning(f"FlareSolverr error: {result.get('message', 'Unknown error')}")
                else:
                    logger.warning(f"HTTP error {response.status_code}: {response.text}")
                    
            except requests.exceptions.Timeout:
                logger.warning(f"⏰ Timeout after {timeout}s on attempt {attempt + 1}")
                
            except Exception as e:
                logger.error(f"❌ Error on attempt {attempt + 1}: {e}")
                
            # Mark instance as potentially unhealthy if it fails
            if attempt == self.max_retries - 1:
                self.instance_health[instance_url] = False
                self.last_health_check[instance_url] = 0  # Force recheck
            
            # Exponential backoff between retries
            if attempt < self.max_retries - 1:
                wait_time = (2 ** attempt) + random.uniform(1, 5)
                logger.info(f"💤 Waiting {wait_time:.1f}s before retry...")
                time.sleep(wait_time)
        
        logger.error(f"❌ All attempts failed for {url}")
        return False, None
    
    def get_instance_stats(self) -> Dict:
        """Get statistics about instance usage and health"""
        return {
            "instance_health": self.instance_health.copy(),
            "request_counts": self.request_counts.copy(),
            "session_counts": {url: len(sessions) for url, sessions in self.session_pools.items()},
            "healthy_instances": sum(1 for healthy in self.instance_health.values() if healthy),
            "total_instances": len(self.flaresolverr_urls)
        } 