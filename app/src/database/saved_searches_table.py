"""
Saved Searches Table

Handles all operations related to the saved_searches table.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import json
from .base_table import BaseTable


class SavedSearchesTable(BaseTable):
    """Handles saved_searches table operations."""
    
    def create_table(self, cursor) -> None:
        """Create the saved_searches table."""
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS saved_searches (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) UNIQUE NOT NULL,
                job_titles JSONB NOT NULL,
                location VARCHAR(255) NOT NULL,
                platforms JSONB NOT NULL,
                max_pages INTEGER DEFAULT 5,
                english_only BOOLEAN DEFAULT FALSE,
                enable_grouping BOOLEAN DEFAULT TRUE,
                deep_scrape BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                last_used TIMESTAMP WITH TIME ZONE,
                use_count INTEGER DEFAULT 0
            )
        ''')
    
    def create_indexes(self, cursor) -> None:
        """Create indexes for saved_searches table."""
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_saved_searches_name ON saved_searches(name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_saved_searches_last_used ON saved_searches(last_used)')
    
    def save_search_parameters(self, name: str, job_titles: list, location: str, 
                              platforms: list, max_pages: int, english_only: bool,
                              enable_grouping: bool, deep_scrape: bool) -> bool:
        """Save search parameters to database."""
        try:
            query = """
                INSERT INTO saved_searches 
                (name, job_titles, location, platforms, max_pages, english_only, enable_grouping, deep_scrape)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (name) DO UPDATE SET
                    job_titles = EXCLUDED.job_titles,
                    location = EXCLUDED.location,
                    platforms = EXCLUDED.platforms,
                    max_pages = EXCLUDED.max_pages,
                    english_only = EXCLUDED.english_only,
                    enable_grouping = EXCLUDED.enable_grouping,
                    deep_scrape = EXCLUDED.deep_scrape,
                    last_used = CURRENT_TIMESTAMP
            """
            
            params = (
                name,
                json.dumps(job_titles),
                location,
                json.dumps(platforms),
                max_pages,
                english_only,
                enable_grouping,
                deep_scrape
            )
            
            self.execute_query(query, params)
            return True
            
        except Exception as e:
            self.log_error("save_search_parameters", e)
            return False
    
    def get_all_saved_searches(self) -> List[Dict[str, Any]]:
        """Get all saved searches from database."""
        try:
            query = """
                SELECT id, name, job_titles, location, platforms, max_pages, 
                       english_only, enable_grouping, deep_scrape, created_at, 
                       last_used, use_count
                FROM saved_searches 
                ORDER BY last_used DESC NULLS LAST, created_at DESC
            """
            
            results = self.execute_query(query, fetch='all')
            if not results:
                return []
            
            saved_searches = []
            for row in results:
                try:
                    # JSONB columns return Python objects directly, not JSON strings
                    job_titles = row[2] if row[2] else []
                    platforms = row[4] if row[4] else []
                    
                    saved_searches.append({
                        'id': row[0],
                        'name': row[1],
                        'job_titles': job_titles,
                        'location': row[3],
                        'platforms': platforms,
                        'max_pages': row[5],
                        'english_only': row[6],
                        'enable_grouping': row[7],
                        'deep_scrape': row[8],
                        'created_at': row[9].isoformat() if row[9] else None,
                        'last_used': row[10].isoformat() if row[10] else None,
                        'use_count': row[11] or 0
                    })
                except Exception as e:
                    self.logger.error(f"Error parsing saved search row: {e}")
                    continue
            
            return saved_searches
            
        except Exception as e:
            self.log_error("get_all_saved_searches", e)
            return []
    
    def get_saved_search(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a specific saved search by name."""
        try:
            query = """
                SELECT id, name, job_titles, location, platforms, max_pages, 
                       english_only, enable_grouping, deep_scrape, created_at, 
                       last_used, use_count
                FROM saved_searches 
                WHERE name = %s
            """
            
            result = self.execute_query(query, (name,), fetch='one')
            if not result:
                return None
            
            try:
                # JSONB columns return Python objects directly, not JSON strings
                job_titles = result[2] if result[2] else []
                platforms = result[4] if result[4] else []
                
                return {
                    'id': result[0],
                    'name': result[1],
                    'job_titles': job_titles,
                    'location': result[3],
                    'platforms': platforms,
                    'max_pages': result[5],
                    'english_only': result[6],
                    'enable_grouping': result[7],
                    'deep_scrape': result[8],
                    'created_at': result[9].isoformat() if result[9] else None,
                    'last_used': result[10].isoformat() if result[10] else None,
                    'use_count': result[11] or 0
                }
            except Exception as e:
                self.logger.error(f"Error parsing saved search: {e}")
                return None
            
        except Exception as e:
            self.log_error("get_saved_search", e)
            return None
    
    def delete_saved_search(self, name: str) -> bool:
        """Delete a saved search by name."""
        try:
            query = "DELETE FROM saved_searches WHERE name = %s"
            self.execute_query(query, (name,))
            return True
            
        except Exception as e:
            self.log_error("delete_saved_search", e)
            return False
    
    def update_saved_search_usage(self, name: str) -> bool:
        """Update usage statistics for a saved search."""
        try:
            query = """
                UPDATE saved_searches 
                SET last_used = CURRENT_TIMESTAMP, use_count = use_count + 1
                WHERE name = %s
            """
            self.execute_query(query, (name,))
            return True
            
        except Exception as e:
            self.log_error("update_saved_search_usage", e)
            return False
    
    def check_saved_search_exists(self, name: str) -> bool:
        """Check if a saved search with the given name already exists."""
        try:
            query = "SELECT COUNT(*) FROM saved_searches WHERE name = %s"
            result = self.execute_query(query, (name,), fetch='one')
            return result[0] > 0 if result else False
            
        except Exception as e:
            self.log_error("check_saved_search_exists", e)
            return False
