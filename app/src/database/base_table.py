"""
Base table class for database operations.

Provides common functionality for all table classes.
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Tuple
from contextlib import contextmanager
import psycopg2
import psycopg2.extras


class BaseTable(ABC):
    """Base class for all database table operations."""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def create_table(self, cursor) -> None:
        """Create the table in the database."""
        pass
    
    @abstractmethod
    def create_indexes(self, cursor) -> None:
        """Create indexes for the table."""
        pass
    
    def execute_query(self, query: str, params: Optional[Tuple] = None, fetch: str = 'none') -> Any:
        """Execute a database query."""
        return self.db_manager.execute_query(query, params, fetch)
    
    @contextmanager
    def get_connection(self):
        """Get a database connection."""
        with self.db_manager.get_connection() as conn:
            yield conn
    
    def log_error(self, operation: str, error: Exception) -> None:
        """Log database errors consistently."""
        self.logger.error(f"Error in {operation}: {error}")
    
    def log_info(self, message: str) -> None:
        """Log database operations."""
        self.logger.info(message)
