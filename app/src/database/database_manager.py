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
                        return cursor.fetchone()
                    elif fetch == 'all':
                        return cursor.fetchall()
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
