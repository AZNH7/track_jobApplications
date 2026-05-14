"""
Session state management for Job Tracker
"""

import streamlit as st

try:
    from constants import SESSION_MAX_LOG_ENTRIES as _MAX_LOG_ENTRIES, SESSION_MAX_TEST_RESULTS as _MAX_TEST_RESULTS
except ImportError:
    _MAX_LOG_ENTRIES = 100
    _MAX_TEST_RESULTS = 50


class SessionStateManager:
    @staticmethod
    def initialize_session_state() -> None:
        """Initialize all required session state variables."""
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
    def trim_session_state() -> None:
        """Cap unbounded session-state lists to prevent memory growth over a long session."""
        log = st.session_state.get('search_log')
        if isinstance(log, list) and len(log) > _MAX_LOG_ENTRIES:
            st.session_state.search_log = log[-_MAX_LOG_ENTRIES:]

        email_log = st.session_state.get('email_log_messages')
        if isinstance(email_log, list) and len(email_log) > _MAX_LOG_ENTRIES:
            st.session_state.email_log_messages = email_log[-_MAX_LOG_ENTRIES:]

        test_results = st.session_state.get('platform_test_results')
        if isinstance(test_results, dict) and len(test_results) > _MAX_TEST_RESULTS:
            # Evict oldest keys (insertion order is preserved in Python 3.7+)
            excess = len(test_results) - _MAX_TEST_RESULTS
            for key in list(test_results.keys())[:excess]:
                del st.session_state.platform_test_results[key]

    @staticmethod
    def clear_search_results() -> None:
        """Clear search-related session state."""
        st.session_state.search_results = None
        st.session_state.search_log = []

    @staticmethod
    def clear_test_results() -> None:
        """Clear platform test results."""
        st.session_state.platform_test_results = {}

    @staticmethod
    def clear_email_log() -> None:
        """Clear email log messages."""
        st.session_state.email_log_messages = [] 