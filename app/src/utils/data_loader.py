"""
Data loading utilities for Job Tracker
"""

import pandas as pd
from datetime import datetime, timedelta
import streamlit as st

class DataLoader:
    def __init__(self, db_manager):
        self.db_manager = db_manager
    
    def load_job_data(self):
        """Load job data from database"""
        try:
            # Use the new modular structure to get job listings
            job_listings = self.db_manager.job_listings.get_all_jobs()
            if job_listings:
                return pd.DataFrame(job_listings)
            else:
                return pd.DataFrame()
        except Exception as e:
            st.error(f"Error loading job data: {e}")
            return pd.DataFrame()

    def load_applications_data(self):
        """Load job applications data"""
        try:
            # Use the new modular structure to get applications
            applications = self.db_manager.job_applications.get_all_applications()
            if applications:
                return pd.DataFrame(applications)
            else:
                return pd.DataFrame()
        except Exception as e:
            st.error(f"Error loading applications: {str(e)}")
            return pd.DataFrame()
    
    def get_data_date_range(self):
        """Get date range for available data"""
        try:
            # Get job listings date range
            job_query = """
                SELECT 
                    MIN(scraped_date) as earliest,
                    MAX(scraped_date) as latest
                FROM job_listings
            """
            job_range = self.db_manager.execute_query(job_query, fetch='one')
            
            return {
                'job_range': {
                    'earliest': job_range[0] if job_range else None,
                    'latest': job_range[1] if job_range else None
                }
            }
            
        except Exception as e:
            st.error(f"Error getting date range: {e}")
            return None 