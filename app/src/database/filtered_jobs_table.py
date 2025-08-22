"""
Filtered Jobs Table

Handles all operations related to the filtered_jobs table.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from .base_table import BaseTable


class FilteredJobsTable(BaseTable):
    """Handles filtered_jobs table operations."""
    
    def create_table(self, cursor) -> None:
        """Create the filtered_jobs table."""
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS filtered_jobs (
                id SERIAL PRIMARY KEY,
                job_listing_id INTEGER REFERENCES job_listings(id) ON DELETE CASCADE,
                filter_reason TEXT,
                filtered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    
    def create_indexes(self, cursor) -> None:
        """Create indexes for filtered_jobs table."""
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_filtered_jobs_job_id ON filtered_jobs(job_listing_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_filtered_jobs_filtered_at ON filtered_jobs(filtered_at)')
    
    def add_filtered_job(self, job_listing_id: int, filter_reason: str) -> bool:
        """Add a job to the filtered list."""
        try:
            query = """
                INSERT INTO filtered_jobs (job_listing_id, filter_reason)
                VALUES (%s, %s)
                ON CONFLICT (job_listing_id) DO UPDATE SET
                    filter_reason = EXCLUDED.filter_reason,
                    filtered_at = CURRENT_TIMESTAMP
            """
            self.execute_query(query, (job_listing_id, filter_reason))
            return True
            
        except Exception as e:
            self.log_error("add_filtered_job", e)
            return False
    
    def get_filtered_jobs(self) -> List[Dict[str, Any]]:
        """Get all filtered jobs with job listing details."""
        try:
            query = """
                SELECT 
                    fj.id,
                    fj.job_listing_id,
                    fj.filter_reason,
                    fj.filtered_at,
                    jl.title,
                    jl.company,
                    jl.location,
                    jl.url
                FROM filtered_jobs fj
                LEFT JOIN job_listings jl ON fj.job_listing_id = jl.id
                ORDER BY fj.filtered_at DESC
            """
            results = self.execute_query(query, fetch='all')
            return [dict(row) for row in results] if results else []
            
        except Exception as e:
            self.log_error("get_filtered_jobs", e)
            return []
    
    def is_job_filtered(self, job_listing_id: int) -> bool:
        """Check if a job is filtered."""
        try:
            query = "SELECT COUNT(*) FROM filtered_jobs WHERE job_listing_id = %s"
            result = self.execute_query(query, (job_listing_id,), fetch='one')
            return result[0] > 0 if result else False
            
        except Exception as e:
            self.log_error("is_job_filtered", e)
            return False
    
    def remove_filtered_job(self, filtered_job_id: int) -> bool:
        """Remove a job from the filtered list."""
        try:
            query = "DELETE FROM filtered_jobs WHERE id = %s"
            self.execute_query(query, (filtered_job_id,))
            return True
            
        except Exception as e:
            self.log_error("remove_filtered_job", e)
            return False
    
    def clear_old_filtered_jobs(self, days_old: int) -> int:
        """Clear old filtered jobs."""
        try:
            query = "DELETE FROM filtered_jobs WHERE filtered_at < NOW() - INTERVAL '%s days'"
            self.execute_query(query, (days_old,))
            return 0  # Return deleted count if needed
            
        except Exception as e:
            self.log_error("clear_old_filtered_jobs", e)
            return 0
