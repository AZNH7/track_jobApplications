"""
Ignored Jobs Table

Handles all operations related to the ignored_jobs table.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from .base_table import BaseTable


class IgnoredJobsTable(BaseTable):
    """Handles ignored_jobs table operations."""
    
    def create_table(self, cursor) -> None:
        """Create the ignored_jobs table."""
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ignored_jobs (
                id SERIAL PRIMARY KEY,
                job_listing_id INTEGER REFERENCES job_listings(id) ON DELETE CASCADE,
                reason TEXT,
                ignored_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    
    def create_indexes(self, cursor) -> None:
        """Create indexes for ignored_jobs table."""
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_ignored_jobs_job_id ON ignored_jobs(job_listing_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_ignored_jobs_ignored_at ON ignored_jobs(ignored_at)')
    
    def ignore_job(self, job_listing_id: int, reason: str = None) -> bool:
        """Add a job to the ignored list."""
        try:
            query = """
                INSERT INTO ignored_jobs (job_listing_id, reason)
                VALUES (%s, %s)
                ON CONFLICT (job_listing_id) DO UPDATE SET
                    reason = EXCLUDED.reason,
                    ignored_at = CURRENT_TIMESTAMP
            """
            self.execute_query(query, (job_listing_id, reason))
            return True
            
        except Exception as e:
            self.log_error("ignore_job", e)
            return False
    
    def unignore_job(self, ignored_job_id: int) -> bool:
        """Remove a job from the ignored list."""
        try:
            query = "DELETE FROM ignored_jobs WHERE id = %s"
            self.execute_query(query, (ignored_job_id,))
            return True
            
        except Exception as e:
            self.log_error("unignore_job", e)
            return False
    
    def get_ignored_jobs(self) -> List[Dict[str, Any]]:
        """Get all ignored jobs with job listing details."""
        try:
            query = """
                SELECT 
                    ij.id,
                    ij.job_listing_id,
                    ij.reason,
                    ij.ignored_at,
                    jl.title,
                    jl.company,
                    jl.location,
                    jl.url
                FROM ignored_jobs ij
                LEFT JOIN job_listings jl ON ij.job_listing_id = jl.id
                ORDER BY ij.ignored_at DESC
            """
            results = self.execute_query(query, fetch='all')
            return [dict(row) for row in results] if results else []
            
        except Exception as e:
            self.log_error("get_ignored_jobs", e)
            return []
    
    def is_job_ignored(self, job_listing_id: int) -> bool:
        """Check if a job is ignored."""
        try:
            query = "SELECT COUNT(*) FROM ignored_jobs WHERE job_listing_id = %s"
            result = self.execute_query(query, (job_listing_id,), fetch='one')
            return result[0] > 0 if result else False
            
        except Exception as e:
            self.log_error("is_job_ignored", e)
            return False
    
    def clear_old_ignored_jobs(self, days_old: int) -> int:
        """Clear old ignored jobs."""
        try:
            query = "DELETE FROM ignored_jobs WHERE ignored_at < NOW() - INTERVAL '%s days'"
            self.execute_query(query, (days_old,))
            return 0  # Return deleted count if needed
            
        except Exception as e:
            self.log_error("clear_old_ignored_jobs", e)
            return 0
