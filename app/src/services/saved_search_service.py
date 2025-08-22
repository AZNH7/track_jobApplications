"""
Saved Search Parameters Service

This service manages user-saved search parameters for quick reuse.
Persists data to database for container restart/rebuild resilience.
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import streamlit as st

@dataclass
class SavedSearch:
    """Data class for saved search parameters"""
    name: str
    job_titles: List[str]
    location: str
    platforms: List[str]
    max_pages: int
    english_only: bool
    enable_grouping: bool
    deep_scrape: bool
    created_at: str
    last_used: Optional[str] = None
    use_count: int = 0

class SavedSearchService:
    """Service for managing saved search parameters with database persistence"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # Import database manager
        try:
            from src.database.database_manager import get_db_manager
            self.db_manager = get_db_manager()
        except Exception as e:
            self.logger.error(f"Failed to initialize database manager: {e}")
            self.db_manager = None
    
    def save_search(self, name: str, job_titles: List[str], location: str, 
                   platforms: List[str], max_pages: int, english_only: bool,
                   enable_grouping: bool, deep_scrape: bool) -> bool:
        """Save search parameters with a given name to database"""
        try:
            if not self.db_manager:
                self.logger.error("Database manager not available")
                return False
            
            # Check if name already exists (for user feedback)
            exists = self.db_manager.saved_searches.check_saved_search_exists(name)
            
            # Save to database (will update if exists due to ON CONFLICT)
            success = self.db_manager.saved_searches.save_search_parameters(
                name, job_titles, location, platforms, max_pages, 
                english_only, enable_grouping, deep_scrape
            )
            
            if success:
                if exists:
                    self.logger.info(f"Updated existing search '{name}' with {len(job_titles)} job titles in database")
                else:
                    self.logger.info(f"Saved new search '{name}' with {len(job_titles)} job titles to database")
                return True
            else:
                self.logger.error(f"Failed to save search '{name}' to database")
                return False
            
        except Exception as e:
            self.logger.error(f"Error saving search: {e}")
            return False
    
    def get_all_saved_searches(self) -> List[SavedSearch]:
        """Get all saved searches from database"""
        try:
            if not self.db_manager:
                self.logger.error("Database manager not available")
                return []
            
            # Get from database
            saved_data = self.db_manager.saved_searches.get_all_saved_searches()
            
            # Convert to SavedSearch objects
            saved_searches = []
            for search_dict in saved_data:
                saved_searches.append(SavedSearch(
                    name=search_dict['name'],
                    job_titles=search_dict['job_titles'],
                    location=search_dict['location'],
                    platforms=search_dict['platforms'],
                    max_pages=search_dict['max_pages'],
                    english_only=search_dict['english_only'],
                    enable_grouping=search_dict['enable_grouping'],
                    deep_scrape=search_dict['deep_scrape'],
                    created_at=search_dict['created_at'],
                    last_used=search_dict['last_used'],
                    use_count=search_dict['use_count']
                ))
            
            return saved_searches
            
        except Exception as e:
            self.logger.error(f"Error getting saved searches: {e}")
            return []
    
    def get_saved_search(self, name: str) -> Optional[SavedSearch]:
        """Get a specific saved search by name from database"""
        try:
            search_dict = self.db_manager.saved_searches.get_saved_search(name)
            if not search_dict:
                return None
            
            return SavedSearch(
                name=search_dict['name'],
                job_titles=search_dict['job_titles'],
                location=search_dict['location'],
                platforms=search_dict['platforms'],
                max_pages=search_dict['max_pages'],
                english_only=search_dict['english_only'],
                enable_grouping=search_dict['enable_grouping'],
                deep_scrape=search_dict['deep_scrape'],
                created_at=search_dict['created_at'],
                last_used=search_dict['last_used'],
                use_count=search_dict['use_count']
            )
            
        except Exception as e:
            self.logger.error(f"Error getting saved search: {e}")
            return None
    
    def delete_saved_search(self, name: str) -> bool:
        """Delete a saved search by name from database"""
        try:
            success = self.db_manager.saved_searches.delete_saved_search(name)
            if success:
                self.logger.info(f"Deleted saved search '{name}' from database")
            return success
            
        except Exception as e:
            self.logger.error(f"Error deleting saved search: {e}")
            return False
    
    def update_usage(self, name: str) -> bool:
        """Update usage statistics for a saved search in database"""
        try:
            success = self.db_manager.saved_searches.update_saved_search_usage(name)
            if success:
                self.logger.info(f"Updated usage for saved search '{name}' in database")
            return success
            
        except Exception as e:
            self.logger.error(f"Error updating usage: {e}")
            return False
    
    def get_search_names(self) -> List[str]:
        """Get list of saved search names"""
        saved_searches = self.get_all_saved_searches()
        return [search.name for search in saved_searches]
    

    
    def export_searches(self) -> str:
        """Export all saved searches as JSON string from database"""
        try:
            saved_searches = self.get_all_saved_searches()
            search_dicts = [asdict(search) for search in saved_searches]
            return json.dumps(search_dicts, indent=2)
            
        except Exception as e:
            self.logger.error(f"Error exporting searches: {e}")
            return "[]"
    
    def import_searches(self, json_data: str) -> bool:
        """Import saved searches from JSON string to database"""
        try:
            if not self.db_manager:
                self.logger.error("Database manager not available")
                return False
            
            search_dicts = json.loads(json_data)
            
            # Import each search to database
            for search_dict in search_dicts:
                success = self.db_manager.saved_searches.save_search_parameters(
                    search_dict['name'],
                    search_dict['job_titles'],
                    search_dict['location'],
                    search_dict['platforms'],
                    search_dict['max_pages'],
                    search_dict['english_only'],
                    search_dict['enable_grouping'],
                    search_dict['deep_scrape']
                )
                if not success:
                    self.logger.error(f"Failed to import search '{search_dict.get('name', 'Unknown')}'")
                    return False
            
            self.logger.info(f"Successfully imported {len(search_dicts)} saved searches to database")
            return True
            
        except Exception as e:
            self.logger.error(f"Error importing searches: {e}")
            return False
    
    def migrate_session_state_to_database(self) -> bool:
        """Migrate any existing saved searches from session state to database"""
        try:
            if not self.db_manager:
                self.logger.error("Database manager not available")
                return False
            
            # Check if there are any saved searches in session state
            if "saved_searches" in st.session_state:
                saved_data = st.session_state["saved_searches"]
                if saved_data:
                    self.logger.info(f"Migrating {len(saved_data)} saved searches from session state to database")
                    
                    # Import each search to database
                    for search_dict in saved_data:
                        success = self.db_manager.saved_searches.save_search_parameters(
                            search_dict['name'],
                            search_dict['job_titles'],
                            search_dict['location'],
                            search_dict['platforms'],
                            search_dict['max_pages'],
                            search_dict['english_only'],
                            search_dict['enable_grouping'],
                            search_dict['deep_scrape']
                        )
                        if not success:
                            self.logger.error(f"Failed to migrate search '{search_dict.get('name', 'Unknown')}'")
                            return False
                    
                    # Clear session state after successful migration
                    del st.session_state["saved_searches"]
                    self.logger.info("Successfully migrated saved searches to database and cleared session state")
                    return True
            
            return True  # No migration needed
            
        except Exception as e:
            self.logger.error(f"Error migrating session state to database: {e}")
            return False
