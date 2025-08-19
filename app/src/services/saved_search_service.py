"""
Saved Search Parameters Service

This service manages user-saved search parameters for quick reuse.
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
    """Service for managing saved search parameters"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.storage_key = "saved_searches"
    
    def save_search(self, name: str, job_titles: List[str], location: str, 
                   platforms: List[str], max_pages: int, english_only: bool,
                   enable_grouping: bool, deep_scrape: bool) -> bool:
        """Save search parameters with a given name"""
        try:
            saved_searches = self.get_all_saved_searches()
            
            # Check if name already exists
            if any(search.name == name for search in saved_searches):
                return False
            
            # Create new saved search
            new_search = SavedSearch(
                name=name,
                job_titles=job_titles,
                location=location,
                platforms=platforms,
                max_pages=max_pages,
                english_only=english_only,
                enable_grouping=enable_grouping,
                deep_scrape=deep_scrape,
                created_at=datetime.now().isoformat()
            )
            
            saved_searches.append(new_search)
            self._save_to_session_state(saved_searches)
            
            self.logger.info(f"Saved search '{name}' with {len(job_titles)} job titles")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving search: {e}")
            return False
    
    def get_all_saved_searches(self) -> List[SavedSearch]:
        """Get all saved searches"""
        try:
            if self.storage_key not in st.session_state:
                st.session_state[self.storage_key] = []
                return []
            
            saved_data = st.session_state[self.storage_key]
            return [SavedSearch(**search_dict) for search_dict in saved_data]
            
        except Exception as e:
            self.logger.error(f"Error getting saved searches: {e}")
            return []
    
    def get_saved_search(self, name: str) -> Optional[SavedSearch]:
        """Get a specific saved search by name"""
        saved_searches = self.get_all_saved_searches()
        for search in saved_searches:
            if search.name == name:
                return search
        return None
    
    def delete_saved_search(self, name: str) -> bool:
        """Delete a saved search by name"""
        try:
            saved_searches = self.get_all_saved_searches()
            original_count = len(saved_searches)
            
            saved_searches = [search for search in saved_searches if search.name != name]
            
            if len(saved_searches) < original_count:
                self._save_to_session_state(saved_searches)
                self.logger.info(f"Deleted saved search '{name}'")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error deleting saved search: {e}")
            return False
    
    def update_usage(self, name: str) -> bool:
        """Update usage statistics for a saved search"""
        try:
            saved_searches = self.get_all_saved_searches()
            
            for search in saved_searches:
                if search.name == name:
                    search.last_used = datetime.now().isoformat()
                    search.use_count += 1
                    self._save_to_session_state(saved_searches)
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error updating usage: {e}")
            return False
    
    def get_search_names(self) -> List[str]:
        """Get list of saved search names"""
        saved_searches = self.get_all_saved_searches()
        return [search.name for search in saved_searches]
    
    def _save_to_session_state(self, saved_searches: List[SavedSearch]):
        """Save searches to session state"""
        try:
            # Convert to dictionaries for JSON serialization
            search_dicts = [asdict(search) for search in saved_searches]
            st.session_state[self.storage_key] = search_dicts
            
        except Exception as e:
            self.logger.error(f"Error saving to session state: {e}")
    
    def export_searches(self) -> str:
        """Export all saved searches as JSON string"""
        try:
            saved_searches = self.get_all_saved_searches()
            search_dicts = [asdict(search) for search in saved_searches]
            return json.dumps(search_dicts, indent=2)
            
        except Exception as e:
            self.logger.error(f"Error exporting searches: {e}")
            return "[]"
    
    def import_searches(self, json_data: str) -> bool:
        """Import saved searches from JSON string"""
        try:
            search_dicts = json.loads(json_data)
            saved_searches = [SavedSearch(**search_dict) for search_dict in search_dicts]
            self._save_to_session_state(saved_searches)
            return True
            
        except Exception as e:
            self.logger.error(f"Error importing searches: {e}")
            return False
