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
            engine = self.db_manager.get_sqlalchemy_engine()
            return pd.read_sql_query("SELECT * FROM job_listings ORDER BY scraped_date DESC", engine)
        except Exception as e:
            st.error(f"Error loading job data: {e}")
            return pd.DataFrame()

    def load_applications_data(self):
        """Load job applications data"""
        try:
            return pd.DataFrame(self.db_manager.get_applications())
        except Exception as e:
            st.error(f"Error loading applications: {str(e)}")
            return pd.DataFrame()
    
    def get_data_date_range(self):
        """Get date range for available data"""
        try:
            # Get email date range
            email_query = """
                SELECT 
                    MIN(date) as earliest,
                    MAX(date) as latest
                FROM email_analysis
            """
            email_range = self.db_manager.execute_query(email_query, fetch='one')
            
            # Get job listings date range
            job_query = """
                SELECT 
                    MIN(scraped_date) as earliest,
                    MAX(scraped_date) as latest
                FROM job_listings
            """
            job_range = self.db_manager.execute_query(job_query, fetch='one')
            
            return {
                'email_range': {
                    'earliest': email_range[0] if email_range else None,
                    'latest': email_range[1] if email_range else None
                },
                'job_range': {
                    'earliest': job_range[0] if job_range else None,
                    'latest': job_range[1] if job_range else None
                }
            }
            
        except Exception as e:
            st.error(f"Error getting date range: {e}")
            return None 