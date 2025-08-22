"""
Job Listings Table

Handles all operations related to the job_listings table.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from .base_table import BaseTable


class JobListingsTable(BaseTable):
    """Handles job_listings table operations."""
    
    def create_table(self, cursor) -> None:
        """Create the job_listings table."""
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS job_listings (
                id SERIAL PRIMARY KEY,
                title TEXT,
                company TEXT,
                location TEXT,
                salary TEXT,
                url TEXT UNIQUE,
                source TEXT,
                scraped_date TIMESTAMP,
                posted_date TEXT,
                description TEXT,
                language TEXT,
                job_snippet TEXT,
                llm_filtered BOOLEAN DEFAULT FALSE,
                llm_quality_score DECIMAL(3,2),
                llm_relevance_score DECIMAL(3,2),
                llm_reasoning TEXT
            )
        ''')
    
    def create_indexes(self, cursor) -> None:
        """Create indexes for job_listings table."""
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_job_listings_url ON job_listings(url)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_job_listings_source ON job_listings(source)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_job_listings_scraped_date ON job_listings(scraped_date)')
    
    def insert_job(self, job_data: Dict[str, Any]) -> Optional[int]:
        """Insert a new job listing."""
        try:
            query = """
                INSERT INTO job_listings (
                    title, company, location, salary, url, source, scraped_date, 
                    posted_date, description, language, job_snippet, llm_filtered,
                    llm_quality_score, llm_relevance_score, llm_reasoning
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (url) DO UPDATE SET
                    title = EXCLUDED.title,
                    company = EXCLUDED.company,
                    location = EXCLUDED.location,
                    salary = EXCLUDED.salary,
                    source = EXCLUDED.source,
                    scraped_date = EXCLUDED.scraped_date,
                    posted_date = EXCLUDED.posted_date,
                    description = EXCLUDED.description,
                    language = EXCLUDED.language,
                    job_snippet = EXCLUDED.job_snippet,
                    llm_filtered = EXCLUDED.llm_filtered,
                    llm_quality_score = EXCLUDED.llm_quality_score,
                    llm_relevance_score = EXCLUDED.llm_relevance_score,
                    llm_reasoning = EXCLUDED.llm_reasoning
                RETURNING id
            """
            
            params = (
                job_data.get('title'),
                job_data.get('company'),
                job_data.get('location'),
                job_data.get('salary'),
                job_data.get('url'),
                job_data.get('source'),
                job_data.get('scraped_date', datetime.now()),
                job_data.get('posted_date'),
                job_data.get('description'),
                job_data.get('language'),
                job_data.get('job_snippet'),
                job_data.get('llm_filtered', False),
                job_data.get('llm_quality_score'),
                job_data.get('llm_relevance_score'),
                job_data.get('llm_reasoning')
            )
            
            result = self.execute_query(query, params, fetch='one')
            return result[0] if result else None
            
        except Exception as e:
            self.log_error("insert_job", e)
            return None
    
    def get_all_jobs(self, limit: int = None) -> List[Dict[str, Any]]:
        """Get all jobs ordered by scraped_date DESC."""
        try:
            if limit:
                query = "SELECT * FROM job_listings ORDER BY scraped_date DESC LIMIT %s"
                results = self.execute_query(query, (limit,), fetch='all')
            else:
                query = "SELECT * FROM job_listings ORDER BY scraped_date DESC"
                results = self.execute_query(query, fetch='all')
            
            return [dict(row) for row in results] if results else []
            
        except Exception as e:
            self.log_error("get_all_jobs", e)
            return []
    
    def get_job_by_url(self, url: str) -> Optional[Dict[str, Any]]:
        """Get a job by URL."""
        try:
            query = "SELECT * FROM job_listings WHERE url = %s"
            result = self.execute_query(query, (url,), fetch='one')
            return dict(result) if result else None
            
        except Exception as e:
            self.log_error("get_job_by_url", e)
            return None
    
    def get_jobs_by_source(self, source: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get jobs by source."""
        try:
            query = "SELECT * FROM job_listings WHERE source = %s ORDER BY scraped_date DESC LIMIT %s"
            results = self.execute_query(query, (source, limit), fetch='all')
            return [dict(row) for row in results] if results else []
            
        except Exception as e:
            self.log_error("get_jobs_by_source", e)
            return []
    
    def update_job_llm_data(self, job_id: int, llm_data: Dict[str, Any]) -> bool:
        """Update job with LLM analysis data."""
        try:
            query = """
                UPDATE job_listings 
                SET llm_filtered = %s, llm_quality_score = %s, 
                    llm_relevance_score = %s, llm_reasoning = %s
                WHERE id = %s
            """
            
            params = (
                llm_data.get('llm_filtered', False),
                llm_data.get('llm_quality_score'),
                llm_data.get('llm_relevance_score'),
                llm_data.get('llm_reasoning'),
                job_id
            )
            
            self.execute_query(query, params)
            return True
            
        except Exception as e:
            self.log_error("update_job_llm_data", e)
            return False
    
    def delete_old_jobs(self, days_old: int) -> int:
        """Delete jobs older than specified days."""
        try:
            query = "DELETE FROM job_listings WHERE scraped_date < NOW() - INTERVAL '%s days'"
            self.execute_query(query, (days_old,))
            return 0  # Return deleted count if needed
            
        except Exception as e:
            self.log_error("delete_old_jobs", e)
            return 0
