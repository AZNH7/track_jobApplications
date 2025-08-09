"""
Persistent Search Results Component
Manages and displays search results that persist across all sections of the application.
"""

import streamlit as st
import pandas as pd
from typing import Dict, Optional
from datetime import datetime

class PersistentSearchResults:
    """Component for managing persistent search results across application sections."""
    
    @staticmethod
    def store_search_results(results_df: pd.DataFrame, search_metadata: Dict = None):
        """Store search results in session state with metadata."""
        if results_df is not None and not results_df.empty:
            st.session_state.persistent_search_results = results_df
            st.session_state.search_metadata = search_metadata or {}
            st.session_state.search_timestamp = datetime.now()
            
    @staticmethod
    def get_search_results() -> Optional[pd.DataFrame]:
        """Get stored search results from session state."""
        return st.session_state.get('persistent_search_results', None)
    
    @staticmethod
    def get_search_metadata() -> Dict:
        """Get search metadata from session state."""
        return st.session_state.get('search_metadata', {})
    
    @staticmethod
    def clear_search_results():
        """Clear stored search results."""
        if 'persistent_search_results' in st.session_state:
            del st.session_state.persistent_search_results
        if 'search_metadata' in st.session_state:
            del st.session_state.search_metadata
        if 'search_timestamp' in st.session_state:
            del st.session_state.search_timestamp
    
    @staticmethod
    def has_search_results() -> bool:
        """Check if there are stored search results."""
        results = PersistentSearchResults.get_search_results()
        return results is not None and not results.empty
    
    @staticmethod
    def show_sidebar_summary():
        """Show a compact summary of search results in the sidebar."""
        if not PersistentSearchResults.has_search_results():
            return
            
        results_df = PersistentSearchResults.get_search_results()
        metadata = PersistentSearchResults.get_search_metadata()
        search_time = st.session_state.get('search_timestamp', datetime.now())
        
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 🔍 Latest Search Results")
        
        # Search summary
        total_jobs = len(results_df)
        filtered_count = len(results_df[results_df.get('llm_filtered', False) == True]) if 'llm_filtered' in results_df.columns else 0
        approved_count = total_jobs - filtered_count
        
        # Metrics in sidebar
        col1, col2 = st.sidebar.columns(2)
        with col1:
            st.metric("Total", total_jobs)
        with col2:
            st.metric("✅ Approved", approved_count)
        
        if filtered_count > 0:
            st.sidebar.metric("🚫 Filtered", filtered_count)
        
        # Search metadata
        if metadata:
            keywords = metadata.get('keywords', 'N/A')
            location = metadata.get('location', 'N/A')
            platforms = metadata.get('platforms', [])
            
            st.sidebar.markdown(f"**Keywords:** {keywords}")
            if location and location != 'N/A':
                st.sidebar.markdown(f"**Location:** {location}")
            if platforms:
                st.sidebar.markdown(f"**Platforms:** {', '.join(platforms)}")
        
        # Timestamp
        time_str = search_time.strftime("%H:%M:%S")
        st.sidebar.markdown(f"**Time:** {time_str}")
        
        # Clear button
        if st.sidebar.button("🗑️ Clear Results"):
            PersistentSearchResults.clear_search_results()
            st.rerun()
    
    @staticmethod
    def show_expandable_results():
        """Show expandable search results that can be displayed on any page."""
        if not PersistentSearchResults.has_search_results():
            return
            
        results_df = PersistentSearchResults.get_search_results()
        metadata = PersistentSearchResults.get_search_metadata()
        search_time = st.session_state.get('search_timestamp', datetime.now())
        
        # Create expandable section
        with st.expander("🔍 Latest Search Results", expanded=False):
            # Header with metadata
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                keywords = metadata.get('keywords', 'N/A')
                location = metadata.get('location', 'N/A')
                st.markdown(f"**Search:** {keywords}")
                if location and location != 'N/A':
                    st.markdown(f"**Location:** {location}")
            
            with col2:
                platforms = metadata.get('platforms', [])
                if platforms:
                    st.markdown(f"**Platforms:** {', '.join(platforms)}")
                time_str = search_time.strftime("%Y-%m-%d %H:%M:%S")
                st.markdown(f"**Time:** {time_str}")
            
            with col3:
                if st.button("🗑️ Clear", key="clear_expandable_results"):
                    PersistentSearchResults.clear_search_results()
                    st.rerun()
            
            st.markdown("---")
            
            # Display results using the same logic as job search view
            PersistentSearchResults._display_results_compact(results_df)
    
    @staticmethod
    def _display_results_compact(df: pd.DataFrame):
        """Display search results in a compact format."""
        if df.empty:
            st.warning("No jobs found.")
            return
            
        # Separate filtered and approved jobs
        filtered_jobs = df[df.get('llm_filtered', False) == True] if 'llm_filtered' in df.columns else pd.DataFrame()
        approved_jobs = df[df.get('llm_filtered', False) == False] if 'llm_filtered' in df.columns else df
        
        # Show statistics
        total_jobs = len(df)
        approved_count = len(approved_jobs)
        filtered_count = len(filtered_jobs)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Jobs", total_jobs)
        with col2:
            st.metric("✅ Approved", approved_count)
        with col3:
            st.metric("🚫 Filtered", filtered_count)
        
        # Show approved jobs first (compact view)
        if not approved_jobs.empty:
            st.markdown("#### ✅ Approved Jobs")
            PersistentSearchResults._display_job_list_compact(approved_jobs.head(5))  # Show top 5
            
            if len(approved_jobs) > 5:
                st.markdown(f"*... and {len(approved_jobs) - 5} more approved jobs*")
        
        # Show filtered jobs in expandable section
        if not filtered_jobs.empty:
            with st.expander(f"🚫 Filtered Jobs ({filtered_count})"):
                st.markdown("These jobs were filtered by AI assessment:")
                PersistentSearchResults._display_job_list_compact(filtered_jobs, show_reasoning=True)
    
    @staticmethod
    def _display_job_list_compact(df: pd.DataFrame, show_reasoning: bool = False):
        """Display a compact list of jobs."""
        for idx, row in df.head(10).iterrows():  # Limit to 10 for performance
            with st.container():
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    # Job title and company
                    title = row.get('title', 'Unknown Title')
                    company = row.get('company', 'Unknown Company')
                    st.markdown(f"**{title}** at {company}")
                    
                    # Location and language
                    location = row.get('location', 'Unknown')
                    language = str(row.get('language', 'unknown') or 'unknown').lower() if row.get('language') and str(row.get('language')) != 'nan' else 'unknown'
                    platform = row.get('platform', row.get('source', 'Unknown'))
                    
                    # Language flag emoji
                    lang_flag = {'en': '🇬🇧', 'de': '🇩🇪', 'fr': '🇫🇷', 'es': '🇪🇸'}.get(language, '🌐')
                    
                    st.markdown(f"📍 {location} | {lang_flag} {language.upper()} | 🔗 {platform}")
                    
                    # Job snippet if available
                    job_snippet = row.get('job_snippet', '')
                    if job_snippet:
                        st.markdown(f"💼 *{job_snippet}*")
                
                with col2:
                    # AI Assessment scores and actions
                    quality_score = row.get('llm_quality_score', 0)
                    if quality_score > 0:
                        st.markdown(f"**Quality:** {quality_score}/10")
                    
                    if row.get('url'):
                        st.link_button("🔗 View", row['url'], use_container_width=True)
                
                # Show AI reasoning if requested and available
                if show_reasoning and row.get('llm_reasoning'):
                    with st.expander("🤖 AI Reasoning", expanded=False):
                        st.write(row['llm_reasoning'])
                
                st.divider() 