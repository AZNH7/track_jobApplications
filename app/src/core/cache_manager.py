"""
Cache management system for Job Tracker
"""

import time
from datetime import datetime, timedelta
import json
import streamlit as st

class CacheManager:
    def __init__(self, cache_duration: int = 300):  # Default 5 minutes
        self.cache_duration = cache_duration
    
    def is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache is still valid"""
        if cache_key not in st.session_state:
            return False
            
        cache_data = st.session_state[cache_key]
        if not isinstance(cache_data, dict) or 'timestamp' not in cache_data:
            return False
            
        cache_time = cache_data['timestamp']
        current_time = time.time()
        
        return (current_time - cache_time) < self.cache_duration
    
    def get_cached_data(self, cache_key: str):
        """Get cached data if valid"""
        if not self.is_cache_valid(cache_key):
            return None
            
        return st.session_state[cache_key].get('data')
    
    def set_cached_data(self, cache_key: str, data):
        """Set data in cache with timestamp"""
        st.session_state[cache_key] = {
            'data': data,
            'timestamp': time.time()
        }
    
    def clear_cache(self, cache_key: str = None):
        """Clear specific or all cached data"""
        if cache_key:
            if cache_key in st.session_state:
                del st.session_state[cache_key]
        else:
            # Clear all cache keys (those that have timestamp)
            keys_to_clear = [
                key for key in st.session_state.keys()
                if isinstance(st.session_state[key], dict) and 'timestamp' in st.session_state[key]
            ]
            for key in keys_to_clear:
                del st.session_state[key]
    
    def get_cache_status(self, cache_key: str) -> dict:
        """Get cache status information"""
        if not self.is_cache_valid(cache_key):
            return {'valid': False, 'age': None, 'expires_in': None}
            
        cache_data = st.session_state[cache_key]
        current_time = time.time()
        cache_age = current_time - cache_data['timestamp']
        expires_in = max(0, self.cache_duration - cache_age)
        
        return {
            'valid': True,
            'age': timedelta(seconds=int(cache_age)),
            'expires_in': timedelta(seconds=int(expires_in))
        }

    def get_cache_stats(self):
        """Get cache statistics"""
        stats = {
            'total_entries': len(st.session_state),
            'valid_entries': sum(1 for k in st.session_state if self.is_cache_valid(k)),
            'total_size': sum(len(str(v['data'])) for v in st.session_state.values()),
            'oldest_entry': min((v['timestamp'] for v in st.session_state.values()), default=None),
            'newest_entry': max((v['timestamp'] for v in st.session_state.values()), default=None)
        }
        return stats 