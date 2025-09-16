"""
Job Browser View
Comprehensive view of all jobs found with LLM-enhanced snippets and action management.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging
import json
from views.base_view import BaseView
from src.database.database_manager import get_db_manager

class JobBrowserView(BaseView):
    """View for browsing all discovered jobs with enhanced features."""
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.db_manager = get_db_manager()
        
        # Initialize LLM client for enhanced snippets
        try:
            from ollama_client import ollama_client
            self.ollama_client = ollama_client
        except ImportError:
            self.ollama_client = None
            self.logger.warning("Ollama client not available")
    
    def show(self):
        """Show the job browser interface."""
        st.markdown("# 🔍 Job Browser")
        st.markdown("Browse all discovered jobs with AI-enhanced insights and management tools.")
        
        # Add some CSS for better navigation experience
        st.markdown("""
        <style>
        .stButton > button {
            border-radius: 5px;
            font-weight: 500;
        }
        .stProgress > div > div > div > div {
            background-color: #1f77b4;
        }
        </style>
        """, unsafe_allow_html=True)
    
        # Filters and controls
        self._show_filters()
        
        # Show search status if active
        current_filters = st.session_state.get('job_browser_filters', {})
        search_title = current_filters.get('search_title', '').strip()
        search_company = current_filters.get('search_company', '').strip()
        
        if search_title or search_company:
            search_info = []
            if search_title:
                search_info.append(f"**Job Title:** '{search_title}'")
            if search_company:
                search_info.append(f"**Company:** '{search_company}'")
            
            st.info(f"🔍 **Searching for:** {' and '.join(search_info)}")
        
        # Load and display jobs
        jobs_df = self._load_jobs()
        
        if jobs_df.empty:
            st.warning("📭 No jobs found with current filters.")
            st.info("💡 **Troubleshooting Tips:**")
            st.info("- Try changing the **Date Range** filter to 'All Time'")
            st.info("- Make sure **Status** is set to 'All Jobs' or '✅ Approved Only'")
            st.info("- Check if **Source** filter is not too restrictive")
            st.info("- Use the 🔄 Refresh button to reload data")
            
            # Show a button to reset filters
            if st.button("🔄 Reset All Filters", type="primary"):
                if 'job_browser_filters' in st.session_state:
                    del st.session_state.job_browser_filters
                st.rerun()
            return
        
        # Show statistics
        self._show_statistics(jobs_df)
        
        # Display jobs
        self._display_jobs(jobs_df)
    
    def _show_filters(self):
        """Show filtering and sorting controls."""
        st.markdown("### 🎛️ Filters & Controls")
        
        # Search Row
        st.markdown("#### 🔍 Search Jobs")
        search_col1, search_col2, search_col3, search_col4 = st.columns([2, 2, 1, 1])
        
        with search_col1:
            search_title = st.text_input(
                "🔍 Search Job Title", 
                value=st.session_state.get('job_browser_filters', {}).get('search_title', ''),
                placeholder="e.g., System Administrator, DevOps Engineer",
                help="Search for specific job titles"
            )
        
        with search_col2:
            search_company = st.text_input(
                "🏢 Search Company", 
                value=st.session_state.get('job_browser_filters', {}).get('search_company', ''),
                placeholder="e.g., Google, Microsoft, Startup",
                help="Search for specific companies"
            )
        
        with search_col3:
            st.markdown("")  # Add some spacing
            if st.button("🔍 Search", type="primary", use_container_width=True):
                st.rerun()
        
        with search_col4:
            st.markdown("")  # Add some spacing
            if st.button("🗑️ Clear Search", use_container_width=True):
                # Clear search filters
                if 'job_browser_filters' in st.session_state:
                    st.session_state.job_browser_filters['search_title'] = ''
                    st.session_state.job_browser_filters['search_company'] = ''
                st.rerun()
        
        # Row 1: Date, Status, Source, Language
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            date_options = ["All Time", "Last 24 Hours", "Last Week", "Last Month"]
            # Default to "All Time" to show all jobs
            current_date_filter = st.session_state.get('job_browser_filters', {}).get('date', 'All Time')
            date_index = date_options.index(current_date_filter) if current_date_filter in date_options else 0
            selected_date = st.selectbox("📅 Date Range", date_options, index=date_index)
            
        with col2:
            status_options = ["All Jobs", "✅ Approved Only", "🚫 Filtered Only", "📝 Applied", "🙈 Ignored"]
            # Default to "✅ Approved Only" to show approved jobs
            current_status_filter = st.session_state.get('job_browser_filters', {}).get('status', '✅ Approved Only')
            status_index = status_options.index(current_status_filter) if current_status_filter in status_options else 0
            selected_status = st.selectbox("🏷️ Status", status_options, index=status_index)
            
        with col3:
            # Add source filter
            source_options = ["All Sources"] + self._get_all_sources()
            current_source_filter = st.session_state.get('job_browser_filters', {}).get('source', 'All Sources')
            selected_source = st.selectbox("🔗 Source", source_options, index=source_options.index(current_source_filter) if current_source_filter in source_options else 0)

        with col4:
            language_options = ["All Languages", "🇬🇧 English", "🇩🇪 German", "🌐 Others"]
            current_language_filter = st.session_state.get('job_browser_filters', {}).get('language', 'All Languages')
            language_index = language_options.index(current_language_filter) if current_language_filter in language_options else 0
            selected_language = st.selectbox("🌐 Language", language_options, index=language_index)
        
        # Row 2: Location, Sort, Refresh
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            # Add location filter
            common_cities = ["Essen", "Berlin", "Hamburg", "Munich", "Frankfurt", "Cologne", "Düsseldorf", "Stuttgart", "Dortmund", "Leipzig"]
            db_locations = self._get_all_locations()
            
            # Combine common cities with database locations, avoiding duplicates
            all_locations = ["All Locations"] + common_cities
            for loc in db_locations:
                if loc not in all_locations:
                    all_locations.append(loc)
            
            location_options = all_locations
            current_location_filter = st.session_state.get('job_browser_filters', {}).get('location', 'All Locations')
            location_index = location_options.index(current_location_filter) if current_location_filter in location_options else 0
            selected_location = st.selectbox("📍 Location", location_options, index=location_index)
            
        with col2:
            sort_options = ["Newest First", "Quality Score", "Relevance Score", "Company A-Z"]
            current_sort_filter = st.session_state.get('job_browser_filters', {}).get('sort', 'Newest First')
            sort_index = sort_options.index(current_sort_filter) if current_sort_filter in sort_options else 0
            selected_sort = st.selectbox("📊 Sort By", sort_options, index=sort_index)
        
        # Store filters in session state
        new_filters = {
            'date': selected_date,
            'status': selected_status,
            'source': selected_source,
            'language': selected_language,
            'location': selected_location,
            'sort': selected_sort,
            'search_title': search_title,
            'search_company': search_company
        }
        
        # Check if filters have changed
        old_filters = st.session_state.get('job_browser_filters', {})
        filters_changed = new_filters != old_filters
        
        st.session_state.job_browser_filters = new_filters
        
        # Reset pagination when filters change
        if filters_changed:
            st.session_state.current_page = 1
        
        # Refresh button
        with col3:
            if st.button("🔄 Refresh", type="secondary"):
                st.rerun()
        
        # Test location filter button
        with col4:
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🧪 Test Location Filter", type="secondary"):
                    self._test_location_filter()
            with col2:
                if st.button("🔍 Test Combined Filters", type="secondary"):
                    self._test_combined_filters()
    
    def _get_all_sources(self) -> List[str]:
        """Fetch all unique job sources from the database."""
        try:
            query = "SELECT DISTINCT source FROM job_listings WHERE source IS NOT NULL ORDER BY source"
            results = self.db_manager.execute_query(query, fetch='all')
            return [row[0] for row in results] if results else []
        except Exception as e:
            self.logger.error(f"Error fetching job sources: {e}")
            return []
    
    def _get_all_locations(self) -> List[str]:
        """Fetch all unique job locations from the database."""
        try:
            # Get locations with case-insensitive grouping
            query = """
                SELECT DISTINCT 
                    CASE 
                        WHEN location IS NULL OR location = '' THEN NULL
                        ELSE TRIM(location)
                    END as location
                FROM job_listings 
                WHERE location IS NOT NULL 
                AND location != '' 
                AND TRIM(location) != ''
                ORDER BY location
            """
            results = self.db_manager.execute_query(query, fetch='all')
            locations = [row[0] for row in results if row[0]]  # Filter out None values
            
            # Log for debugging
            self.logger.info(f"Found {len(locations)} unique locations in database")
            if locations:
                self.logger.info(f"Sample locations: {locations[:10]}")
            
            return locations
        except Exception as e:
            self.logger.error(f"Error fetching job locations: {e}")
            return []
    
    def _load_jobs(self) -> pd.DataFrame:
        """Load jobs from database with applied filters."""
        try:
            # Debug: First check if there are any jobs at all
            total_jobs_query = "SELECT COUNT(*) FROM job_listings"
            total_result = self.db_manager.execute_query(total_jobs_query, fetch='one')
            total_count = total_result[0] if total_result else 0
            self.logger.info(f"Total jobs in database: {total_count}")
            
            if total_count == 0:
                self.logger.warning("No jobs found in database at all!")
                return pd.DataFrame()
            base_query = """
                SELECT 
                    id, title, company, location, salary, url, source,
                    scraped_date, posted_date, description, language,
                    job_snippet, llm_filtered, llm_quality_score,
                    llm_relevance_score, llm_reasoning,
                    CASE 
                        WHEN url IN (SELECT url FROM job_applications) THEN 'applied'
                        WHEN id IN (SELECT job_listing_id FROM ignored_jobs) THEN 'ignored'
                        ELSE 'available'
                    END as job_status
                FROM job_listings 
                WHERE 1=1
            """
            
            filters = st.session_state.get('job_browser_filters', {})
            params = []
            
            # Debug: Log current filters
            self.logger.info(f"Current Job Browser filters: {filters}")
            
            # Apply filters
            if filters.get('date') == "Last 24 Hours":
                base_query += " AND scraped_date >= %s"
                params.append(datetime.now() - timedelta(days=1))
            elif filters.get('date') == "Last Week":
                base_query += " AND scraped_date >= %s"
                params.append(datetime.now() - timedelta(weeks=1))
            elif filters.get('date') == "Last Month":
                base_query += " AND scraped_date >= %s"
                params.append(datetime.now() - timedelta(days=30))
            
            status_filter = filters.get('status')
            
            if status_filter == "🙈 Ignored":
                base_query += " AND id IN (SELECT job_listing_id FROM ignored_jobs)"
            elif status_filter == "✅ Approved Only":
                # Show only approved jobs that are NOT applied and NOT ignored
                base_query += " AND (llm_filtered = false OR llm_filtered IS NULL)"
                base_query += " AND url NOT IN (SELECT url FROM job_applications)"
                base_query += " AND id NOT IN (SELECT job_listing_id FROM ignored_jobs)"
            elif status_filter == "🚫 Filtered Only":
                # Show only filtered jobs that are NOT ignored
                base_query += " AND llm_filtered = true"
                base_query += " AND id NOT IN (SELECT job_listing_id FROM ignored_jobs)"
            elif status_filter == "📝 Applied":
                # Show only applied jobs
                base_query += " AND url IN (SELECT url FROM job_applications)"
            # For "All Jobs" - don't add any status filters, show everything
            
            # Source filter
            if filters.get('source') and filters.get('source') != "All Sources":
                base_query += " AND source = %s"
                params.append(filters.get('source'))

            if filters.get('language') == "🇬🇧 English":
                base_query += " AND language = 'en'"
            elif filters.get('language') == "🇩🇪 German":
                base_query += " AND language = 'de'"
            elif filters.get('language') == "🌐 Others":
                base_query += " AND (language NOT IN ('en', 'de') OR language IS NULL)"
            
            # Location filter
            if filters.get('location') and filters.get('location') != "All Locations":
                # Use case-insensitive matching and handle partial matches
                base_query += " AND LOWER(location) LIKE LOWER(%s)"
                # Add wildcards for partial matching
                location_param = f"%{filters.get('location')}%"
                params.append(location_param)
            
            # Search filters
            search_title = filters.get('search_title', '').strip()
            search_company = filters.get('search_company', '').strip()
            
            # Job title search
            if search_title:
                base_query += " AND LOWER(title) LIKE LOWER(%s)"
                title_param = f"%{search_title}%"
                params.append(title_param)
            
            # Company search
            if search_company:
                base_query += " AND LOWER(company) LIKE LOWER(%s)"
                company_param = f"%{search_company}%"
                params.append(company_param)
            
            # Sort order
            if filters.get('sort') == "Quality Score":
                base_query += " ORDER BY llm_quality_score DESC NULLS LAST"
            elif filters.get('sort') == "Relevance Score":
                base_query += " ORDER BY llm_relevance_score DESC NULLS LAST"
            elif filters.get('sort') == "Company A-Z":
                base_query += " ORDER BY company ASC"
            else:
                base_query += " ORDER BY scraped_date DESC"
            
            # Debug: Log the query being executed
            self.logger.info(f"Executing Job Browser query with {len(params)} parameters")
            self.logger.debug(f"Query: {base_query}")
            self.logger.debug(f"Params: {params}")
            
            result = self.db_manager.execute_query(base_query, params, fetch='all')
            
            # Debug: Log query results
            self.logger.info(f"Job Browser query returned {len(result) if result else 0} rows")
            
            if result:
                columns = [
                    'id', 'title', 'company', 'location', 'salary', 'url', 'source',
                    'scraped_date', 'posted_date', 'description', 'language',
                    'job_snippet', 'llm_filtered', 'llm_quality_score',
                    'llm_relevance_score', 'llm_reasoning', 'job_status'
                ]
                df = pd.DataFrame(result, columns=columns)
                return df
            else:
                return pd.DataFrame()
                
        except Exception as e:
            self.logger.error(f"Error loading jobs: {e}")
            st.error(f"Error loading jobs: {e}")
            return pd.DataFrame()
    
    def _show_statistics(self, df: pd.DataFrame):
        """Show job statistics dashboard."""
        st.markdown("### 📊 Job Statistics")
        
        # Check if search filters are active
        current_filters = st.session_state.get('job_browser_filters', {})
        search_title = current_filters.get('search_title', '').strip()
        search_company = current_filters.get('search_company', '').strip()
        has_search = search_title or search_company
        
        if has_search:
            st.info(f"🔍 **Search Results:** Found {len(df)} jobs matching your search criteria")
        
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        
        with col1:
            st.metric("Total Jobs", len(df))
        with col2:
            # Count approved jobs (not filtered by LLM and not applied)
            approved_jobs = len(df[(df['llm_filtered'] == False) & (df['job_status'] != 'applied')])
            st.metric("✅ Approved", approved_jobs)
        with col3:
            filtered_jobs = len(df[df['llm_filtered'] == True])
            st.metric("🚫 Filtered", filtered_jobs)
        with col4:
            applied_jobs = len(df[df['job_status'] == 'applied'])
            st.metric("📝 Applied", applied_jobs)
        with col5:
            ignored_jobs = len(df[df['job_status'] == 'ignored'])
            st.metric("🙈 Ignored", ignored_jobs)
        with col6:
            # Count jobs with cached details
            cached_count = 0
            for _, job in df.iterrows():
                job_url = job.get('url', '')
                if job_url:
                    cached_details = self.db_manager.get_cached_job_details(job_url)
                    if cached_details:
                        cached_count += 1
            st.metric("📋 Cached Details", cached_count)
    
    def _display_jobs(self, df: pd.DataFrame):
        """Display jobs with enhanced features."""
        st.markdown("### 💼 Job Listings")
        
        # Multi-select functionality
        if 'selected_jobs' not in st.session_state:
            st.session_state.selected_jobs = set()
        
        # Bulk actions
        if st.session_state.selected_jobs:
            st.markdown("#### 🎯 Bulk Actions")
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                if st.button("🙈 Ignore Selected", type="primary", use_container_width=True):
                    self._bulk_ignore_jobs(df, st.session_state.selected_jobs)
            
            with col2:
                if st.button("📝 Apply to Selected", use_container_width=True):
                    self._bulk_apply_jobs(df, st.session_state.selected_jobs)
            
            with col3:
                if st.button("📋 Fetch Details", use_container_width=True):
                    self._bulk_fetch_job_details(df, st.session_state.selected_jobs)
            
            with col4:
                if st.button("🗑️ Clear Selection", use_container_width=True):
                    st.session_state.selected_jobs.clear()
                    st.rerun()
            
            with col5:
                st.markdown(f"**Selected {len(st.session_state.selected_jobs)} jobs**")
        else:
            # Show select all option when no jobs are selected
            st.markdown("#### 🎯 Bulk Actions")
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("☑️ Select All Jobs", use_container_width=True):
                    st.session_state.selected_jobs = set(df['id'].tolist())
                    st.rerun()
            
            with col2:
                st.markdown("**No jobs selected**")
        
        st.divider()
        
        # Enhanced Pagination
        jobs_per_page = st.session_state.get('jobs_per_page', 10)
        total_pages = (len(df) - 1) // jobs_per_page + 1
        current_page = st.session_state.get('current_page', 1)
        
        # Store user preference for jobs per page
        if 'jobs_per_page' not in st.session_state:
            st.session_state.jobs_per_page = 10
        
        # Ensure current page is within valid range
        if current_page > total_pages:
            current_page = 1
        if current_page < 1:
            current_page = 1
        
        # Pagination controls
        if total_pages > 1:
            st.markdown("### 📄 Navigation")
            
            # Page size selector
            col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 1])
            
            with col1:
                new_jobs_per_page = st.selectbox(
                    "Jobs per page",
                    [5, 10, 15, 20, 25, 50],
                    index=[5, 10, 15, 20, 25, 50].index(jobs_per_page),
                    key="jobs_per_page_selector"
                )
                if new_jobs_per_page != jobs_per_page:
                    st.session_state.jobs_per_page = new_jobs_per_page
                    st.session_state.current_page = 1
                    st.rerun()
            
            with col2:
                st.markdown(f"**Page {current_page} of {total_pages}**")
            
            with col3:
                st.markdown(f"**Showing {len(df)} total jobs**")
            
            # Navigation buttons
            nav_col1, nav_col2, nav_col3, nav_col4, nav_col5 = st.columns([1, 1, 1, 1, 1])
            
            with nav_col1:
                if st.button("⏮️ First", disabled=current_page == 1, use_container_width=True):
                    st.session_state.current_page = 1
                    st.rerun()
            
            with nav_col2:
                if st.button("◀️ Previous", disabled=current_page == 1, use_container_width=True):
                    st.session_state.current_page = current_page - 1
                    st.rerun()
            
            with nav_col3:
                # Page number input
                new_page = st.number_input(
                    "Go to page",
                    min_value=1,
                    max_value=total_pages,
                    value=current_page,
                    key="page_input"
                )
                if new_page != current_page:
                    st.session_state.current_page = new_page
                    st.rerun()
            
            with nav_col4:
                if st.button("Next ▶️", disabled=current_page == total_pages, use_container_width=True):
                    st.session_state.current_page = current_page + 1
                    st.rerun()
            
            with nav_col5:
                if st.button("Last ⏭️", disabled=current_page == total_pages, use_container_width=True):
                    st.session_state.current_page = total_pages
                    st.rerun()
            
            # Page jump shortcuts for large datasets
            if total_pages > 10:
                st.markdown("**Quick Navigation:**")
                quick_nav_cols = st.columns(min(10, total_pages))
                
                # Show first 5 pages, last 5 pages, and current page vicinity
                pages_to_show = set()
                pages_to_show.update(range(1, min(6, total_pages + 1)))  # First 5 pages
                pages_to_show.update(range(max(1, current_page - 2), min(total_pages + 1, current_page + 3)))  # Current page vicinity
                pages_to_show.update(range(max(1, total_pages - 4), total_pages + 1))  # Last 5 pages
                
                pages_to_show = sorted(list(pages_to_show))
                
                for i, page_num in enumerate(pages_to_show):
                    if i < len(quick_nav_cols):
                        with quick_nav_cols[i]:
                            if st.button(
                                f"📄 {page_num}",
                                key=f"quick_nav_{page_num}",
                                use_container_width=True,
                                type="secondary" if page_num == current_page else "primary"
                            ):
                                st.session_state.current_page = page_num
                                st.rerun()
            
            # Jump to specific job feature
            st.markdown("**🔍 Jump to Job:**")
            jump_col1, jump_col2 = st.columns([2, 1])
            
            with jump_col1:
                job_search_term = st.text_input(
                    "Search for a specific job by title or company",
                    placeholder="e.g., 'System Administrator' or 'Google'",
                    key="job_search_jump"
                )
            
            with jump_col2:
                if st.button("🔍 Find Job", use_container_width=True):
                    if job_search_term.strip():
                        self._jump_to_job(df, job_search_term.strip())
            
            # Keyboard navigation hints
            st.markdown("**⌨️ Navigation Tips:**")
            st.markdown("- Use the **Previous/Next** buttons or **page input** to navigate")
            st.markdown("- **Quick Navigation** buttons for jumping to specific pages")
            st.markdown("- **Jobs per page** selector to adjust view size")
            st.markdown("- **Jump to Job** to find specific positions quickly")
            
            st.divider()
        else:
            current_page = 1
        
        # Calculate page data
        start_idx = (current_page - 1) * jobs_per_page
        end_idx = start_idx + jobs_per_page
        page_df = df.iloc[start_idx:end_idx]
        
        # Show current page info with progress bar
        if total_pages > 1:
            # Progress bar for page navigation
            progress = current_page / total_pages
            st.progress(progress, text=f"📄 Page {current_page} of {total_pages}")
            
            # Page info
            st.info(f"📄 **Page {current_page} of {total_pages}** - Showing jobs {start_idx + 1} to {min(end_idx, len(df))} of {len(df)} total jobs")
            
            # Navigation status
            if current_page == 1:
                st.success("📍 You're on the first page")
            elif current_page == total_pages:
                st.success("📍 You're on the last page")
            else:
                st.info(f"📍 {total_pages - current_page} pages remaining")
            
            # Page summary
            page_jobs = page_df
            if not page_jobs.empty:
                approved_count = len(page_jobs[page_jobs['llm_filtered'] == False])
                filtered_count = len(page_jobs[page_jobs['llm_filtered'] == True])
                applied_count = len(page_jobs[page_jobs['job_status'] == 'applied'])
                
                summary_cols = st.columns(4)
                with summary_cols[0]:
                    st.metric("Jobs on this page", len(page_jobs))
                with summary_cols[1]:
                    st.metric("✅ Approved", approved_count)
                with summary_cols[2]:
                    st.metric("🚫 Filtered", filtered_count)
                with summary_cols[3]:
                    st.metric("📝 Applied", applied_count)
        
        for idx, job in page_df.iterrows():
            self._display_job_card(job, idx)
        
        # Bottom navigation controls
        if total_pages > 1:
            st.markdown("---")
            st.markdown("### 📄 Bottom Navigation")
            
            # Bottom page size selector
            bottom_col1, bottom_col2, bottom_col3, bottom_col4, bottom_col5 = st.columns([1, 1, 1, 1, 1])
            
            with bottom_col1:
                bottom_jobs_per_page = st.selectbox(
                    "Jobs per page",
                    [5, 10, 15, 20, 25, 50],
                    index=[5, 10, 15, 20, 25, 50].index(jobs_per_page),
                    key="bottom_jobs_per_page_selector"
                )
                if bottom_jobs_per_page != jobs_per_page:
                    st.session_state.jobs_per_page = bottom_jobs_per_page
                    st.session_state.current_page = 1
                    st.rerun()
            
            with bottom_col2:
                st.markdown(f"**Page {current_page} of {total_pages}**")
            
            with bottom_col3:
                st.markdown(f"**Showing {len(df)} total jobs**")
            
            # Bottom navigation buttons
            bottom_nav_col1, bottom_nav_col2, bottom_nav_col3, bottom_nav_col4, bottom_nav_col5 = st.columns([1, 1, 1, 1, 1])
            
            with bottom_nav_col1:
                if st.button("⏮️ First", disabled=current_page == 1, use_container_width=True, key="bottom_first"):
                    st.session_state.current_page = 1
                    st.rerun()
            
            with bottom_nav_col2:
                if st.button("◀️ Previous", disabled=current_page == 1, use_container_width=True, key="bottom_previous"):
                    st.session_state.current_page = current_page - 1
                    st.rerun()
            
            with bottom_nav_col3:
                # Bottom page number input
                bottom_new_page = st.number_input(
                    "Go to page",
                    min_value=1,
                    max_value=total_pages,
                    value=current_page,
                    key="bottom_page_input"
                )
                if bottom_new_page != current_page:
                    st.session_state.current_page = bottom_new_page
                    st.rerun()
            
            with bottom_nav_col4:
                if st.button("Next ▶️", disabled=current_page == total_pages, use_container_width=True, key="bottom_next"):
                    st.session_state.current_page = current_page + 1
                    st.rerun()
            
            with bottom_nav_col5:
                if st.button("Last ⏭️", disabled=current_page == total_pages, use_container_width=True, key="bottom_last"):
                    st.session_state.current_page = total_pages
                    st.rerun()
            
            # Bottom quick navigation for large datasets
            if total_pages > 10:
                st.markdown("**Quick Navigation:**")
                bottom_quick_nav_cols = st.columns(min(10, total_pages))
                
                # Show first 5 pages, last 5 pages, and current page vicinity
                bottom_pages_to_show = set()
                bottom_pages_to_show.update(range(1, min(6, total_pages + 1)))  # First 5 pages
                bottom_pages_to_show.update(range(max(1, current_page - 2), min(total_pages + 1, current_page + 3)))  # Current page vicinity
                bottom_pages_to_show.update(range(max(1, total_pages - 4), total_pages + 1))  # Last 5 pages
                
                bottom_pages_to_show = sorted(list(bottom_pages_to_show))
                
                for i, page_num in enumerate(bottom_pages_to_show):
                    if i < len(bottom_quick_nav_cols):
                        with bottom_quick_nav_cols[i]:
                            if st.button(
                                f"📄 {page_num}",
                                key=f"bottom_quick_nav_{page_num}",
                                use_container_width=True,
                                type="secondary" if page_num == current_page else "primary"
                            ):
                                st.session_state.current_page = page_num
                                st.rerun()
            
            # Bottom jump to job feature
            st.markdown("**🔍 Jump to Job:**")
            bottom_jump_col1, bottom_jump_col2 = st.columns([2, 1])
            
            with bottom_jump_col1:
                bottom_job_search_term = st.text_input(
                    "Search for a specific job by title or company",
                    placeholder="e.g., 'System Administrator' or 'Google'",
                    key="bottom_job_search_jump"
                )
            
            with bottom_jump_col2:
                if st.button("🔍 Find Job", use_container_width=True, key="bottom_find_job"):
                    if bottom_job_search_term.strip():
                        self._jump_to_job(df, bottom_job_search_term.strip())
            
            # Bottom progress bar
            bottom_progress = current_page / total_pages
            st.progress(bottom_progress, text=f"📄 Page {current_page} of {total_pages}")
            
            # Bottom page info
            st.info(f"📄 **Page {current_page} of {total_pages}** - Showing jobs {start_idx + 1} to {min(end_idx, len(df))} of {len(df)} total jobs")
            
            # Bottom navigation status
            if current_page == 1:
                st.success("📍 You're on the first page")
            elif current_page == total_pages:
                st.success("📍 You're on the last page")
            else:
                st.info(f"📍 {total_pages - current_page} pages remaining")
            
            # Bottom page summary
            if not page_df.empty:
                bottom_approved_count = len(page_df[page_df['llm_filtered'] == False])
                bottom_filtered_count = len(page_df[page_df['llm_filtered'] == True])
                bottom_applied_count = len(page_df[page_df['job_status'] == 'applied'])
                
                bottom_summary_cols = st.columns(4)
                with bottom_summary_cols[0]:
                    st.metric("Jobs on this page", len(page_df))
                with bottom_summary_cols[1]:
                    st.metric("✅ Approved", bottom_approved_count)
                with bottom_summary_cols[2]:
                    st.metric("🚫 Filtered", bottom_filtered_count)
                with bottom_summary_cols[3]:
                    st.metric("📝 Applied", bottom_applied_count)
        
        # Back to top button for long pages
        if total_pages > 1 and len(page_df) > 5:
            st.markdown("---")
            col1, col2, col3 = st.columns([1, 1, 1])
            with col2:
                if st.button("⬆️ Back to Top", use_container_width=True, key="back_to_top"):
                    st.rerun()
    
    def _display_job_card(self, job: pd.Series, idx: int):
        """Display individual job card with enhanced features."""
        with st.container():
            status_emoji = {'applied': '📝', 'ignored': '🙈', 'available': '🆕'}
            
            # Multi-select checkbox
            job_id = job.get('id')
            is_selected = job_id in st.session_state.selected_jobs
            
            col1, col2 = st.columns([1, 4])
            with col1:
                # Add visual indicator for selected jobs
                if is_selected:
                    st.markdown("✅")
                if st.checkbox("Select job", value=is_selected, key=f"select_{job_id}_{idx}", label_visibility="collapsed"):
                    st.session_state.selected_jobs.add(job_id)
                else:
                    st.session_state.selected_jobs.discard(job_id)
            
            with col2:
                # Add selection indicator to job title
                selection_indicator = "**🔒 SELECTED** " if is_selected else ""
                status = job.get('job_status', 'available')
                
                # Header
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.markdown(f"## {status_emoji.get(status, '🆕')} {selection_indicator}{job.get('title', 'Unknown Title')}")
                with col2:
                    quality_score = job.get('llm_quality_score', 0)
                    if quality_score > 0:
                        color = "🟢" if quality_score >= 7 else "🟡" if quality_score >= 5 else "🔴"
                        st.markdown(f"**Quality:** {color} {quality_score}/10")
                
                # Basic info
                col1, col2, col3 = st.columns([2, 2, 1])
                
                with col1:
                    st.markdown(f"**🏢 Company:** {job.get('company', 'Unknown')}")
                    st.markdown(f"**📍 Location:** {job.get('location', 'Unknown')}")
                
                with col2:
                    language = str(job.get('language', 'unknown') or 'unknown').lower()
                    if language == 'nan':
                        language = 'unknown'
                    lang_flag = {'en': '🇬🇧', 'de': '🇩🇪', 'fr': '🇫🇷', 'es': '🇪🇸'}.get(language, '🌐')
                    st.markdown(f"**🌐 Language:** {lang_flag} {language.upper()}")
                    st.markdown(f"**🔗 Source:** {job.get('source', 'Unknown')}")
                
                with col3:
                    scraped_date = job.get('scraped_date')
                    if scraped_date:
                        try:
                            if isinstance(scraped_date, str):
                                scraped_date = datetime.fromisoformat(scraped_date.replace('Z', '+00:00'))
                            if isinstance(scraped_date, datetime):
                                st.markdown(f"**📅 Found:** {scraped_date.strftime('%Y-%m-%d')}")
                        except:
                            pass
                    
                    posted_date = job.get('posted_date')
                    if posted_date:
                        try:
                            if isinstance(posted_date, str):
                                posted_date = datetime.fromisoformat(posted_date.replace('Z', '+00:00'))
                            if isinstance(posted_date, datetime):
                                st.markdown(f"**✍️ Posted:** {posted_date.strftime('%Y-%m-%d')}")
                        except:
                            pass
                
                # Job snippet
                snippet = job.get('job_snippet', '')
                if not snippet and self.ollama_client:
                    snippet = self._generate_job_snippet(job)
                
                if snippet:
                    st.markdown("**💼 Key Responsibilities:**")
                    st.markdown(f"*{snippet}*")
                
                # Salary
                salary = job.get('salary', '')
                if salary and str(salary).strip() and str(salary) != 'nan':
                    st.markdown(f"**💰 Salary:** {salary}")
                
                # Check if cached details are available
                job_url = job.get('url', '')
                cached_details_available = False
                if job_url:
                    cached_details = self.db_manager.get_cached_job_details(job_url)
                    cached_details_available = cached_details is not None
                
                # Show cached details indicator
                if cached_details_available:
                    st.success("📋 Cached details available - Click 'Full Details' to view")
                else:
                    st.info("📋 No cached details - Job details may not have been fetched yet")
                
                # LLM Assessment for filtered jobs
                if job.get('llm_filtered') == True:
                    with st.expander("🤖 AI Assessment - Why this job was filtered"):
                        reasoning = job.get('llm_reasoning', 'No reasoning available')
                        st.write(reasoning)
                
                # Action buttons
                st.markdown("**Actions:**")
                col1, col2, col3, col4, col5 = st.columns(5)
                
                job_url = job.get('url', '')
                current_status = job.get('job_status', 'available')
                is_filtered = job.get('llm_filtered') == True
                
                with col1:
                    if job_url:
                        st.link_button("🔗 View Job", job_url, use_container_width=True)
                
                with col2:
                    if current_status != 'applied':
                        if st.button("📝 Apply", key=f"apply_{job_id}_{idx}", use_container_width=True):
                            self._apply_for_job(job)
                    else:
                        st.success("✅ Applied")
                
                with col3:
                    # Only show ignore button for non-filtered jobs
                    if not is_filtered and current_status != 'ignored':
                        if st.button("🙈 Ignore", key=f"ignore_{job_id}_{idx}", use_container_width=True):
                            self._ignore_job(job)
                    elif is_filtered:
                        st.info("🚫 Filtered")
                    else:
                        st.success("🙈 Ignored")
                
                with col4:
                    if st.button("🔄 Enhance", key=f"enhance_{job_id}_{idx}", use_container_width=True):
                        self._enhance_job_with_llm(job, idx)
                
                with col5:
                    if st.button("📋 Full Details", key=f"details_{job_id}_{idx}", use_container_width=True):
                        self._show_full_job_details(job)
                
                st.divider()
    
    def _generate_job_snippet(self, job: pd.Series) -> str:
        """Generate enhanced job snippet using LLM."""
        if not self.ollama_client or not self.ollama_client.available:
            return ""
        
        try:
            title = job.get('title', '')
            company = job.get('company', '')
            salary = job.get('salary', '')
            description = str(job.get('description', ''))[:1500]
            
            if not description or len(description.strip()) < 50:
                return ""
            
            system_prompt = """You are an expert job analyst. Your task is to extract key job responsibilities and requirements from a job posting. 
            Respond with ONLY a concise snippet (max 150 characters), no additional text.
            The snippet MUST be in the same language as the provided job description."""
            
            prompt = f"""
            Extract the 2-3 most important responsibilities or requirements from this job posting.
            Keep it under 150 characters and focus on technical skills, key duties, or unique aspects.
            
            Job Title: {title}
            Company: {company}
            Salary: {salary if salary else "Not specified"}
            Description: {description}
            
            Provide only the snippet, nothing else:
            """
            
            response = self.ollama_client.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=100,
                temperature=0.1
            )
            
            if response:
                snippet = response.strip().replace('"', '').replace('\n', ' ')
                return snippet[:150] + "..." if len(snippet) > 150 else snippet
            
        except Exception as e:
            self.logger.error(f"Error generating job snippet: {e}")
        
        return ""
    
    def _apply_for_job(self, job: pd.Series):
        """Add job to applications."""
        try:
            existing_query = "SELECT id FROM job_applications WHERE url = %s"
            existing = self.db_manager.execute_query(existing_query, (job.get('url'),), fetch='one')
            
            if existing:
                st.warning("📋 Already applied to this job!")
                return
            
            insert_query = """
                INSERT INTO job_applications (
                    job_listing_id, position_title, company, location, salary, url, source,
                    added_date, status, notes
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            params = (
                job.get('id'), job.get('title', ''), job.get('company', ''),
                job.get('location', ''), job.get('salary', ''), job.get('url', ''),
                job.get('source', ''), datetime.now(), 'saved',
                f"Added from Job Browser - Quality: {job.get('llm_quality_score', 'N/A')}/10"
            )
            
            self.db_manager.execute_query(insert_query, params)
            st.success("✅ Job added to applications!")
            st.rerun()
            
        except Exception as e:
            self.logger.error(f"Error applying for job: {e}")
            st.error(f"Error applying for job: {e}")
    
    def _ignore_job(self, job: pd.Series):
        """Add job to ignored list."""
        try:
            # Don't allow ignoring filtered jobs - they should stay in filtered status
            if job.get('llm_filtered') == True:
                st.warning("🚫 Cannot ignore filtered jobs. Filtered jobs should remain in the '🚫 Filtered Only' view for review.")
                return
            
            existing_query = "SELECT id FROM ignored_jobs WHERE job_listing_id = %s"
            existing = self.db_manager.execute_query(existing_query, (job.get('id'),), fetch='one')
            
            if existing:
                st.warning("👁️ Job already ignored!")
                return
            
            insert_query = """
                INSERT INTO ignored_jobs (
                    job_listing_id, reason, ignored_at
                ) VALUES (%s, %s, %s)
            """
            
            params = (
                job.get('id'), 
                f"Ignored from Job Browser - Quality: {job.get('llm_quality_score', 'N/A')}/10",
                datetime.now()
            )
            
            self.db_manager.execute_query(insert_query, params)
            st.success("🙈 Job added to ignored list!")
            st.rerun()
            
        except Exception as e:
            self.logger.error(f"Error ignoring job: {e}")
            st.error(f"Error ignoring job: {e}")
    

    

    
    def _enhance_job_with_llm(self, job: pd.Series, idx: int):
        """Enhance job with additional LLM analysis."""
        if not self.ollama_client or not self.ollama_client.available:
            st.warning("🤖 LLM not available for enhancement")
            return
        
        with st.spinner("🤖 Enhancing job with AI analysis..."):
            try:
                if not job.get('job_snippet'):
                    snippet = self._generate_job_snippet(job)
                    if snippet:
                        update_query = "UPDATE job_listings SET job_snippet = %s WHERE id = %s"
                        self.db_manager.execute_query(update_query, (snippet, job.get('id')))
                        st.success("✨ Job snippet enhanced!")
                        st.rerun()
                
                insights = self._generate_job_insights(job)
                if insights:
                    st.success("🔍 Additional insights generated!")
                    with st.expander("🤖 AI Job Insights", expanded=True):
                        st.markdown(insights)
                
            except Exception as e:
                self.logger.error(f"Error enhancing job: {e}")
                st.error(f"Error enhancing job: {e}")
    
    def _generate_job_insights(self, job: pd.Series) -> str:
        """Generate additional job insights using LLM."""
        try:
            title = job.get('title', '')
            company = job.get('company', '')
            salary = job.get('salary', '')
            description = str(job.get('description', ''))[:2000]
            
            system_prompt = """You are a career advisor. Provide helpful insights about job opportunities.
            Be concise and practical."""
            
            prompt = f"""
            Analyze this job posting and provide brief insights on:
            1. Key skills required
            2. Career growth potential  
            3. Company type/industry
            4. Application tips
            5. Salary considerations (if salary info is available)
            
            Job Title: {title}
            Company: {company}
            Salary: {salary if salary else "Not specified"}
            Description: {description}
            
            Provide 3-4 bullet points, keep it concise:
            """
            
            response = self.ollama_client.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=300,
                temperature=0.3
            )
            
            return response if response else ""
            
        except Exception as e:
            self.logger.error(f"Error generating insights: {e}")
            return "" 

    def _bulk_ignore_jobs(self, df: pd.DataFrame, selected_job_ids: set):
        """Bulk ignore selected jobs."""
        try:
            selected_jobs = df[df['id'].isin(selected_job_ids)]
            
            if selected_jobs.empty:
                st.warning("No valid jobs selected for ignoring.")
                return
            
            # Check for already ignored jobs
            already_ignored = selected_jobs[selected_jobs['job_status'] == 'ignored']
            to_ignore = selected_jobs[selected_jobs['job_status'] != 'ignored']
            
            # Filter out filtered jobs from bulk ignore
            filtered_jobs = to_ignore[to_ignore['llm_filtered'] == True]
            non_filtered_jobs = to_ignore[to_ignore['llm_filtered'] != True]
            
            if filtered_jobs.empty and non_filtered_jobs.empty:
                st.warning("No jobs to ignore.")
                return
            
            if not filtered_jobs.empty:
                st.warning(f"🚫 Skipped {len(filtered_jobs)} filtered jobs. Filtered jobs should remain in '🚫 Filtered Only' view for review.")
            
            if not already_ignored.empty:
                st.warning(f"⚠️ {len(already_ignored)} jobs are already ignored.")
            
            if not non_filtered_jobs.empty:
                # Check for existing ignored jobs to avoid duplicates
                existing_ignored_query = "SELECT job_listing_id FROM ignored_jobs WHERE job_listing_id IN %s"
                existing_job_ids = tuple(non_filtered_jobs['id'].tolist())
                
                existing_results = self.db_manager.execute_query(existing_ignored_query, (existing_job_ids,), fetch='all')
                existing_ignored_ids = {row[0] for row in existing_results} if existing_results else set()
                
                # Filter out jobs that are already ignored
                jobs_to_ignore = non_filtered_jobs[~non_filtered_jobs['id'].isin(existing_ignored_ids)]
                
                if not jobs_to_ignore.empty:
                    # Bulk insert ignored jobs
                    insert_query = """
                        INSERT INTO ignored_jobs (
                            job_listing_id, reason, ignored_at
                        ) VALUES (%s, %s, %s)
                    """
                    
                    params_list = []
                    for _, job in jobs_to_ignore.iterrows():
                        params_list.append((
                            job.get('id'), 
                            f"Bulk ignored from Job Browser - Quality: {job.get('llm_quality_score', 'N/A')}/10",
                            datetime.now()
                        ))
                    
                    # Execute bulk insert
                    for params in params_list:
                        self.db_manager.execute_query(insert_query, params)
                    
                    st.success(f"🙈 Successfully ignored {len(jobs_to_ignore)} jobs!")
                else:
                    st.info("All selected jobs are already ignored.")
                
                if existing_ignored_ids:
                    st.info(f"⚠️ {len(existing_ignored_ids)} jobs were already ignored and skipped.")
                
                # Clear selection
                st.session_state.selected_jobs.clear()
                st.rerun()
            
        except Exception as e:
            self.logger.error(f"Error bulk ignoring jobs: {e}")
            st.error(f"Error bulk ignoring jobs: {e}")
    
    def _bulk_fetch_job_details(self, df: pd.DataFrame, selected_job_ids: set):
        """Bulk fetch job details for selected jobs."""
        try:
            selected_jobs = df[df['id'].isin(selected_job_ids)]
            
            if selected_jobs.empty:
                st.warning("No valid jobs selected for fetching details.")
                return
            
            st.info(f"🔄 Fetching job details for {len(selected_jobs)} selected jobs...")
            
            # Import the job details cache service
            from services.job_details_cache import job_details_cache
            
            fetched_count = 0
            failed_count = 0
            
            # Create a progress bar
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for idx, (_, job) in enumerate(selected_jobs.iterrows()):
                job_url = job.get('url', '')
                if not job_url:
                    failed_count += 1
                    continue
                
                # Update progress
                progress = (idx + 1) / len(selected_jobs)
                progress_bar.progress(progress)
                status_text.text(f"Fetching details for job {idx + 1}/{len(selected_jobs)}: {job.get('title', 'Unknown')[:50]}...")
                
                try:
                    # First try to get from cache
                    details = job_details_cache.get_job_details_with_retry(
                        job_url,
                        force_refresh=False,  # Don't force refresh for bulk operations
                        max_retries=2,
                        retry_delay=0.5
                    )
                    
                    if details:
                        fetched_count += 1
                    else:
                        # If not in cache, try to fetch using the appropriate scraper
                        details = self._fetch_job_details_with_scraper(job_url, job.get('source', ''))
                        if details:
                            fetched_count += 1
                        else:
                            failed_count += 1
                        
                except Exception as e:
                    self.logger.error(f"Error fetching details for {job_url}: {e}")
                    failed_count += 1
            
            # Clear progress indicators
            progress_bar.empty()
            status_text.empty()
            
            # Show results
            if fetched_count > 0:
                st.success(f"✅ Successfully fetched details for {fetched_count} jobs!")
            if failed_count > 0:
                st.warning(f"⚠️ Failed to fetch details for {failed_count} jobs.")
            
            # Clear selection and refresh
            st.session_state.selected_jobs.clear()
            st.rerun()
            
        except Exception as e:
            self.logger.error(f"Error bulk fetching job details: {e}")
            st.error(f"Error bulk fetching job details: {e}")

    def _bulk_apply_jobs(self, df: pd.DataFrame, selected_job_ids: set):
        """Bulk apply to selected jobs."""
        try:
            selected_jobs = df[df['id'].isin(selected_job_ids)]
            
            if selected_jobs.empty:
                st.warning("No valid jobs selected for applying.")
                return
            
            # Check for already applied jobs
            already_applied = selected_jobs[selected_jobs['job_status'] == 'applied']
            to_apply = selected_jobs[selected_jobs['job_status'] != 'applied']
            
            if already_applied.empty and to_apply.empty:
                st.warning("No jobs to apply to.")
                return
            
            if not already_applied.empty:
                st.warning(f"⚠️ {len(already_applied)} jobs are already applied to.")
            
            if not to_apply.empty:
                # Bulk insert job applications
                insert_query = """
                    INSERT INTO job_applications (
                        job_listing_id, position_title, company, location, salary, url, source,
                        added_date, status, notes
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (url) DO NOTHING
                """
                
                params_list = []
                for _, job in to_apply.iterrows():
                    params_list.append((
                        job.get('id'), job.get('title', ''), job.get('company', ''),
                        job.get('location', ''), job.get('salary', ''), job.get('url', ''),
                        job.get('source', ''), datetime.now(), 'saved',
                        f"Bulk applied from Job Browser - Quality: {job.get('llm_quality_score', 'N/A')}/10"
                    ))
                
                # Execute bulk insert
                for params in params_list:
                    self.db_manager.execute_query(insert_query, params)
                
                st.success(f"📝 Successfully applied to {len(to_apply)} jobs!")
                
                # Clear selection
                st.session_state.selected_jobs.clear()
                st.rerun()
            
        except Exception as e:
            self.logger.error(f"Error bulk applying to jobs: {e}")
            st.error(f"Error bulk applying to jobs: {e}") 

    def _test_location_filter(self):
        """Test the current location filter against the database."""
        current_location_filter = st.session_state.get('job_browser_filters', {}).get('location', 'All Locations')
        current_source_filter = st.session_state.get('job_browser_filters', {}).get('source', 'All Sources')
        
        if current_location_filter == "All Locations":
            st.warning("Please select a specific location to test.")
            return

        try:
            # Test location filter alone
            location_query = "SELECT COUNT(*) FROM job_listings WHERE LOWER(location) LIKE LOWER(%s)"
            location_param = f"%{current_location_filter}%"
            location_result = self.db_manager.execute_query(location_query, (location_param,), fetch='one')
            location_count = location_result[0] if location_result else 0
            
            st.success(f"**Testing location filter:** '{current_location_filter}'")
            st.write(f"**Jobs matching location '{current_location_filter}':** {location_count}")
            
            # Test combined filter if source is also selected
            if current_source_filter != "All Sources":
                combined_query = "SELECT COUNT(*) FROM job_listings WHERE source = %s AND LOWER(location) LIKE LOWER(%s)"
                combined_result = self.db_manager.execute_query(combined_query, (current_source_filter, location_param), fetch='one')
                combined_count = combined_result[0] if combined_result else 0
                
                st.write(f"**Jobs matching both source '{current_source_filter}' AND location '{current_location_filter}':** {combined_count}")
            
            # Show sample jobs for this location
            if location_count > 0:
                sample_query = """
                    SELECT title, company, location, source
                    FROM job_listings 
                    WHERE LOWER(location) LIKE LOWER(%s) 
                    LIMIT 5
                """
                sample_result = self.db_manager.execute_query(sample_query, (location_param,), fetch='all')
                if sample_result:
                    st.write("**Sample jobs for this location:**")
                    for job in sample_result:
                        st.write(f"- {job[0]} at {job[1]} ({job[2]}) - Source: {job[3]}")
            
        except Exception as e:
            st.error(f"**Error testing filter:** {e}")
    
    def _show_full_job_details(self, job: pd.Series):
        """Display full cached job details in an expandable section."""
        try:
            job_url = job.get('url', '')
            if not job_url:
                st.warning("No URL available for this job.")
                return
            
            # Get cached job details
            cached_details = self.db_manager.get_cached_job_details(job_url)
            
            if not cached_details:
                st.warning("No cached details available for this job. The job details may not have been fetched yet.")
                return
            
            # Create an expandable section for full details
            with st.expander("📋 Full Job Details", expanded=True):
                st.markdown("### 📄 Complete Job Information")
                
                # Basic Information
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**🏢 Company Information**")
                    st.write(f"**Company:** {cached_details.get('company', 'N/A')}")
                    st.write(f"**Location:** {cached_details.get('location', 'N/A')}")
                    st.write(f"**Salary:** {cached_details.get('salary', 'N/A')}")
                    
                    # Cache Information
                    st.markdown("**💾 Cache Information**")
                    scraped_date = cached_details.get('scraped_date')
                    if scraped_date:
                        if isinstance(scraped_date, str):
                            scraped_date = datetime.fromisoformat(scraped_date.replace('Z', '+00:00'))
                        st.write(f"**Scraped:** {scraped_date.strftime('%Y-%m-%d %H:%M:%S')}")
                    
                    last_accessed = cached_details.get('last_accessed')
                    if last_accessed:
                        if isinstance(last_accessed, str):
                            last_accessed = datetime.fromisoformat(last_accessed.replace('Z', '+00:00'))
                        st.write(f"**Last Accessed:** {last_accessed.strftime('%Y-%m-%d %H:%M:%S')}")
                    
                    access_count = cached_details.get('access_count', 0)
                    st.write(f"**Access Count:** {access_count}")
                    
                    is_valid = cached_details.get('is_valid', True)
                    st.write(f"**Cache Valid:** {'✅ Yes' if is_valid else '❌ No'}")
                
                with col2:
                    st.markdown("**🔗 URLs**")
                    st.write(f"**External URL:** {cached_details.get('external_url', 'N/A')}")
                    st.write(f"**Application URL:** {cached_details.get('application_url', 'N/A')}")
                    
                    # Error Information (if any)
                    error_message = cached_details.get('error_message')
                    if error_message:
                        st.markdown("**⚠️ Error Information**")
                        st.error(f"**Error:** {error_message}")
                
                # Full Description
                st.markdown("### 📝 Full Description")
                description = cached_details.get('description', '')
                if description:
                    st.markdown(description)
                else:
                    st.info("No description available.")
                
                # Requirements Section
                requirements = cached_details.get('requirements', '')
                if requirements:
                    st.markdown("### 📋 Requirements")
                    st.markdown(requirements)
                
                # Benefits Section
                benefits = cached_details.get('benefits', '')
                if benefits:
                    st.markdown("### 🎁 Benefits")
                    st.markdown(benefits)
                
                # Contact Information
                contact_info = cached_details.get('contact_info', '')
                if contact_info:
                    st.markdown("### 📞 Contact Information")
                    st.markdown(contact_info)
                
                # Cache Metadata (if available)
                cache_metadata = cached_details.get('cache_metadata')
                if cache_metadata:
                    st.markdown("### 🔧 Cache Metadata")
                    if isinstance(cache_metadata, str):
                        try:
                            metadata_dict = json.loads(cache_metadata)
                            for key, value in metadata_dict.items():
                                st.write(f"**{key}:** {value}")
                        except:
                            st.code(cache_metadata)
                    else:
                        for key, value in cache_metadata.items():
                            st.write(f"**{key}:** {value}")
                
                # Raw HTML Content (collapsed by default)
                html_content = cached_details.get('html_content', '')
                if html_content:
                    with st.expander("🔍 Raw HTML Content", expanded=False):
                        st.code(html_content[:5000] + "..." if len(html_content) > 5000 else html_content)
                
                # Action buttons for the full details
                st.markdown("### 🎯 Actions")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button("🔄 Refresh Cache", key=f"refresh_cache_{job.get('id')}"):
                        self._refresh_job_cache(job_url)
                
                with col2:
                    if st.button("🗑️ Clear Cache", key=f"clear_cache_{job.get('id')}"):
                        self._clear_job_cache(job_url)
                
                with col3:
                    if st.button("📊 Cache Stats", key=f"cache_stats_{job.get('id')}"):
                        self._show_cache_stats(job_url)
        
        except Exception as e:
            st.error(f"Error displaying full job details: {e}")
            self.logger.error(f"Error in _show_full_job_details: {e}")
    
    def _refresh_job_cache(self, job_url: str):
        """Refresh the cached job details by fetching fresh data."""
        try:
            st.info("🔄 Refreshing job cache...")
            
            # Import the job details cache service
            from services.job_details_cache import job_details_cache
            
            # Force refresh by fetching with scraper
            fresh_details = self._fetch_job_details_with_scraper(job_url, '')
            
            if fresh_details:
                st.success("✅ Job cache refreshed successfully!")
                st.rerun()
            else:
                st.error("❌ Failed to refresh job cache. The job may no longer be available.")
        
        except Exception as e:
            st.error(f"Error refreshing job cache: {e}")
            self.logger.error(f"Error in _refresh_job_cache: {e}")
    
    def _clear_job_cache(self, job_url: str):
        """Clear the cached job details."""
        try:
            st.info("🗑️ Clearing job cache...")
            
            # Invalidate the cache
            from services.job_details_cache import job_details_cache
            success = job_details_cache.invalidate_job_details(job_url, "Manually cleared by user")
            
            if success:
                st.success("✅ Job cache cleared successfully!")
                st.rerun()
            else:
                st.error("❌ Failed to clear job cache.")
        
        except Exception as e:
            st.error(f"Error clearing job cache: {e}")
            self.logger.error(f"Error in _clear_job_cache: {e}")
    
    def _show_cache_stats(self, job_url: str):
        """Show cache statistics for the job."""
        try:
            from services.job_details_cache import job_details_cache
            
            stats = job_details_cache.get_cache_performance_metrics()
            
            st.markdown("### 📊 Cache Performance Statistics")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Cache Hits", stats.get('performance', {}).get('cache_hits', 0))
                st.metric("Cache Misses", stats.get('performance', {}).get('cache_misses', 0))
            
            with col2:
                hit_rate = stats.get('performance', {}).get('hit_rate', 0)
                st.metric("Hit Rate", f"{hit_rate:.1%}")
                error_rate = stats.get('performance', {}).get('error_rate', 0)
                st.metric("Error Rate", f"{error_rate:.1%}")
            
            with col3:
                efficiency = stats.get('performance', {}).get('efficiency_score', 0)
                st.metric("Efficiency Score", f"{efficiency:.1f}")
                total_cached = stats.get('storage', {}).get('total_cached', 0)
                st.metric("Total Cached", total_cached)
        
        except Exception as e:
            st.error(f"Error showing cache stats: {e}")
            self.logger.error(f"Error in _show_cache_stats: {e}")

    def _jump_to_job(self, df: pd.DataFrame, search_term: str):
        """Jump to the page containing a specific job."""
        try:
            # Search for jobs matching the term (case-insensitive)
            matching_jobs = df[
                df['title'].str.contains(search_term, case=False, na=False) |
                df['company'].str.contains(search_term, case=False, na=False)
            ]
            
            if matching_jobs.empty:
                st.warning(f"🔍 No jobs found matching '{search_term}'")
                return
            
            # Get the first matching job
            first_match = matching_jobs.iloc[0]
            job_index = df.index.get_loc(first_match.name)
            
            # Calculate which page this job is on
            jobs_per_page = st.session_state.get('jobs_per_page', 10)
            target_page = (job_index // jobs_per_page) + 1
            
            # Jump to that page
            st.session_state.current_page = target_page
            
            # Show success message
            st.success(f"🔍 Found '{first_match['title']}' at {first_match['company']} - Jumping to page {target_page}")
            
            # Rerun to show the page
            st.rerun()
            
        except Exception as e:
            st.error(f"Error jumping to job: {e}")
            self.logger.error(f"Error in _jump_to_job: {e}")

    def _fetch_job_details_with_scraper(self, job_url: str, source: str) -> Optional[Dict[str, Any]]:
        """Fetch job details using the appropriate scraper based on the source."""
        try:
            # Import scrapers
            from scrapers.stellenanzeigen_scraper import StellenanzeigenScraper
            from scrapers.stepstone_scraper import StepstoneScraper
            from scrapers.indeed_scraper import IndeedScraper
            from scrapers.linkedin_scraper import LinkedInScraper
            from scrapers.xing_scraper import XingScraper
            from scrapers.jobrapido_scraper import JobrapidoScraper
            from scrapers.meinestadt_scraper import MeinestadtScraper
            
            # Determine which scraper to use based on source
            scraper = None
            if 'stellenanzeigen' in source.lower():
                scraper = StellenanzeigenScraper()
            elif 'stepstone' in source.lower():
                scraper = StepstoneScraper()
            elif 'indeed' in source.lower():
                scraper = IndeedScraper()
            elif 'linkedin' in source.lower():
                scraper = LinkedInScraper()
            elif 'xing' in source.lower():
                scraper = XingScraper()
            elif 'jobrapido' in source.lower():
                scraper = JobrapidoScraper()
            elif 'meinestadt' in source.lower():
                scraper = MeinestadtScraper()
            else:
                # Try to determine from URL if source is not clear
                if 'stellenanzeigen.de' in job_url.lower():
                    scraper = StellenanzeigenScraper()
                elif 'stepstone.de' in job_url.lower():
                    scraper = StepstoneScraper()
                elif 'indeed.com' in job_url.lower():
                    scraper = IndeedScraper()
                elif 'linkedin.com' in job_url.lower():
                    scraper = LinkedInScraper()
                elif 'xing.com' in job_url.lower():
                    scraper = XingScraper()
                elif 'jobrapido.com' in job_url.lower():
                    scraper = JobrapidoScraper()
                elif 'meinestadt.de' in job_url.lower():
                    scraper = MeinestadtScraper()
            
            if scraper:
                self.logger.info(f"Fetching job details using {scraper.__class__.__name__} for: {job_url}")
                details = scraper.fetch_job_details(job_url)
                if details:
                    # Cache the fetched details
                    from services.job_details_cache import job_details_cache
                    job_details_cache.cache_job_details(job_url, details, is_valid=True)
                    return details
                else:
                    self.logger.warning(f"Failed to fetch job details using {scraper.__class__.__name__} for: {job_url}")
            else:
                self.logger.warning(f"No suitable scraper found for source '{source}' and URL: {job_url}")
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error fetching job details with scraper for {job_url}: {e}")
            return None

    def _test_combined_filters(self):
        """Test the combined source and location filters."""
        current_source_filter = st.session_state.get('job_browser_filters', {}).get('source', 'All Sources')
        current_location_filter = st.session_state.get('job_browser_filters', {}).get('location', 'All Locations')
        
        if current_source_filter == "All Sources" and current_location_filter == "All Locations":
            st.warning("Please select both a source and location to test combined filters.")
            return
        
        try:
            test_query = "SELECT COUNT(*) FROM job_listings WHERE 1=1"
            test_params = []
            
            if current_source_filter != "All Sources":
                test_query += " AND source = %s"
                test_params.append(current_source_filter)
            
            if current_location_filter != "All Locations":
                test_query += " AND LOWER(location) LIKE LOWER(%s)"
                test_params.append(f"%{current_location_filter}%")
            
            test_result = self.db_manager.execute_query(test_query, test_params, fetch='one')
            match_count = test_result[0] if test_result else 0
            
            st.success(f"**Testing combined filters:**")
            st.write(f"**Source:** {current_source_filter}")
            st.write(f"**Location:** {current_location_filter}")
            st.write(f"**Jobs matching combined filters:** {match_count}")
            
            # Show sample jobs
            if match_count > 0:
                sample_query = f"""
                    SELECT title, company, location, source
                    FROM job_listings 
                    WHERE 1=1
                """
                sample_params = []
                
                if current_source_filter != "All Sources":
                    sample_query += " AND source = %s"
                    sample_params.append(current_source_filter)
                
                if current_location_filter != "All Locations":
                    sample_query += " AND LOWER(location) LIKE LOWER(%s)"
                    sample_params.append(f"%{current_location_filter}%")
                
                sample_query += " LIMIT 5"
                
                sample_result = self.db_manager.execute_query(sample_query, sample_params, fetch='all')
                if sample_result:
                    st.write("**Sample jobs matching combined filters:**")
                    for job in sample_result:
                        st.write(f"- {job[0]} at {job[1]} ({job[2]}) - Source: {job[3]}")
            
        except Exception as e:
            st.error(f"**Error testing combined filters:** {e}") 