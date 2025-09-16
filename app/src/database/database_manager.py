"""
Database Manager

Main database manager that orchestrates all table operations.
"""

import os
import logging
import psycopg2
import psycopg2.extras
import psycopg2.pool
from contextlib import contextmanager
from typing import Optional, Tuple, Any, Dict, List
import pandas as pd

from .job_listings_table import JobListingsTable
from .job_applications_table import JobApplicationsTable
from .job_details_table import JobDetailsTable
from .ignored_jobs_table import IgnoredJobsTable
from .filtered_jobs_table import FilteredJobsTable
from .job_offers_table import JobOffersTable
from .saved_searches_table import SavedSearchesTable


class DatabaseManager:
    """Main database manager for the job tracker application."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.connection_pool = None
        
        # Initialize table managers
        self.job_listings = JobListingsTable(self)
        self.job_applications = JobApplicationsTable(self)
        self.job_details = JobDetailsTable(self)
        self.ignored_jobs = IgnoredJobsTable(self)
        self.filtered_jobs = FilteredJobsTable(self)
        self.job_offers = JobOffersTable(self)
        self.saved_searches = SavedSearchesTable(self)
        
        # Initialize database
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize database connection and create tables."""
        try:
            self._create_connection_pool()
            self._create_tables()
            self.logger.info("✅ Database initialized successfully")
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize database: {e}")
            raise
    
    def _create_connection_pool(self):
        """Create database connection pool."""
        try:
            # Get database configuration from environment
            db_config = {
                'host': os.getenv('DB_HOST', 'localhost'),
                'port': os.getenv('DB_PORT', '5432'),
                'database': os.getenv('DB_NAME', 'job_tracker'),
                'user': os.getenv('DB_USER', 'postgres'),
                'password': os.getenv('DB_PASSWORD', ''),
                'minconn': 1,
                'maxconn': 10
            }
            
            self.connection_pool = psycopg2.pool.SimpleConnectionPool(**db_config)
            self.logger.info("✅ Database connection pool created")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to create connection pool: {e}")
            raise
    
    def _create_tables(self):
        """Create all database tables."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Create tables
                    self.job_listings.create_table(cursor)
                    self.job_applications.create_table(cursor)
                    self.job_details.create_table(cursor)
                    self.ignored_jobs.create_table(cursor)
                    self.filtered_jobs.create_table(cursor)
                    self.job_offers.create_table(cursor)
                    self.saved_searches.create_table(cursor)
                    
                    conn.commit()
            
            self.logger.info("✅ All tables created successfully")
            
            # Create indexes separately to handle any schema issues
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    try:
                        self.job_listings.create_indexes(cursor)
                        self.job_applications.create_indexes(cursor)
                        self.job_details.create_indexes(cursor)
                        self.ignored_jobs.create_indexes(cursor)
                        self.filtered_jobs.create_indexes(cursor)
                        self.job_offers.create_indexes(cursor)
                        self.saved_searches.create_indexes(cursor)
                        conn.commit()
                        self.logger.info("✅ All indexes created successfully")
                    except Exception as e:
                        self.logger.warning(f"⚠️ Some indexes could not be created: {e}")
                        conn.rollback()
            
        except Exception as e:
            self.logger.error(f"❌ Failed to create tables: {e}")
            raise
    
    @contextmanager
    def get_connection(self, timeout: float = 30.0):
        """Get a connection from the pool."""
        if not self.connection_pool:
            self._create_connection_pool()
        
        conn = self.connection_pool.getconn()
        try:
            yield conn
        finally:
            self.connection_pool.putconn(conn)
    
    def execute_query(self, query: str, params: Optional[Tuple] = None, fetch: str = 'none') -> Any:
        """Execute a database query."""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                    cursor.execute(query, params)
                    
                    if fetch == 'one':
                        result = cursor.fetchone()
                        conn.commit()  # Always commit after successful execution
                        return result
                    elif fetch == 'all':
                        result = cursor.fetchall()
                        conn.commit()  # Always commit after successful execution
                        return result
                    else:
                        conn.commit()
                        return None
                        
        except Exception as e:
            self.logger.error(f"Error executing query: {e}")
            raise
    
    def execute_many(self, query: str, params_list: List[Tuple]) -> None:
        """Execute multiple queries with different parameters."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.executemany(query, params_list)
                    conn.commit()
                    
        except Exception as e:
            self.logger.error(f"Error executing many queries: {e}")
            raise
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get overall database statistics."""
        try:
            stats = {
                'job_listings': self._get_table_count('job_listings'),
                'job_applications': self._get_table_count('job_applications'),
                'job_details': self._get_table_count('job_details'),
                'ignored_jobs': self._get_table_count('ignored_jobs'),
                'filtered_jobs': self._get_table_count('filtered_jobs'),
                'job_offers': self._get_table_count('job_offers'),
                'saved_searches': self._get_table_count('saved_searches'),
            }
            
            # Add cache stats
            cache_stats = self.job_details.get_cache_stats()
            stats['cache_stats'] = cache_stats
            
            # Add offer stats
            offer_stats = self.job_offers.get_offer_stats()
            stats['offer_stats'] = offer_stats
            

            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting database stats: {e}")
            return {}
    
    def _get_table_count(self, table_name: str) -> int:
        """Get row count for a table."""
        try:
            query = f"SELECT COUNT(*) FROM {table_name}"
            result = self.execute_query(query, fetch='one')
            return result[0] if result else 0
        except Exception as e:
            self.logger.error(f"Error getting count for {table_name}: {e}")
            return 0
    
    def get_cached_job_details(self, job_url: str) -> Optional[Dict[str, Any]]:
        """Get cached job details for a specific URL."""
        try:
            return self.job_details.get_cached_job_details(job_url)
        except Exception as e:
            self.logger.error(f"Error getting cached job details: {e}")
            return None
    
    def get_cached_job_details_stats(self) -> Dict[str, Any]:
        """Get statistics about cached job details."""
        try:
            return self.job_details.get_cache_stats()
        except Exception as e:
            self.logger.error(f"Error getting cached job details stats: {e}")
            return {}
    
    def batch_insert_jobs(self, jobs_data: List[Dict[str, Any]]) -> int:
        """Insert multiple jobs into the database in batch."""
        if not jobs_data:
            self.logger.warning("No jobs data provided for batch insert")
            return 0
        
        saved_count = 0
        failed_count = 0
        try:
            self.logger.info(f"Starting batch insert of {len(jobs_data)} jobs")
            
            for i, job in enumerate(jobs_data):
                try:
                    # Log job details for debugging
                    job_title = job.get('title', 'Unknown')
                    job_url = job.get('url', 'No URL')
                    self.logger.debug(f"Processing job {i+1}/{len(jobs_data)}: {job_title}")
                    
                    job_id = self.job_listings.insert_job(job)
                    if job_id:
                        saved_count += 1
                        self.logger.debug(f"✅ Saved job: {job_title} (ID: {job_id})")
                    else:
                        failed_count += 1
                        self.logger.warning(f"❌ Failed to save job: {job_title} (URL: {job_url})")
                        
                except Exception as job_error:
                    failed_count += 1
                    self.logger.error(f"❌ Error saving job {job.get('title', 'Unknown')}: {job_error}")
            
            self.logger.info(f"Batch insert completed: {saved_count} saved, {failed_count} failed out of {len(jobs_data)} total")
            return saved_count
            
        except Exception as e:
            self.logger.error(f"Critical error in batch insert: {e}")
            return saved_count
    
    def save_job_listing(self, job_data: Dict[str, Any]) -> bool:
        """Save a single job listing to the database."""
        try:
            job_id = self.job_listings.insert_job(job_data)
            if job_id:
                self.logger.info(f"Job saved successfully: {job_data.get('title', 'Unknown')} (ID: {job_id})")
                return True
            else:
                self.logger.warning(f"Failed to save job: {job_data.get('title', 'Unknown')}")
                return False
        except Exception as e:
            self.logger.error(f"Error saving job listing: {e}")
            return False
    
    def cleanup_filtered_jobs_from_ignored(self) -> int:
        """Clean up jobs that are in filtered_jobs but also in ignored_jobs."""
        try:
            # Get jobs that are in both filtered and ignored tables using job_listing_id
            query = """
                SELECT f.id, f.job_listing_id, jl.title, jl.company
                FROM filtered_jobs f
                INNER JOIN ignored_jobs i ON f.job_listing_id = i.job_listing_id
                LEFT JOIN job_listings jl ON f.job_listing_id = jl.id
            """
            
            duplicate_jobs = self.execute_query(query, fetch='all')
            
            if not duplicate_jobs:
                return 0
            
            # Remove duplicates from filtered_jobs (keep in ignored_jobs)
            removed_count = 0
            for job in duplicate_jobs:
                delete_query = "DELETE FROM filtered_jobs WHERE id = %s"
                self.execute_query(delete_query, (job['id'],))
                removed_count += 1
                self.logger.debug(f"Removed duplicate from filtered_jobs: {job['title']} at {job['company']}")
            
            self.logger.info(f"Cleaned up {removed_count} duplicate jobs from filtered_jobs")
            return removed_count
            
        except Exception as e:
            self.logger.error(f"Error cleaning up filtered jobs: {e}")
            return 0
    
    def close(self):
        """Close database connections."""
        if self.connection_pool:
            self.connection_pool.closeall()
            self.logger.info("Database connections closed")


# Global database manager instance
_db_manager = None


def get_db_manager() -> DatabaseManager:
    """Get the global database manager instance."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


def close_db_manager():
    """Close the global database manager."""
    global _db_manager
    if _db_manager:
        _db_manager.close()
        _db_manager = None
