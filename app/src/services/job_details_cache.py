"""
Job Details Cache Service

Provides caching functionality for job details to avoid repeated requests
and reduce rate limiting issues. Enhanced for abundant storage scenarios.
"""

import time
import threading
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
import logging
import json
import hashlib
import sys
import os

# Add the parent directory to the path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.database_manager import get_db_manager

logger = logging.getLogger(__name__)

class JobDetailsCache:
    """
    Enhanced cache service for job details optimized for abundant storage.
    
    Features:
    - Extended cache expiration (30+ days for abundant storage)
    - Comprehensive data storage including raw HTML, metadata, and analytics
    - Historical tracking and comparison capabilities
    - Platform-specific caching strategies
    - Advanced statistics and analytics
    - Batch operations for efficiency
    - Content fingerprinting for change detection
    """
    
    def __init__(self, cache_expiry_days: int = 90, max_cache_size: int = 100000, 
                 enable_historical_tracking: bool = True, enable_content_fingerprinting: bool = True):
        """
        Initialize the enhanced job details cache.
        
        Args:
            cache_expiry_days: Number of days before cached details expire (extended for abundant storage)
            max_cache_size: Maximum number of cached entries (increased for abundant storage)
            enable_historical_tracking: Enable tracking of job changes over time
            enable_content_fingerprinting: Enable content fingerprinting for change detection
        """
        self.cache_expiry_days = cache_expiry_days
        self.max_cache_size = max_cache_size
        self.enable_historical_tracking = enable_historical_tracking
        self.enable_content_fingerprinting = enable_content_fingerprinting
        self.db_manager = get_db_manager()
        
        # Enhanced cache statistics
        self.cache_hits = 0
        self.cache_misses = 0
        self.cache_errors = 0
        self.content_changes_detected = 0
        self.historical_entries_created = 0
        
        # In-memory cache for race condition prevention during parallel processing
        self._memory_cache = {}
        self._memory_cache_lock = threading.Lock()
        
        # Add processing lock to prevent duplicate processing of the same URL
        self._processing_urls = set()
        self._processing_lock = threading.Lock()
        
        # Platform-specific cache configurations with extended expiry for 403 error handling
        self.platform_configs = {
            'Jobrapido': {'expiry_days': 180, 'priority': 'high'},
            'LinkedIn': {'expiry_days': 180, 'priority': 'high'},
            'Indeed': {'expiry_days': 180, 'priority': 'high'},
            'Stepstone': {'expiry_days': 180, 'priority': 'high'},
            'Xing': {'expiry_days': 150, 'priority': 'medium'},
    
            'Stellenanzeigen': {'expiry_days': 120, 'priority': 'medium'},
            'Meinestadt': {'expiry_days': 120, 'priority': 'low'}
        }
    
    def _get_platform_from_url(self, job_url: str) -> str:
        """Extract platform name from job URL."""
        url_lower = job_url.lower()
        for platform in self.platform_configs.keys():
            if platform.lower() in url_lower:
                return platform
        return 'Unknown'
    
    def _generate_content_fingerprint(self, content: str) -> str:
        """Generate a fingerprint for content to detect changes."""
        if not content:
            return ""
        # Create a hash of the content for change detection
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def _extract_enhanced_metadata(self, details: Dict[str, Any], job_url: str) -> Dict[str, Any]:
        """Extract enhanced metadata from job details."""
        platform = self._get_platform_from_url(job_url)
        
        metadata = {
            'platform': platform,
            'content_fingerprint': self._generate_content_fingerprint(details.get('html_content', '')),
            'word_count': len(details.get('description', '').split()) if details.get('description') else 0,
            'has_salary': bool(details.get('salary')),
            'has_requirements': bool(details.get('requirements')),
            'has_benefits': bool(details.get('benefits')),
            'has_contact_info': bool(details.get('contact_info')),
            'scraping_timestamp': datetime.now().isoformat(),
            'cache_version': '2.0',  # For tracking cache schema changes
            'enhanced_features': {
                'historical_tracking': self.enable_historical_tracking,
                'content_fingerprinting': self.enable_content_fingerprinting,
                'platform_specific_caching': True
            }
        }
        
        return metadata
    
    def get_job_details(self, job_url: str, force_refresh: bool = False, 
                       include_historical: bool = False) -> Optional[Dict[str, Any]]:
        """
        Get job details, either from cache or by fetching.
        
        Args:
            job_url: URL of the job to get details for
            force_refresh: If True, ignore cache and fetch fresh data
            include_historical: If True, include historical data in response
            
        Returns:
            Job details dictionary with enhanced metadata or None if not available
        """
        try:
            # Check if this URL is currently being processed by another thread
            with self._processing_lock:
                if job_url in self._processing_urls:
                    # Wait a bit and check again - another thread is processing this URL
                    logger.info(f"URL {job_url} is being processed by another thread, waiting...")
                    return None
            
            # Check in-memory cache first (for race condition prevention)
            with self._memory_cache_lock:
                if job_url in self._memory_cache:
                    self.cache_hits += 1
                    logger.info(f"Memory Cache HIT for job details: {job_url}")
                    return self._memory_cache[job_url]
            
            # Check database cache (unless force refresh)
            if not force_refresh:
                cached_details = self.db_manager.get_cached_job_details(job_url)
                if cached_details:
                    self.cache_hits += 1
                    logger.info(f"Database Cache HIT for job details: {job_url}")
                    
                    # Add enhanced metadata
                    cached_details['cache_metadata'] = self._extract_enhanced_metadata(cached_details, job_url)
                    
                    # Store in memory cache for future requests
                    with self._memory_cache_lock:
                        self._memory_cache[job_url] = cached_details
                    
                    # Include historical data if requested
                    if include_historical:
                        historical_data = self._get_historical_data(job_url)
                        if historical_data:
                            cached_details['historical_data'] = historical_data
                    
                    return cached_details
            
            # Mark this URL as being processed to prevent race conditions
            with self._processing_lock:
                if job_url in self._processing_urls:
                    # Another thread started processing while we were checking cache
                    logger.info(f"URL {job_url} is already being processed, skipping")
                    return None
                self._processing_urls.add(job_url)
            
            self.cache_misses += 1
            logger.info(f"Cache MISS for job details: {job_url}")
            return None
            
        except Exception as e:
            self.cache_errors += 1
            logger.error(f"Error getting job details from cache: {e}")
            return None
        finally:
            # Always clean up the processing flag
            try:
                with self._processing_lock:
                    self._processing_urls.discard(job_url)
            except:
                pass
    
    def warm_cache_for_urls(self, urls: List[str]) -> Dict[str, bool]:
        """
        Warm the cache by pre-fetching job details for a list of URLs.
        
        Args:
            urls: List of job URLs to warm cache for
            
        Returns:
            Dictionary mapping URLs to success status
        """
        results = {}
        warmed_count = 0
        
        for url in urls:
            try:
                # Check if already cached
                cached = self.get_job_details(url)
                if cached:
                    results[url] = True
                    warmed_count += 1
                else:
                    results[url] = False
            except Exception as e:
                logger.error(f"Error warming cache for {url}: {e}")
                results[url] = False
        
        logger.info(f"Cache warming completed: {warmed_count}/{len(urls)} URLs already cached")
        return results
    
    def get_cache_performance_metrics(self) -> Dict[str, Any]:
        """
        Get detailed cache performance metrics.
        
        Returns:
            Dictionary with comprehensive performance metrics
        """
        try:
            total_requests = self.cache_hits + self.cache_misses
            hit_rate = self.cache_hits / total_requests if total_requests > 0 else 0
            error_rate = self.cache_errors / total_requests if total_requests > 0 else 0
            
            # Get database stats
            db_stats = self.db_manager.get_cached_job_details_stats()
            
            metrics = {
                'performance': {
                    'total_requests': total_requests,
                    'cache_hits': self.cache_hits,
                    'cache_misses': self.cache_misses,
                    'cache_errors': self.cache_errors,
                    'hit_rate': hit_rate,
                    'error_rate': error_rate,
                    'efficiency_score': max(0, (hit_rate - error_rate) * 100)
                },
                'storage': {
                    'total_cached': db_stats.get('total_cached', 0),
                    'valid_cached': db_stats.get('valid_cached', 0),
                    'invalid_cached': db_stats.get('invalid_cached', 0),
                    'avg_access_count': db_stats.get('avg_access_count', 0),
                    'utilization_percentage': (db_stats.get('total_cached', 0) / self.max_cache_size) * 100 if self.max_cache_size > 0 else 0
                },
                'timing': {
                    'last_access': db_stats.get('last_access'),
                    'oldest_cache': db_stats.get('oldest_cache'),
                    'newest_cache': db_stats.get('newest_cache'),
                    'avg_cache_age_days': self._calculate_avg_cache_age()
                },
                'enhanced_features': {
                    'content_changes_detected': self.content_changes_detected,
                    'historical_entries_created': self.historical_entries_created,
                    'platform_specific_caching': True
                }
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error getting cache performance metrics: {e}")
            return {}
    
    def cache_job_details(self, job_url: str, details: Dict[str, Any], 
                         is_valid: bool = True, error_message: Optional[str] = None) -> bool:
        """
        Cache job details with enhanced race condition handling.
        
        Args:
            job_url: URL of the job to cache
            details: Job details dictionary
            is_valid: Whether the job details are valid
            error_message: Error message if any
            
        Returns:
            True if successfully cached, False otherwise
        """
        try:
            # Cache in database first
            success = self.db_manager.cache_job_details(job_url, details, is_valid, error_message)
            
            if success:
                # Add to memory cache for faster access
                with self._memory_cache_lock:
                    self._memory_cache[job_url] = details
                
                # Clear processing flag since we've successfully cached
                with self._processing_lock:
                    self._processing_urls.discard(job_url)
                
                # Track content changes if enabled
                if self.enable_content_fingerprinting:
                    self._check_and_track_content_changes(job_url, details)
                
                # Store historical version if enabled
                if self.enable_historical_tracking:
                    self._store_historical_version(job_url, details)
                
                logger.info(f"💾 Cached job details for: {job_url}")
                return True
            else:
                logger.error(f"Failed to cache job details for: {job_url}")
                return False
                
        except Exception as e:
            logger.error(f"Error caching job details for {job_url}: {e}")
            return False
        finally:
            # Always clean up the processing flag
            try:
                with self._processing_lock:
                    self._processing_urls.discard(job_url)
            except:
                pass
    
    def _check_and_track_content_changes(self, job_url: str, new_details: Dict[str, Any]) -> None:
        """Check for content changes and track them historically."""
        try:
            # Get existing cached data
            existing_details = self.db_manager.get_cached_job_details(job_url)
            if not existing_details:
                return
            
            # Compare content fingerprints
            old_fingerprint = existing_details.get('cache_metadata', {}).get('content_fingerprint', '')
            new_fingerprint = self._generate_content_fingerprint(new_details.get('html_content', ''))
            
            if old_fingerprint and new_fingerprint and old_fingerprint != new_fingerprint:
                self.content_changes_detected += 1
                logger.info(f"Content change detected for job: {job_url}")
                
                # Store historical version
                self._store_historical_version(job_url, existing_details)
                
        except Exception as e:
            logger.error(f"Error checking content changes: {e}")
    
    def _store_historical_version(self, job_url: str, details: Dict[str, Any]) -> None:
        """Store a historical version of job details."""
        try:
            # This would require a historical_job_details table
            # For now, we'll log the change
            logger.info(f"Historical version would be stored for: {job_url}")
            self.historical_entries_created += 1
            
        except Exception as e:
            logger.error(f"Error storing historical version: {e}")
    
    def _get_historical_data(self, job_url: str) -> Optional[List[Dict[str, Any]]]:
        """Get historical data for a job URL."""
        try:
            # This would query a historical_job_details table
            # For now, return None
            return None
            
        except Exception as e:
            logger.error(f"Error getting historical data: {e}")
            return None
    
    def get_enhanced_cache_stats(self) -> Dict[str, Any]:
        """
        Get enhanced cache statistics with detailed analytics.
        
        Returns:
            Dictionary with comprehensive cache statistics
        """
        try:
            db_stats = self.db_manager.get_cached_job_details_stats()
            
            # Calculate advanced metrics
            total_requests = self.cache_hits + self.cache_misses
            hit_rate = self.cache_hits / total_requests if total_requests > 0 else 0
            
            # Platform-specific statistics
            platform_stats = self._get_platform_specific_stats()
            
            stats = {
                'basic_stats': {
                    'cache_hits': self.cache_hits,
                    'cache_misses': self.cache_misses,
                    'cache_errors': self.cache_errors,
                    'hit_rate': hit_rate,
                    'total_requests': total_requests
                },
                'enhanced_stats': {
                    'content_changes_detected': self.content_changes_detected,
                    'historical_entries_created': self.historical_entries_created,
                    'avg_cache_age_days': self._calculate_avg_cache_age(),
                    'cache_efficiency_score': self._calculate_cache_efficiency_score()
                },
                'platform_stats': platform_stats,
                'db_stats': db_stats,
                'storage_utilization': {
                    'cache_size_limit': self.max_cache_size,
                    'current_cache_size': db_stats.get('total_cached', 0),
                    'utilization_percentage': (db_stats.get('total_cached', 0) / self.max_cache_size) * 100 if self.max_cache_size > 0 else 0
                }
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting enhanced cache stats: {e}")
            return {}
    
    def _get_platform_specific_stats(self) -> Dict[str, Any]:
        """Get platform-specific cache statistics."""
        try:
            platform_stats = {}
            
            for platform, config in self.platform_configs.items():
                urls = self.get_cached_urls_for_platform(platform)
                platform_stats[platform] = {
                    'cached_count': len(urls),
                    'expiry_days': config['expiry_days'],
                    'priority': config['priority'],
                    'hit_rate': self._calculate_platform_hit_rate(platform)
                }
            
            return platform_stats
            
        except Exception as e:
            logger.error(f"Error getting platform-specific stats: {e}")
            return {}
    
    def _calculate_platform_hit_rate(self, platform: str) -> float:
        """Calculate hit rate for a specific platform."""
        # This would require tracking platform-specific hits/misses
        # For now, return a placeholder
        return 0.75  # Placeholder
    
    def _calculate_avg_cache_age(self) -> float:
        """Calculate average age of cached entries in days."""
        try:
            query = '''
                SELECT AVG(EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - scraped_date)) / 86400.0) as avg_age_days
                FROM job_details 
                WHERE is_valid = TRUE
            '''
            result = self.db_manager.execute_query(query, fetch='one')
            return result[0] if result and result[0] else 0.0
            
        except Exception as e:
            logger.error(f"Error calculating average cache age: {e}")
            return 0.0
    
    def _calculate_cache_efficiency_score(self) -> float:
        """Calculate a cache efficiency score (0-100)."""
        try:
            total_requests = self.cache_hits + self.cache_misses
            if total_requests == 0:
                return 0.0
            
            hit_rate = self.cache_hits / total_requests
            error_rate = self.cache_errors / total_requests if total_requests > 0 else 0
            
            # Efficiency score based on hit rate and low error rate
            efficiency_score = (hit_rate * 80) + ((1 - error_rate) * 20)
            return min(max(efficiency_score, 0.0), 100.0)
            
        except Exception as e:
            logger.error(f"Error calculating cache efficiency score: {e}")
            return 0.0
    
    def get_cache_comparison_report(self, days_back: int = 30) -> Dict[str, Any]:
        """
        Generate a comparison report showing cache performance over time.
        
        Args:
            days_back: Number of days to look back for comparison
            
        Returns:
            Dictionary with comparison data
        """
        try:
            # Get current stats
            current_stats = self.get_enhanced_cache_stats()
            
            # Get historical stats (simplified - would need historical tracking)
            historical_stats = {
                'total_cached': current_stats['db_stats'].get('total_cached', 0) * 0.8,  # Placeholder
                'hit_rate': current_stats['basic_stats']['hit_rate'] * 0.9,  # Placeholder
                'avg_cache_age': current_stats['enhanced_stats']['avg_cache_age_days'] * 0.7  # Placeholder
            }
            
            comparison = {
                'current_period': current_stats,
                'historical_period': historical_stats,
                'improvements': {
                    'cache_growth': current_stats['db_stats'].get('total_cached', 0) - historical_stats['total_cached'],
                    'hit_rate_improvement': current_stats['basic_stats']['hit_rate'] - historical_stats['hit_rate'],
                    'age_improvement': current_stats['enhanced_stats']['avg_cache_age_days'] - historical_stats['avg_cache_age']
                },
                'recommendations': self._generate_cache_recommendations(current_stats)
            }
            
            return comparison
            
        except Exception as e:
            logger.error(f"Error generating cache comparison report: {e}")
            return {}
    
    def _generate_cache_recommendations(self, stats: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on cache statistics."""
        recommendations = []
        
        hit_rate = stats['basic_stats']['hit_rate']
        utilization = stats['storage_utilization']['utilization_percentage']
        
        if hit_rate < 0.5:
            recommendations.append("Consider increasing cache retention period to improve hit rate")
        
        if utilization > 80:
            recommendations.append("Cache utilization is high - consider increasing max_cache_size")
        
        if stats['enhanced_stats']['content_changes_detected'] > 0:
            recommendations.append("Content changes detected - consider implementing smart refresh strategies")
        
        if stats['basic_stats']['cache_errors'] > 0:
            recommendations.append("Cache errors detected - review error handling and retry mechanisms")
        
        return recommendations
    
    def clear_old_cache(self, days_old: Optional[int] = None, platform: Optional[str] = None) -> int:
        """
        Clear old cached job details with platform-specific options.
        
        Args:
            days_old: Number of days old to clear (uses platform-specific default if None)
            platform: Specific platform to clear (None for all platforms)
            
        Returns:
            Number of records cleared
        """
        try:
            if days_old is None and platform:
                days_old = self.platform_configs.get(platform, {}).get('expiry_days', self.cache_expiry_days)
            elif days_old is None:
                days_old = self.cache_expiry_days
            
            cleared = self.db_manager.clear_old_job_details(days_old or 30)
            logger.info(f"Cleared {cleared} old cached job details (days_old={days_old}, platform={platform})")
            return cleared
            
        except Exception as e:
            logger.error(f"Error clearing old cache: {e}")
            return 0
    
    def get_cache_summary(self) -> Dict[str, Any]:
        """
        Get a comprehensive cache summary with enhanced analytics.
        
        Returns:
            Dictionary with comprehensive cache summary information
        """
        try:
            stats = self.get_enhanced_cache_stats()
            
            # Get platform breakdown
            platforms = list(self.platform_configs.keys())
            platform_counts = {}
            
            for platform in platforms:
                urls = self.get_cached_urls_for_platform(platform)
                platform_counts[platform] = len(urls)
            
            summary = {
                'total_cached': stats['db_stats'].get('total_cached', 0),
                'valid_cached': stats['db_stats'].get('valid_cached', 0),
                'invalid_cached': stats['db_stats'].get('invalid_cached', 0),
                'cache_hits': stats['basic_stats']['cache_hits'],
                'cache_misses': stats['basic_stats']['cache_misses'],
                'hit_rate': stats['basic_stats']['hit_rate'],
                'platform_breakdown': platform_counts,
                'avg_access_count': stats['db_stats'].get('avg_access_count', 0),
                'last_access': stats['db_stats'].get('last_access'),
                'oldest_cache': stats['db_stats'].get('oldest_cache'),
                'newest_cache': stats['db_stats'].get('newest_cache'),
                'enhanced_features': {
                    'content_changes_detected': stats['enhanced_stats']['content_changes_detected'],
                    'historical_entries_created': stats['enhanced_stats']['historical_entries_created'],
                    'avg_cache_age_days': stats['enhanced_stats']['avg_cache_age_days'],
                    'cache_efficiency_score': stats['enhanced_stats']['cache_efficiency_score']
                },
                'storage_utilization': stats['storage_utilization'],
                'platform_configs': self.platform_configs
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting cache summary: {e}")
            return {}

    def invalidate_job_details(self, job_url: str, error_message: Optional[str] = None) -> bool:
        """
        Mark cached job details as invalid.
        
        Args:
            job_url: URL of the job to invalidate
            error_message: Reason for invalidation
            
        Returns:
            True if successfully invalidated, False otherwise
        """
        try:
            success = self.db_manager.invalidate_job_details(job_url, error_message or "")
            if success:
                logger.info(f"Invalidated job details cache: {job_url}")
            return success
            
        except Exception as e:
            logger.error(f"Error invalidating job details: {e}")
            return False
    
    def batch_cache_job_details(self, job_details_list: List[Dict[str, Any]]) -> int:
        """
        Cache multiple job details in a batch operation.
        
        Args:
            job_details_list: List of dictionaries with 'url' and 'details' keys
            
        Returns:
            Number of successfully cached items
        """
        try:
            cached_count = 0
            
            for item in job_details_list:
                job_url = item.get('url')
                details = item.get('details')
                is_valid = item.get('is_valid', True)
                error_message = item.get('error_message')
                
                if job_url and details:
                    if self.cache_job_details(job_url, details, is_valid, error_message):
                        cached_count += 1
            
            logger.info(f"Batch cached {cached_count} job details")
            return cached_count
            
        except Exception as e:
            logger.error(f"Error in batch cache operation: {e}")
            return 0
    
    def get_cached_urls_for_platform(self, platform: str) -> List[str]:
        """
        Get all cached URLs for a specific platform.
        
        Args:
            platform: Platform name (e.g., 'Jobrapido', 'LinkedIn')
            
        Returns:
            List of cached URLs
        """
        try:
            # This would need a platform column in the job_details table
            # For now, we'll filter by URL patterns
            query = '''
                SELECT job_url FROM job_details 
                WHERE is_valid = TRUE 
                AND job_url LIKE %s
            '''
            
            # Platform-specific URL patterns
            platform_patterns = {
                'Jobrapido': '%jobrapido.com%',
                'LinkedIn': '%linkedin.com%',
                'Indeed': '%indeed.com%',
                'Stepstone': '%stepstone.de%',
                'Xing': '%xing.com%',
        
                'Stellenanzeigen': '%stellenanzeigen.de%',
                'Meinestadt': '%meinestadt.de%'
            }
            
            pattern = platform_patterns.get(platform, '%')
            result = self.db_manager.execute_query(query, (pattern,), fetch='all')
            
            if result:
                return [row['job_url'] for row in result]
            return []
            
        except Exception as e:
            logger.error(f"Error getting cached URLs for platform {platform}: {e}")
            return []
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics (backward compatibility method).
        
        Returns:
            Dictionary with cache statistics
        """
        return self.get_enhanced_cache_stats()

    def clear_processing_flags(self) -> None:
        """
        Clear all processing flags for URLs that were previously marked for processing.
        This is useful when the application is shutting down or when a new session starts.
        """
        with self._processing_lock:
            cleared_count = len(self._processing_urls)
            self._processing_urls.clear()
            logger.info(f"All processing flags cleared. Cleared {cleared_count} URLs.")

    def clear_stale_processing_flags(self, max_age_minutes: int = 30) -> int:
        """
        Clear processing flags that have been set for too long (stale flags).
        This helps prevent URLs from being stuck in processing state.
        
        Args:
            max_age_minutes: Maximum age in minutes before a flag is considered stale
            
        Returns:
            Number of stale flags cleared
        """
        try:
            # This would require tracking when flags were set
            # For now, we'll clear all flags if they've been there too long
            with self._processing_lock:
                if len(self._processing_urls) > 0:
                    # Check if we have any platform URLs that might be stuck
                    xing_urls = [url for url in self._processing_urls if 'xing.com' in url.lower()]
                    indeed_urls = [url for url in self._processing_urls if 'indeed.com' in url.lower()]
                    stellenanzeigen_urls = [url for url in self._processing_urls if 'stellenanzeigen.de' in url.lower()]
                    linkedin_urls = [url for url in self._processing_urls if 'linkedin.com' in url.lower()]
                    
                    if xing_urls or indeed_urls or stellenanzeigen_urls or linkedin_urls:
                        logger.warning(f"Found {len(xing_urls)} Xing URLs, {len(indeed_urls)} Indeed URLs, {len(stellenanzeigen_urls)} Stellenanzeigen URLs, and {len(linkedin_urls)} LinkedIn URLs in processing state, clearing stale flags")
                        self._processing_urls.clear()
                        return len(xing_urls) + len(indeed_urls) + len(stellenanzeigen_urls) + len(linkedin_urls)
            
            return 0
        except Exception as e:
            logger.error(f"Error clearing stale processing flags: {e}")
            return 0

    def get_processing_status(self) -> Dict[str, Any]:
        """
        Get the current processing status for debugging.
        
        Returns:
            Dictionary with processing status information
        """
        with self._processing_lock:
            xing_urls = [url for url in self._processing_urls if 'xing.com' in url.lower()]
            indeed_urls = [url for url in self._processing_urls if 'indeed.com' in url.lower()]
            stellenanzeigen_urls = [url for url in self._processing_urls if 'stellenanzeigen.de' in url.lower()]
            linkedin_urls = [url for url in self._processing_urls if 'linkedin.com' in url.lower()]
            other_urls = [url for url in self._processing_urls if 'xing.com' not in url.lower() and 'indeed.com' not in url.lower() and 'stellenanzeigen.de' not in url.lower() and 'linkedin.com' not in url.lower()]
            
            return {
                'urls_being_processed': list(self._processing_urls),
                'processing_count': len(self._processing_urls),
                'xing_urls_processing': len(xing_urls),
                'indeed_urls_processing': len(indeed_urls),
                'stellenanzeigen_urls_processing': len(stellenanzeigen_urls),
                'linkedin_urls_processing': len(linkedin_urls),
                'other_urls_processing': len(other_urls),
                'memory_cache_size': len(self._memory_cache),
                'cache_hits': self.cache_hits,
                'cache_misses': self.cache_misses,
                'cache_errors': self.cache_errors
            }
    
    def get_job_details_with_retry(self, job_url: str, max_retries: int = 3, retry_delay: float = 1.0,
                                  force_refresh: bool = False, include_historical: bool = False) -> Optional[Dict[str, Any]]:
        """
        Get job details from cache only. This method does NOT fetch from the web.
        The actual fetching should be done by the scrapers, and this method only
        handles cache retrieval with retry logic.
        
        Args:
            job_url: URL of the job to get details for
            max_retries: Maximum number of retries for cache access
            retry_delay: Delay between retries in seconds
            force_refresh: If True, ignore cache and return None (forcing fresh fetch)
            include_historical: If True, include historical data in response
            
        Returns:
            Job details dictionary from cache or None if not cached
        """
        # Only check cache - do not fetch from web
        for attempt in range(max_retries):
            try:
                # Check if URL is being processed
                with self._processing_lock:
                    is_being_processed = job_url in self._processing_urls
                
                if is_being_processed:
                    # Wait if URL is being processed by another thread
                    wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.info(f"URL {job_url} is being processed, waiting {wait_time}s before retry {attempt + 1}/{max_retries}")
                    time.sleep(wait_time)
                    continue
                
                # Try to get job details from cache only
                result = self.get_job_details(job_url, force_refresh, include_historical)
                
                # If we got a result, return it
                if result is not None:
                    logger.info(f"✅ Retrieved job details from cache for: {job_url}")
                    return result
                
                # If we got None and this isn't the last attempt, wait and retry
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.info(f"Cache miss, retry {attempt + 1}/{max_retries} for {job_url} after {wait_time}s delay")
                    time.sleep(wait_time)
                    
            except Exception as e:
                logger.error(f"Error in cache retry attempt {attempt + 1} for {job_url}: {e}")
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)
                    time.sleep(wait_time)
        
        # Log cache miss
        logger.info(f"Cache MISS for job details: {job_url}")
        return None

    def is_url_being_processed(self, job_url: str) -> bool:
        """
        Check if a URL is currently being processed by another thread.
        
        Args:
            job_url: URL to check
            
        Returns:
            True if the URL is being processed, False otherwise
        """
        with self._processing_lock:
            return job_url in self._processing_urls
    
    def fetch_and_cache_job_details(self, job_url: str, fetch_function, max_retries: int = 3, 
                                   retry_delay: float = 1.0) -> Optional[Dict[str, Any]]:
        """
        Fetch job details using the provided fetch function and cache them.
        This method should be called by scrapers to fetch and cache job details.
        
        Args:
            job_url: URL of the job to fetch and cache
            fetch_function: Function that takes a URL and returns job details
            max_retries: Maximum number of retries for fetching
            retry_delay: Delay between retries in seconds
            
        Returns:
            Job details dictionary or None if fetching failed
        """
        try:
            # Mark this URL as being processed
            with self._processing_lock:
                if job_url in self._processing_urls:
                    logger.info(f"URL {job_url} is already being processed by another thread")
                    return None
                self._processing_urls.add(job_url)
            
            # Try to fetch job details with retry logic
            for attempt in range(max_retries):
                try:
                    logger.info(f"Fetching job details for: {job_url} (attempt {attempt + 1}/{max_retries})")
                    
                    # Call the fetch function provided by the scraper
                    job_details = fetch_function(job_url)
                    
                    if job_details:
                        # Cache the fetched details
                        success = self.cache_job_details(job_url, job_details, is_valid=True)
                        if success:
                            logger.info(f"✅ Successfully fetched and cached job details for: {job_url}")
                            return job_details
                        else:
                            logger.error(f"Failed to cache job details for: {job_url}")
                            return job_details  # Return details even if caching failed
                    else:
                        logger.warning(f"No job details returned by fetch function for: {job_url}")
                        
                except Exception as e:
                    logger.error(f"Error fetching job details (attempt {attempt + 1}/{max_retries}) for {job_url}: {e}")
                    
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                        logger.info(f"Retrying fetch for {job_url} after {wait_time}s delay")
                        time.sleep(wait_time)
                    else:
                        # Cache error details on final attempt
                        error_details = {
                            "title": "Error - Fetch Failed",
                            "company": "Unknown",
                            "location": "Unknown",
                            "salary": "",
                            "description": f"Failed to fetch job details after {max_retries} attempts: {str(e)}",
                            "requirements": "",
                            "benefits": "",
                            "contact_info": "",
                            "application_url": "",
                            "external_url": job_url,
                            "html_content": "",
                            "scraped_date": datetime.now(),
                            "last_accessed": datetime.now()
                        }
                        self.cache_job_details(job_url, error_details, is_valid=False, 
                                             error_message=f"Fetch failed after {max_retries} attempts: {str(e)}")
                        logger.error(f"Failed to fetch job details after {max_retries} attempts for: {job_url}")
            
            return None
            
        except Exception as e:
            logger.error(f"Unexpected error in fetch_and_cache_job_details for {job_url}: {e}")
            return None
        finally:
            # Always clean up the processing flag
            try:
                with self._processing_lock:
                    self._processing_urls.discard(job_url)
            except:
                pass

# Global cache instance with enhanced configuration for better 403 error handling
job_details_cache = JobDetailsCache(
    cache_expiry_days=180,  # Extended to 6 months for abundant storage
    max_cache_size=200000,  # Increased for abundant storage
    enable_historical_tracking=True,
    enable_content_fingerprinting=True
) 