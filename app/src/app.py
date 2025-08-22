#!/usr/bin/env python3
"""
Main Streamlit Application Entry Point
"""

import streamlit as st
import pandas as pd
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Add src directory to path
# sys.path.append('/app/src') # This is no longer necessary

from utils.ui_components import UIComponents
from utils.data_loader import DataLoader
from components.quick_insights_widget import QuickInsightsWidget
from components.persistent_search_results import PersistentSearchResults
from core.session_state import SessionStateManager
from src.database.database_manager import get_db_manager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Main application entry point"""
    try:
        # Configure Streamlit page
        st.set_page_config(
            page_title="Job Tracker",
            page_icon="💼",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        
        # Initialize session state
        SessionStateManager.initialize_session_state()
        
        # Initialize UI components
        ui = UIComponents()
        ui.apply_custom_css()
        
        # Initialize data loader and insights widget
        from core.base_tracker import BaseJobTracker
        base_tracker = BaseJobTracker()
        data_loader = DataLoader(base_tracker.db_manager)
        insights_widget = QuickInsightsWidget(base_tracker.db_manager)
        
        # Load data for insights
        try:
            df = data_loader.load_job_data()
            applications_df = data_loader.load_applications_data()
        except Exception as e:
            df = pd.DataFrame()
            applications_df = pd.DataFrame()
            logging.warning(f"Could not load data for insights: {e}")
        
        # Sidebar navigation
        st.sidebar.title("Navigation")
        
        # Combined navigation using a single selectbox
        page = st.sidebar.radio(
            "Go to",
            [
                "🏠 Main Dashboard",
                "🔍 Job Search",
                "📊 Job Browser",
                "📝 Job Offers",
                "📄 Applications",
                "🛠️ Data Management",
                "🔧 Platform Config",
                "⚙️ Settings"
            ]
        )
        
        # Show quick insights in sidebar only on main dashboard
        if page == "🏠 Main Dashboard":
            insights_widget.show_sidebar_widget(df, applications_df)
        
        # Cache status indicator
        if 'cache_status' in st.session_state:
            ui.show_cache_status(st.session_state.cache_status)
        
        # Show persistent search results in sidebar
        PersistentSearchResults.show_sidebar_summary()
        
        # Route to appropriate page
        if page == "🏠 Main Dashboard":
            from views.main_dashboard import MainDashboardView
            dashboard = MainDashboardView()
            dashboard.show()
            
        elif page == "🔍 Job Search":
            from views.enhanced_job_search import EnhancedJobSearchView
            search_view = EnhancedJobSearchView()
            search_view.show()
            
        elif page == "📊 Job Browser":
            from views.job_browser import JobBrowserView
            browser = JobBrowserView()
            browser.show()
            
        elif page == "📝 Job Offers":
            from views.job_offers import JobOffersView
            offers_view = JobOffersView()
            offers_view.show()
            
        elif page == "📄 Applications":
            from views.applications import ApplicationsView
            applications_view = ApplicationsView()
            applications_view.show()
            
        elif page == "🛠️ Data Management":
            from views.data_management import DataManagementView
            data_view = DataManagementView()
            data_view.show()
            
        elif page == "🔧 Platform Config":
            from views.platform_config import PlatformConfigView
            config_view = PlatformConfigView()
            config_view.show()
            
        elif page == "⚙️ Settings":
            from views.settings_view import SettingsView
            settings_view = SettingsView()
            settings_view.show()
            
    except Exception as e:
        logger.error(f"Error in main application: {e}")
        st.error(f"Application error: {e}")

if __name__ == "__main__":
    main() 