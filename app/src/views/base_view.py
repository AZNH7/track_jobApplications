"""
Base view class for all views in the application
"""

import streamlit as st
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import time

class BaseView:
    """Base class for all views in the application"""
    
    def __init__(self):
        """Initialize base view components"""
        # Initialize cache settings
        if 'cache_enabled' not in st.session_state:
            st.session_state.cache_enabled = True
        if 'cache_ttl' not in st.session_state:
            st.session_state.cache_ttl = 300  # 5 minutes default TTL
        if 'last_cache_update' not in st.session_state:
            st.session_state.last_cache_update = {}
        if 'cached_data' not in st.session_state:
            st.session_state.cached_data = {}
        
        # Initialize logger
        self.logger = logging.getLogger(__name__)
    
    def clear_cache(self):
        """Clear all cached data"""
        st.session_state.cached_data = {}
        st.session_state.last_cache_update = {}
    
    def is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid based on TTL"""
        if not st.session_state.cache_enabled:
            return False
        
        last_update = st.session_state.last_cache_update.get(cache_key, 0)
        return (time.time() - last_update) < st.session_state.cache_ttl
    
    def get_cached_data(self, cache_key: str) -> Optional[Any]:
        """Get data from cache if valid"""
        if self.is_cache_valid(cache_key):
            return st.session_state.cached_data.get(cache_key)
        return None
    
    def set_cached_data(self, cache_key: str, data: Any) -> None:
        """Store data in cache with timestamp"""
        if st.session_state.cache_enabled:
            st.session_state.cached_data[cache_key] = data
            st.session_state.last_cache_update[cache_key] = time.time()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        stats = {
            'total_entries': len(st.session_state.cached_data),
            'valid_entries': sum(1 for k in st.session_state.cached_data if self.is_cache_valid(k)),
            'total_size': sum(len(str(v)) for v in st.session_state.cached_data.values()),
            'cache_enabled': st.session_state.cache_enabled,
            'cache_ttl': st.session_state.cache_ttl
        }
        return stats
    
    def show_cache_settings(self) -> None:
        """Show cache settings in the UI"""
        st.sidebar.markdown("### ⚡ Cache Settings")
        
        # Cache toggle
        cache_enabled = st.sidebar.toggle(
            "Enable Caching",
            value=st.session_state.cache_enabled,
            help="Toggle caching on/off"
        )
        if cache_enabled != st.session_state.cache_enabled:
            st.session_state.cache_enabled = cache_enabled
            if not cache_enabled:
                self.clear_cache()
                st.rerun()
        
        # Cache TTL slider
        new_ttl = st.sidebar.slider(
            "Cache TTL (seconds)",
            min_value=60,
            max_value=3600,
            value=st.session_state.cache_ttl,
            step=60,
            help="Time-to-live for cached data"
        )
        if new_ttl != st.session_state.cache_ttl:
            st.session_state.cache_ttl = new_ttl
        
        # Cache stats
        stats = self.get_cache_stats()
        if stats['total_entries'] > 0:
            st.sidebar.markdown(f"""
            **Cache Stats:**
            - Entries: {stats['total_entries']}
            - Valid: {stats['valid_entries']}
            - Size: {stats['total_size']/1024:.1f} KB
            """)
            
            if st.sidebar.button("Clear Cache"):
                self.clear_cache()
                st.rerun()
    
    def cache_data(self, func):
        """Decorator for caching function results"""
        def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            cache_key = f"{func.__name__}_{str(args)}_{str(kwargs)}"
            
            # Try to get from cache
            cached_result = self.get_cached_data(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            self.set_cached_data(cache_key, result)
            return result
        
        return wrapper 