"""
Job Details Table

Handles all operations related to the job_details table for cached job information.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from .base_table import BaseTable


class JobDetailsTable(BaseTable):
    """Handles job_details table operations."""
    
    def create_table(self, cursor) -> None:
        """Create the job_details table."""
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS job_details (
                id SERIAL PRIMARY KEY,
                job_url TEXT UNIQUE NOT NULL,
                title TEXT,
                company TEXT,
                location TEXT,
                salary TEXT,
                description TEXT,
                requirements TEXT,
                benefits TEXT,
                contact_info TEXT,
                application_url TEXT,
                external_url TEXT,
                html_content TEXT,
                scraped_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                last_accessed TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                access_count INTEGER DEFAULT 0,
                is_valid BOOLEAN DEFAULT TRUE,
                error_message TEXT,
                cache_metadata JSONB
            )
        ''')
    
    def create_indexes(self, cursor) -> None:
        """Create indexes for job_details table."""
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_job_details_url ON job_details(job_url)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_job_details_last_accessed ON job_details(last_accessed)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_job_details_is_valid ON job_details(is_valid)')
    
    def cache_job_details(self, job_url: str, details: Dict[str, Any], 
                         is_valid: bool = True, error_message: str = None) -> bool:
        """Cache job details."""
        try:
            query = """
                INSERT INTO job_details (
                    job_url, title, company, location, salary, description,
                    requirements, benefits, contact_info, application_url, external_url,
                    html_content, is_valid, error_message, cache_metadata
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (job_url) DO UPDATE SET
                    title = EXCLUDED.title,
                    company = EXCLUDED.company,
                    location = EXCLUDED.location,
                    salary = EXCLUDED.salary,
                    description = EXCLUDED.description,
                    requirements = EXCLUDED.requirements,
                    benefits = EXCLUDED.benefits,
                    contact_info = EXCLUDED.contact_info,
                    application_url = EXCLUDED.application_url,
                    external_url = EXCLUDED.external_url,
                    html_content = EXCLUDED.html_content,
                    is_valid = EXCLUDED.is_valid,
                    error_message = EXCLUDED.error_message,
                    cache_metadata = EXCLUDED.cache_metadata,
                    last_accessed = CURRENT_TIMESTAMP,
                    access_count = job_details.access_count + 1
            """
            
            import json
            params = (
                job_url,
                details.get('title'),
                details.get('company'),
                details.get('location'),
                details.get('salary'),
                details.get('description'),
                details.get('requirements'),
                details.get('benefits'),
                details.get('contact_info'),
                details.get('application_url'),
                details.get('external_url'),
                details.get('html_content'),
                is_valid,
                error_message,
                json.dumps(details.get('cache_metadata', {}))
            )
            
            self.execute_query(query, params)
            return True
            
        except Exception as e:
            self.log_error("cache_job_details", e)
            return False
    
    def get_cached_job_details(self, job_url: str) -> Optional[Dict[str, Any]]:
        """Get cached job details."""
        try:
            query = """
                SELECT * FROM job_details 
                WHERE job_url = %s AND is_valid = TRUE
            """
            result = self.execute_query(query, (job_url,), fetch='one')
            
            if result:
                # Update access count and last accessed
                self._update_access_stats(job_url)
                return dict(result)
            
            return None
            
        except Exception as e:
            self.log_error("get_cached_job_details", e)
            return None
    
    def _update_access_stats(self, job_url: str) -> None:
        """Update access statistics for cached job details."""
        try:
            query = """
                UPDATE job_details 
                SET last_accessed = CURRENT_TIMESTAMP, access_count = access_count + 1
                WHERE job_url = %s
            """
            self.execute_query(query, (job_url,))
            
        except Exception as e:
            self.log_error("_update_access_stats", e)
    
    def invalidate_job_details(self, job_url: str, error_message: str = None) -> bool:
        """Mark cached job details as invalid."""
        try:
            query = """
                UPDATE job_details 
                SET is_valid = FALSE, error_message = %s
                WHERE job_url = %s
            """
            self.execute_query(query, (error_message, job_url))
            return True
            
        except Exception as e:
            self.log_error("invalidate_job_details", e)
            return False
    
    def clear_old_cache(self, days_old: int) -> int:
        """Clear old cached job details."""
        try:
            query = """
                DELETE FROM job_details 
                WHERE scraped_date < NOW() - INTERVAL '%s days'
            """
            self.execute_query(query, (days_old,))
            return 0  # Return deleted count if needed
            
        except Exception as e:
            self.log_error("clear_old_cache", e)
            return 0
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        try:
            query = """
                SELECT 
                    COUNT(*) as total_cached,
                    COUNT(*) FILTER (WHERE is_valid = TRUE) as valid_cached,
                    COUNT(*) FILTER (WHERE is_valid = FALSE) as invalid_cached,
                    AVG(access_count) as avg_access_count,
                    MAX(last_accessed) as last_access,
                    MIN(scraped_date) as oldest_cache,
                    MAX(scraped_date) as newest_cache
                FROM job_details
            """
            result = self.execute_query(query, fetch='one')
            
            if result:
                return {
                    'total_cached': result[0] or 0,
                    'valid_cached': result[1] or 0,
                    'invalid_cached': result[2] or 0,
                    'avg_access_count': float(result[3]) if result[3] else 0,
                    'last_access': result[4].isoformat() if result[4] else None,
                    'oldest_cache': result[5].isoformat() if result[5] else None,
                    'newest_cache': result[6].isoformat() if result[6] else None
                }
            
            return {}
            
        except Exception as e:
            self.log_error("get_cache_stats", e)
            return {}
