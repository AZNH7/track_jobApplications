"""
Session state management for Job Tracker
"""

import streamlit as st

class SessionStateManager:
    @staticmethod
    def initialize_session_state():
        """Initialize all required session state variables"""
        if 'processed_jobs' not in st.session_state:
            st.session_state.processed_jobs = None
            
        if 'search_results' not in st.session_state:
            st.session_state.search_results = None
            
        if 'search_log' not in st.session_state:
            st.session_state.search_log = []
            
        if 'platform_test_results' not in st.session_state:
            st.session_state.platform_test_results = {}
            
        if 'email_log_messages' not in st.session_state:
            st.session_state['email_log_messages'] = []
    
    @staticmethod
    def clear_search_results():
        """Clear search-related session state"""
        st.session_state.search_results = None
        st.session_state.search_log = []
    
    @staticmethod
    def clear_test_results():
        """Clear platform test results"""
        st.session_state.platform_test_results = {}
    
    @staticmethod
    def clear_email_log():
        """Clear email log messages"""
        st.session_state.email_log_messages = [] 