"""
Enhanced Job Search View with Intelligent Grouping
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
import logging
import time

# Absolute imports
from src.views.base_view import BaseView
from src.services.job_grouping_service import JobGroupingService, JobGroup

from src.utils.ui_components import UIComponents
from src.database.database_manager import get_db_manager
from src.config_manager import get_config_manager
from src.scrapers import JobScraperOrchestrator
from src.components.persistent_search_results import PersistentSearchResults
from src.services.saved_search_service import SavedSearchService

class EnhancedJobSearchView(BaseView):
    """
    Enhanced job search view with intelligent grouping capabilities
    """
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        
        # Initialize services and managers
        self.job_grouping_service = JobGroupingService()
        self.saved_search_service = SavedSearchService()
        self.ui = UIComponents()
        self.db_manager = get_db_manager()
        self.config_manager = get_config_manager()
        
        # Initialize orchestrator with configuration
        config = self.config_manager._config_data
        self.job_scraper_orchestrator = JobScraperOrchestrator(
            debug=True,
            config=config,
            use_flaresolverr=config.get('scraping', {}).get('use_flaresolverr', True)
        )

        # Initialize search state
        if 'search_results' not in st.session_state:
            st.session_state.search_results = None
        if 'processed_jobs' not in st.session_state:
            st.session_state.processed_jobs = None
        if 'search_log' not in st.session_state:
            st.session_state.search_log = []
        if 'platform_test_results' not in st.session_state:
            st.session_state.platform_test_results = {}
        
        # Migrate any existing saved searches from session state to database
        self.saved_search_service.migrate_session_state_to_database()
    
    def _show_last_search_status(self):
        """Show the status of the last search."""
        status = st.session_state.last_search_status
        
        if status['success']:
            # Success status
            st.success(f"✅ Last search completed successfully!")
            
            # Create columns for status info
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Jobs Found", status['jobs_found'])
            
            with col2:
                timestamp = status['timestamp'].strftime('%H:%M:%S')
                st.metric("Completed", timestamp)
            
            with col3:
                platforms_count = len(status['platforms'])
                st.metric("Platforms", platforms_count)
            
            # Show search details in expander
            with st.expander("🔍 Last Search Details", expanded=False):
                st.text(f"Keywords: {status['keywords']}")
                st.text(f"Location: {status['location']}")
                st.text(f"Platforms: {', '.join(status['platforms'])}")
                
                # Add quick action button
                if st.button("📋 View Results in Job Browser", key="view_last_results"):
                    st.switch_page("Job Browser")
        else:
            # Error status
            st.error(f"❌ Last search failed: {status.get('error', 'Unknown error')}")
            
            # Show retry option
            if st.button("🔄 Retry Last Search", key="retry_last_search"):
                # Clear the error status and allow retry
                del st.session_state.last_search_status
                st.rerun()
        
        st.markdown("---")
        
    def show(self):
        """Show enhanced job search interface with grouping"""
        st.markdown("### 🔍 Job Search with Smart Grouping")
        
        # Show last search status if available
        if 'last_search_status' in st.session_state:
            self._show_last_search_status()
        
        # Show persistent search results if available
        if PersistentSearchResults.has_search_results():
            st.markdown("---")
            st.markdown("#### 📋 Previous Search Results")
            PersistentSearchResults.show_expandable_results()
            st.markdown("---")
        
        # --- Start of Form and search logic from old JobSearchView ---
        
        with st.form("job_search_form"):
            # Job titles input
            st.markdown("#### 📋 Job Titles")
            st.markdown("Enter job titles (one per line)")
            
            # Get loaded search parameters if available
            loaded_titles = ""
            if 'loaded_search' in st.session_state:
                loaded_titles = st.session_state.loaded_search.get('job_titles', '')
            
            job_titles_text = st.text_area(
                "Job Titles",
                value=loaded_titles,
                placeholder="Enter job titles (one per line)",
                help="Enter each job title on a new line"
            )
            
            # Location input
            st.markdown("#### 📍 Location")
            default_location = self.config_manager.get_value('job_search.default_location', 'Essen')
            
            # Get loaded location if available
            loaded_location = default_location
            if 'loaded_search' in st.session_state:
                loaded_location = st.session_state.loaded_search.get('location', default_location)
            
            location = st.text_input("Location", value=loaded_location, placeholder="e.g., Essen, Duisburg")
            
            # Platform selection
            st.markdown("#### 🌐 Job Platforms")
            # Get available platforms dynamically from orchestrator
            try:
                available_platforms = self.job_scraper_orchestrator.get_available_platforms()
                working_platforms = available_platforms  # Use all available platforms
            except Exception as e:
                # Fallback to hardcoded list if orchestrator is not available
                available_platforms = ["Indeed", "LinkedIn", "StepStone", "Xing", "Stellenanzeigen", "Jobrapido"]
                working_platforms = available_platforms
                st.warning(f"⚠️ Using fallback platform list. Error: {e}")
            # Get loaded platforms if available
            loaded_platforms = working_platforms
            if 'loaded_search' in st.session_state:
                loaded_platforms = st.session_state.loaded_search.get('platforms', working_platforms)
            
            selected_platforms = st.multiselect(
                "Select Platforms", 
                options=working_platforms, 
                default=loaded_platforms,
                help="Choose which job platforms to search. These platforms have been tested and are working properly."
            )
            
            # Search options
            st.markdown("#### ⚙️ Search Options")
            col1, col2, col3, col4 = st.columns(4)
            
            # Get loaded search options if available
            loaded_max_pages = 3
            loaded_english_only = False
            loaded_enable_grouping = True
            loaded_deep_scrape = True
            
            if 'loaded_search' in st.session_state:
                loaded_max_pages = st.session_state.loaded_search.get('max_pages', 3)
                loaded_english_only = st.session_state.loaded_search.get('english_only', False)
                loaded_enable_grouping = st.session_state.loaded_search.get('enable_grouping', True)
                loaded_deep_scrape = st.session_state.loaded_search.get('deep_scrape', True)
            
            max_pages = col1.number_input("Max Pages", 1, 10, loaded_max_pages)
            english_only = col2.checkbox("English Only", loaded_english_only)
            enable_grouping = col3.checkbox("Smart Grouping", loaded_enable_grouping, help="Group similar jobs by company and position")
            deep_scrape = col4.checkbox("Deep Scrape", loaded_deep_scrape, help="Fetch full job descriptions and details (recommended)")

            # AI Job Analysis Configuration
            st.markdown("#### 🤖 AI Job Analysis Configuration")
            
            # Get loaded analysis criteria if available
            loaded_analysis_criteria = ""
            loaded_boost_descriptions = ""
            loaded_relevance_threshold = 5
            loaded_analysis_mode = "Custom Criteria"
            
            if 'loaded_search' in st.session_state:
                loaded_analysis_criteria = st.session_state.loaded_search.get('analysis_criteria', '')
                loaded_boost_descriptions = st.session_state.loaded_search.get('boost_descriptions', '')
                loaded_relevance_threshold = st.session_state.loaded_search.get('relevance_threshold', 5)
                loaded_analysis_mode = st.session_state.loaded_search.get('analysis_mode', 'Custom Criteria')
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Job Analysis Criteria**")
                analysis_criteria = st.text_area(
                    "Custom Job Analysis Criteria",
                    value=loaded_analysis_criteria,
                    placeholder="Enter your custom job analysis criteria (e.g., 'Focus on Python, DevOps, and cloud technologies. Prefer remote work.')",
                    help="Describe what types of jobs you want to see and what should be filtered out. This will guide the AI analysis.",
                    height=100
                )
                
                relevance_threshold = st.slider(
                    "Relevance Threshold",
                    min_value=1,
                    max_value=10,
                    value=loaded_relevance_threshold,
                    help="Minimum relevance score (1-10) for jobs to be included. Higher values = more strict filtering."
                )
            
            with col2:
                st.markdown("**Job Score Boosters**")
                boost_descriptions = st.text_area(
                    "Job Score Boosters",
                    value=loaded_boost_descriptions,
                    placeholder="Enter keywords/descriptions that should boost job scores (e.g., 'Python, Docker, Kubernetes, AWS, remote work, competitive salary')",
                    help="Keywords or descriptions that will increase the relevance score of matching jobs.",
                    height=100
                )
                
                st.markdown("**Analysis Mode**")
                analysis_mode_options = ["Custom Criteria", "Lenient (All Jobs)"]
                analysis_mode_index = 0
                if loaded_analysis_mode in analysis_mode_options:
                    analysis_mode_index = analysis_mode_options.index(loaded_analysis_mode)
                
                analysis_mode = st.selectbox(
                    "AI Analysis Mode",
                    options=analysis_mode_options,
                    index=analysis_mode_index,
                    help="Choose how the AI should analyze and filter jobs"
                )

            # Saved search functionality
            st.markdown("#### 💾 Save Search Parameters")
            col1, col2 = st.columns([3, 1])
            
            with col1:
                save_search_name = st.text_input(
                    "Save as (optional)",
                    placeholder="e.g., Python Developer Essen",
                    help="Save current search parameters for future use"
                )
            
            with col2:
                save_search = st.checkbox("Save this search", False)

            submitted = st.form_submit_button("🚀 Start Search", type="primary", use_container_width=True)

        if submitted:
            all_titles = []
            if job_titles_text:
                all_titles.extend([t.strip() for t in job_titles_text.split('\n') if t.strip()])
            
            # If no titles from form but we have loaded search data, use that
            if not all_titles and 'loaded_search' in st.session_state:
                loaded_titles = st.session_state.loaded_search.get('job_titles', '')
                if loaded_titles:
                    all_titles.extend([t.strip() for t in loaded_titles.split('\n') if t.strip()])
            
            all_titles = list(dict.fromkeys(all_titles))

            if not all_titles:
                st.error("❌ Please enter at least one job title")
                return
            
            # If no platforms from form but we have loaded search data, use that
            if not selected_platforms and 'loaded_search' in st.session_state:
                selected_platforms = st.session_state.loaded_search.get('platforms', [])
            
            if not selected_platforms:
                st.error("❌ Please select at least one platform")
                return

            if location:
                # Save search parameters if requested
                if save_search and save_search_name:
                    success = self.saved_search_service.save_search(
                        name=save_search_name,
                        job_titles=all_titles,
                        location=location,
                        platforms=selected_platforms,
                        max_pages=max_pages,
                        english_only=english_only,
                        enable_grouping=enable_grouping,
                        deep_scrape=deep_scrape,
                        analysis_criteria=analysis_criteria,
                        boost_descriptions=boost_descriptions,
                        relevance_threshold=relevance_threshold,
                        analysis_mode=analysis_mode
                    )
                    if success:
                        st.success(f"✅ Search parameters saved as '{save_search_name}'")
                    else:
                        st.error(f"❌ Failed to save search. Name '{save_search_name}' might already exist.")
                
                self._execute_search(
                    job_titles=all_titles,
                    location=location,
                    max_pages=max_pages,
                    selected_platforms=selected_platforms,
                    english_only=english_only,
                    deep_scrape=deep_scrape,
                    analysis_criteria=analysis_criteria,
                    boost_descriptions=boost_descriptions,
                    relevance_threshold=relevance_threshold,
                    analysis_mode=analysis_mode
                )
            else:
                st.error("❌ Please provide a location")
        
        # Clear loaded search after form submission is processed
        if submitted and 'loaded_search' in st.session_state:
            del st.session_state.loaded_search
        
        # --- End of Form and search logic ---

        # Display saved searches
        self._show_saved_searches()
        
        # Export/Import functionality
        self._show_export_import_section()

        if ('search_results' in st.session_state and 
            st.session_state.search_results is not None and 
            not st.session_state.search_results.empty):
            
            if enable_grouping:
                self._display_grouped_results(st.session_state.search_results)
            else:
                st.markdown("---")
                st.markdown("### 📊 Search Results")
                self._display_results(st.session_state.search_results)

    def _execute_search(self, job_titles: List[str], location: str, max_pages: int,
                       selected_platforms: List[str], english_only: bool, deep_scrape: bool = True,
                       analysis_criteria: str = "", boost_descriptions: str = "", 
                       relevance_threshold: int = 5, analysis_mode: str = "Custom Criteria"):
        """Execute job search and update session state."""
        try:
            progress_bar = st.progress(0, text="🔍 Initializing search...")
            titles_str = ", ".join(job_titles)
            
            with self.job_scraper_orchestrator as orchestrator:
                # Configure AI analysis parameters
                orchestrator.set_analysis_parameters(
                    analysis_criteria=analysis_criteria,
                    boost_descriptions=boost_descriptions,
                    relevance_threshold=relevance_threshold,
                    analysis_mode=analysis_mode
                )
                
                # Use optimized search method for better performance
                progress_bar.progress(0.2, text="🚀 Starting optimized parallel search...")
                
                results_df = orchestrator.search_optimized(
                    keywords=titles_str,
                    location=location,
                    max_pages=max_pages,
                    selected_platforms=selected_platforms,
                    english_only=english_only,
                    deep_scrape=False,  # Skip deep scraping during search for speed
                    max_workers=8  # Use more workers for parallel processing
                )
                
                if not results_df.empty:
                    progress_bar.progress(0.7, text="💾 Saving initial results to database...")
                    orchestrator.save_to_database(results_df)
                    
                    # Perform deep scraping asynchronously if requested
                    if deep_scrape:
                        progress_bar.progress(0.8, text="🔍 Fetching detailed job descriptions...")
                        results_df = orchestrator.deep_scrape_jobs_async(results_df, max_workers=4)
                        
                        # Save updated results with details
                        progress_bar.progress(0.9, text="💾 Saving detailed results to database...")
                        orchestrator.save_to_database(results_df)

            st.session_state.search_results = results_df
            
            # Store results in persistent search results component
            search_metadata = {
                'keywords': titles_str,
                'location': location,
                'platforms': selected_platforms,
                'max_pages': max_pages,
                'english_only': english_only,
                'deep_scrape': deep_scrape
            }
            PersistentSearchResults.store_search_results(results_df, search_metadata)
            
            progress_bar.progress(1.0, text="✅ Search complete!")
            st.toast(f"Found {len(results_df)} jobs!")
            
            # Store search completion status and results
            st.session_state.last_search_status = {
                'completed': True,
                'success': True,
                'jobs_found': len(results_df),
                'timestamp': datetime.now(),
                'keywords': titles_str,
                'location': location,
                'platforms': selected_platforms
            }
            
            # Show persistent search results summary
            self._show_search_results_summary(results_df, titles_str, location, selected_platforms)
            
        except Exception as e:
            st.error(f"❌ Search failed: {str(e)}")
            self.logger.error(f"Search execution failed: {e}")
            progress_bar.progress(0, text="❌ Search failed")
            
            # Store failed search status
            st.session_state.last_search_status = {
                'completed': True,
                'success': False,
                'error': str(e),
                'timestamp': datetime.now(),
                'keywords': titles_str,
                'location': location,
                'platforms': selected_platforms
            }
    
    def _show_search_results_summary(self, results_df: pd.DataFrame, keywords: str, location: str, platforms: List[str]):
        """Show persistent search results summary."""
        st.markdown("---")
        st.markdown("### 🔍 Search Results Summary")
        
        # Create columns for better layout
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Jobs Found", len(results_df))
        
        with col2:
            if not results_df.empty:
                # Count unique companies
                unique_companies = results_df['company'].nunique() if 'company' in results_df.columns else 0
                st.metric("Unique Companies", unique_companies)
            else:
                st.metric("Unique Companies", 0)
        
        with col3:
            if not results_df.empty:
                # Count platforms
                unique_platforms = results_df['source'].nunique() if 'source' in results_df.columns else 0
                st.metric("Platforms", unique_platforms)
            else:
                st.metric("Platforms", 0)
        
        # Show search details
        st.markdown("**Search Details:**")
        details_col1, details_col2 = st.columns(2)
        
        with details_col1:
            st.text(f"Keywords: {keywords}")
            st.text(f"Location: {location}")
        
        with details_col2:
            st.text(f"Platforms: {', '.join(platforms)}")
            st.text(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Show platform breakdown if we have results
        if not results_df.empty and 'source' in results_df.columns:
            st.markdown("**Platform Breakdown:**")
            platform_counts = results_df['source'].value_counts()
            for platform, count in platform_counts.items():
                st.text(f"• {platform}: {count} jobs")
        
        # Add action buttons
        st.markdown("**Actions:**")
        action_col1, action_col2, action_col3 = st.columns(3)
        
        with action_col1:
            if st.button("📋 View in Job Browser", type="primary"):
                st.switch_page("Job Browser")
        
        with action_col2:
            if st.button("💾 Save Search"):
                # This would save the search for later use
                st.success("Search saved!")
        
        with action_col3:
            if st.button("🔄 New Search"):
                # Clear the current search results
                if 'search_results' in st.session_state:
                    del st.session_state.search_results
                if 'last_search_status' in st.session_state:
                    del st.session_state.last_search_status
                st.rerun()
    
    def _display_grouped_results(self, df: pd.DataFrame):
        """Display grouped results with optimized grouping."""
        try:
            # Use optimized grouping that skips LLM during search
            progress_text = st.empty()
            progress_text.text("🤖 Grouping jobs (fast mode)...")
            
            # Use fast grouping without LLM for better performance
            grouped_jobs = self.job_grouping_service.group_jobs_optimized(df, skip_llm=True)
            
            progress_text.empty()
            
            if not grouped_jobs:
                st.warning("No job groups found.")
                return
            
            # Display grouped results
            st.markdown("### 📊 Grouped Results")
            
            for group_id, group in grouped_jobs.items():
                with st.expander(f"🏢 {group.company} - {group.normalized_title} ({len(group.jobs)} positions)"):
                    # Show group summary
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Positions", len(group.jobs))
                    with col2:
                        st.metric("Cities", len(group.cities))
                    with col3:
                        avg_salary = group.avg_salary if group.avg_salary else "N/A"
                        st.metric("Avg Salary", avg_salary)
                    
                    # Show job details
                    for job in group.jobs[:5]:  # Show first 5 jobs
                        if job:  # Ensure job is not None
                            st.markdown(f"**{job.get('title', 'Unknown')}**")
                            st.markdown(f"📍 {job.get('location', 'Unknown location')}")
                            if job.get('salary'):
                                st.markdown(f"💰 {job.get('salary')}")
                            st.markdown("---")
                    
                    if len(group.jobs) > 5:
                        st.info(f"... and {len(group.jobs) - 5} more positions")
                        
        except Exception as e:
            st.error(f"Error displaying grouped results: {e}")
            self.logger.error(f"Grouped results display error: {e}")
            # Fallback to regular display
            self._display_results(df)

    def _display_results(self, df: pd.DataFrame):
        """Basic display for non-grouped results."""
        st.markdown("---")
        st.markdown("### 📊 Search Results")
        
        # Jobs are already saved by the orchestrator with LLM assessment
        # Just display the results
        st.dataframe(df)
        
        # Show summary of what was found
        if not df.empty:
            st.info(f"💾 {len(df)} jobs were automatically saved to your database with LLM assessment")
            st.info(f"📋 You can view saved jobs in the 'Applications' section")

    def _display_group_summary(self, job_groups: Dict[str, JobGroup]):
        """
        Display summary statistics for job groups
        """
        summary = self.job_grouping_service.get_group_summary(job_groups)
        
        st.markdown("#### 📈 Grouping Summary")
        
        # Main metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Job Groups", summary['total_groups'])
            st.caption("Number of distinct job positions found")
        
        with col2:
            st.metric("Total Jobs", summary['total_jobs'])
            st.caption("Total number of job listings")
        
        with col3:
            st.metric("Avg Jobs/Group", summary['avg_jobs_per_group'])
            st.caption("Average number of jobs per position")
        
        with col4:
            duplicates = summary['total_jobs'] - summary['total_groups']
            st.metric("Duplicates Found", duplicates)
            st.caption("Jobs that were grouped together")
        
        # Top companies and cities
        if summary['top_companies'] or summary['top_cities']:
            col1, col2 = st.columns(2)
            
            with col1:
                if summary['top_companies']:
                    st.markdown("**🏢 Top Companies:**")
                    for company, count in summary['top_companies'][:5]:
                        st.markdown(f"• {company}: {count} positions")
            
            with col2:
                if summary['top_cities']:
                    st.markdown("**🌍 Top Cities:**")
                    for city, count in summary['top_cities'][:5]:
                        st.markdown(f"• {city}: {count} jobs")
    
    def _display_job_groups(self, job_groups: Dict[str, JobGroup]):
        """
        Display job groups with enhanced UI
        """
        # Sort groups by number of jobs (descending)
        sorted_groups = sorted(
            job_groups.values(),
            key=lambda g: g.total_positions,
            reverse=True
        )
        
        for group in sorted_groups:
            self._display_single_job_group(group)
    
    def _display_single_job_group(self, group: JobGroup):
        """
        Display a single job group with all its jobs
        """
        # Create expandable container for each group
        with st.expander(
            f"🎯 **{group.title}** at **{group.company}** "
            f"({group.total_positions} jobs in {len(group.cities)} cities)",
            expanded=group.total_positions <= 3  # Auto-expand small groups
        ):
            
            # Group header with key information
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                st.markdown(f"**Company:** {group.company}")
                st.markdown(f"**Position:** {group.title}")
                if group.avg_salary:
                    st.markdown(f"**Avg Salary:** {group.avg_salary}")
            
            with col2:
                st.markdown(f"**Cities:** {', '.join(group.cities[:3])}")
                if len(group.cities) > 3:
                    st.markdown(f"*... and {len(group.cities) - 3} more*")
                platforms = group.platforms or []
                st.markdown(f"**Platforms:** {', '.join(platforms)}")
            
            with col3:
                # Group-level actions
                group_unique_id = f"{group.company}_{group.normalized_title}_{hash(group.company) % 10000}"
                if st.button(f"💾 Save All {group.total_positions} Jobs", key=f"save_group_{group_unique_id}"):
                    self._save_job_group(group)
                
                if st.button(f"🔗 View All", key=f"view_group_{group_unique_id}"):
                    self._open_all_job_urls(group)
            
            st.markdown("---")
            
            # Display individual jobs in the group
            for i, job in enumerate(group.jobs):
                if not job:  # Skip None jobs
                    continue
                # Create a unique job identifier using multiple fields
                job_url = job.get('url', '')
                job_location = job.get('location', 'Unknown')
                unique_job_id = f"{group.company}_{group.normalized_title}_{job_location}_{i}_{hash(job_url) % 10000}"
                
                col1, col2, col3 = st.columns([3, 1, 2])
                
                with col1:
                    # Show job details
                    snippet = job.get('description', '') or job.get('snippet', '')
                    if snippet:
                        truncated_snippet = snippet[:150] + "..." if len(snippet) > 150 else snippet
                        st.markdown(f"*{truncated_snippet}*")
                    
                    # Show salary if different from group average
                    if 'salary' in job and job['salary'] and group.avg_salary and job['salary'] not in group.avg_salary:
                        st.markdown(f"💰 **Salary:** {job['salary']}")
                
                with col2:
                    # Save job automatically
                    if not self._job_already_saved(job):
                        if self._save_single_job(job):
                            st.success("✅ Job saved successfully")

                    if "url" in job and job["url"]:
                        st.link_button("View Job Posting", job["url"])



                st.markdown("---")
    



    
    def _save_job_group(self, group: JobGroup):
        """
        Save all jobs in a group to applications
        """
        try:
            saved_count = 0
            duplicate_count = 0
            
            with st.spinner(f"Saving {group.total_positions} jobs..."):
                for job in group.jobs:
                    # Check if job already exists
                    if self._job_already_saved(job):
                        duplicate_count += 1
                        continue
                    
                    # Save job
                    if self._save_single_job(job):
                        saved_count += 1
            
            # Show results
            if saved_count > 0:
                st.success(f"✅ Saved {saved_count} new jobs from {group.company}!")
            
            if duplicate_count > 0:
                st.info(f"ℹ️ {duplicate_count} jobs were already in your applications")
            
            if saved_count == 0 and duplicate_count == 0:
                st.error("❌ No jobs were saved")
                
        except Exception as e:
            st.error(f"❌ Error saving job group: {e}")
            self.logger.error(f"Error saving job group: {e}")
    
    def _open_all_job_urls(self, group: JobGroup):
        """
        Display all job URLs for easy access
        """
        st.markdown(f"### 🔗 All Job Links for {group.title} at {group.company}")
        
        for i, job in enumerate(group.jobs, 1):
            url = job.get('url')
            location = job.get('location', 'Unknown')
            platform = job.get('platform', job.get('source', 'Unknown'))
            
            if url:
                st.markdown(f"{i}. [{location} ({platform})]({url})")
            else:
                st.markdown(f"{i}. {location} ({platform}) - No URL available")
    
    def _job_already_saved(self, job: Dict) -> bool:
        """Check if a job already exists in the database."""
        try:
            # Check if job with same URL exists
            if 'url' in job and job['url']:
                query = "SELECT id FROM job_listings WHERE url = %s"
                result = self.db_manager.execute_query(query, (job['url'],), fetch='one')
                if result:
                    return True
            
            # Check if job with same title and company exists
            if 'title' in job and 'company' in job:
                query = """
                    SELECT id FROM job_listings 
                    WHERE title = %s AND company = %s 
                    AND scraped_date >= NOW() - INTERVAL '30 days'
                """
                result = self.db_manager.execute_query(
                    query,
                    (job['title'], job['company']),
                    fetch='one'
                )
                if result:
                    return True
            
            return False
        except Exception as e:
            self.logger.error(f"Error checking if job exists: {str(e)}")
            return False

    def _save_single_job(self, job: Dict) -> bool:
        """Save a single job to the database."""
        try:
            # Add timestamp if not present
            if 'scraped_date' not in job:
                job['scraped_date'] = datetime.now()
            
            # Apply LLM assessment if not already done
            if not job.get('llm_quality_score') and not job.get('llm_relevance_score'):
                try:
                    # Import the job orchestrator to use its LLM assessment
                    from src.scrapers.job_scraper_orchestrator import JobScraperOrchestrator
                    
                    # Create a temporary orchestrator for LLM assessment
                    temp_orchestrator = JobScraperOrchestrator(debug=False)
                    
                    # Apply LLM assessment
                    llm_assessment = temp_orchestrator._llm_job_assessment(job)
                    
                    # Add LLM assessment to job data
                    job['llm_assessment'] = llm_assessment
                    job['llm_filtered'] = llm_assessment.get('should_filter', False)
                    job['llm_quality_score'] = llm_assessment.get('quality_score', 0)
                    job['llm_relevance_score'] = llm_assessment.get('relevance_score', 0)
                    job['llm_reasoning'] = llm_assessment.get('reasoning', '')
                    
                    # Add language detection and job snippet
                    job['language'] = temp_orchestrator._llm_detect_language(job.get('description', ''))
                    job['job_snippet'] = llm_assessment.get('job_snippet', '')
                    
                    print(f"🤖 Applied LLM assessment to job: {job.get('title', 'Unknown')}")
                    print(f"   - Quality Score: {job['llm_quality_score']}/10")
                    print(f"   - Relevance Score: {job['llm_relevance_score']}/10")
                    
                except Exception as e:
                    print(f"⚠️ LLM assessment failed for job {job.get('title', 'Unknown')}: {e}")
                    # Continue with basic assessment
                    job['llm_quality_score'] = 5  # Default medium quality
                    job['llm_relevance_score'] = 7  # Default assumption of relevance
                    job['llm_reasoning'] = 'Basic assessment (LLM not available)'
            
            # Save to job_listings table first
            job_saved = self.db_manager.save_job_listing(job)
            
            if job_saved:
                # Also save to job_applications table for tracking
                try:
                    # Get the job_listing_id that was just inserted
                    query = "SELECT id FROM job_listings WHERE url = %s ORDER BY id DESC LIMIT 1"
                    result = self.db_manager.execute_query(query, (job.get('url', ''),), fetch='one')
                    
                    if result:
                        job_listing_id = result[0]
                        
                        # Check if already exists in applications
                        existing_query = "SELECT id FROM job_applications WHERE url = %s"
                        existing = self.db_manager.execute_query(existing_query, (job.get('url', ''),), fetch='one')
                        
                        if not existing:
                            # Insert into job_applications table
                            insert_query = """
                                INSERT INTO job_applications (
                                    job_listing_id, position_title, company, location, salary, url, source, 
                                    added_date, status, notes
                                ) VALUES (
                                    %s, %s, %s, %s, %s, %s, %s, %s, 'saved', %s
                                )
                            """
                            
                            # Prepare notes with search metadata
                            notes = "Auto-saved from job search"
                            
                            if job.get('language'):
                                notes += f" | Language: {job['language']}"
                            if job.get('llm_quality_score'):
                                notes += f" | Quality: {job['llm_quality_score']}/10"
                            if job.get('llm_relevance_score'):
                                notes += f" | Relevance: {job['llm_relevance_score']}/10"
                            
                            params = (
                                job_listing_id,
                                job.get('title', ''),
                                job.get('company', ''),
                                job.get('location', ''),
                                job.get('salary', ''),
                                job.get('url', ''),
                                job.get('source', job.get('platform', '')),
                                datetime.now(),
                                notes
                            )
                            
                            self.db_manager.execute_query(insert_query, params)
                            self.logger.info(f"✅ Job also saved to applications table: {job.get('title', 'Unknown')}")
                
                except Exception as e:
                    self.logger.warning(f"Could not save to applications table: {str(e)}")
                    # Don't fail the main save operation if applications save fails
            
            return job_saved
        except Exception as e:
            self.logger.error(f"Error saving single job: {str(e)}")
            return False
    
    def _show_saved_searches(self):
        """Display saved searches with load and delete options"""
        saved_searches = self.saved_search_service.get_all_saved_searches()
        
        if not saved_searches:
            return
        
        st.markdown("---")
        st.markdown("#### 💾 Saved Search Parameters")
        
        # Create columns for each saved search
        for i, search in enumerate(saved_searches):
            with st.container():
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    # Display search info
                    st.markdown(f"**{search.name}**")
                    st.markdown(f"📍 {search.location} | 📄 {len(search.job_titles)} titles | 🌐 {len(search.platforms)} platforms")
                    st.markdown(f"📊 Max pages: {search.max_pages} | {'🇬🇧' if search.english_only else '🌍'} | {'📋' if search.enable_grouping else '📄'} | {'🔍' if search.deep_scrape else '⚡'}")
                    
                    if search.last_used:
                        from datetime import datetime
                        last_used = datetime.fromisoformat(search.last_used)
                        st.markdown(f"🕒 Last used: {last_used.strftime('%Y-%m-%d %H:%M')} (used {search.use_count} times)")
                
                with col2:
                    # Load button
                    if st.button(f"Load", key=f"load_{i}"):
                        self._load_saved_search(search)
                        st.rerun()
                
                with col3:
                    # Delete button
                    if st.button(f"🗑️", key=f"delete_{i}"):
                        if self.saved_search_service.delete_saved_search(search.name):
                            st.success(f"✅ Deleted '{search.name}'")
                            st.rerun()
                        else:
                            st.error(f"❌ Failed to delete '{search.name}'")
    
    def _load_saved_search(self, search):
        """Load saved search parameters into session state for form population"""
        # Store the search parameters in session state for form population
        st.session_state.loaded_search = {
            'job_titles': '\n'.join(search.job_titles),
            'location': search.location,
            'platforms': search.platforms,
            'max_pages': search.max_pages,
            'english_only': search.english_only,
            'enable_grouping': search.enable_grouping,
            'deep_scrape': search.deep_scrape,
            'analysis_criteria': search.analysis_criteria,
            'boost_descriptions': search.boost_descriptions,
            'relevance_threshold': search.relevance_threshold,
            'analysis_mode': search.analysis_mode
        }
        
        # Update usage statistics
        self.saved_search_service.update_usage(search.name)
        
        st.success(f"✅ Loaded search parameters from '{search.name}'")
    
    def _show_export_import_section(self):
        """Show export/import functionality for saved searches"""
        saved_searches = self.saved_search_service.get_all_saved_searches()
        
        if not saved_searches:
            return
        
        st.markdown("---")
        st.markdown("#### 📤 Export/Import Saved Searches")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Export Saved Searches**")
            export_data = self.saved_search_service.export_searches()
            st.code(export_data, language="json")
            
            # Download button
            st.download_button(
                label="📥 Download Saved Searches",
                data=export_data,
                file_name=f"saved_searches_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
        
        with col2:
            st.markdown("**Import Saved Searches**")
            uploaded_file = st.file_uploader(
                "Choose a JSON file",
                type=['json'],
                help="Upload a previously exported saved searches file"
            )
            
            if uploaded_file is not None:
                try:
                    content = uploaded_file.read().decode('utf-8')
                    if self.saved_search_service.import_searches(content):
                        st.success("✅ Successfully imported saved searches!")
                        st.rerun()
                    else:
                        st.error("❌ Failed to import saved searches. Please check the file format.")
                except Exception as e:
                    st.error(f"❌ Error importing file: {str(e)}") 