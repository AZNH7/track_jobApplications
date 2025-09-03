"""
Data management view for Job Tracker
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json
import zipfile
import io
import base64

from core.base_tracker import BaseJobTracker
from utils.ui_components import UIComponents

class DataManagementView(BaseJobTracker):
    def __init__(self):
        super().__init__()
        self.ui = UIComponents()
    
    def export_data(self, data_type: str) -> pd.DataFrame:
        """Export data based on type"""
        try:
            if data_type == "jobs":
                query = "SELECT * FROM job_listings"
            elif data_type == "applications":
                query = "SELECT * FROM applications"
            elif data_type == "offers":
                query = "SELECT * FROM job_offers"
            elif data_type == "filtered":
                query = "SELECT * FROM filtered_jobs"
            else:
                return pd.DataFrame()
                
            result = self.db_manager.execute_query(query)
            return pd.DataFrame(result)
        except Exception as e:
            st.error(f"Error exporting {data_type}: {str(e)}")
            return pd.DataFrame()
    
    def import_data(self, data_type: str, df: pd.DataFrame) -> bool:
        """Import data from DataFrame"""
        try:
            if data_type == "jobs":
                table = "job_listings"
            elif data_type == "applications":
                table = "applications"
            elif data_type == "offers":
                table = "job_offers"
            elif data_type == "filtered":
                table = "filtered_jobs"
            else:
                return False
                
            # Convert DataFrame to list of dictionaries
            records = df.to_dict('records')
            
            # Generate placeholders for SQL query
            columns = df.columns
            placeholders = [f"%({col})s" for col in columns]
            
            # Create INSERT query
            query = f"""
            INSERT INTO {table} ({', '.join(columns)})
            VALUES ({', '.join(placeholders)})
            ON CONFLICT (id) DO UPDATE
            SET {', '.join(f"{col} = EXCLUDED.{col}" for col in columns)}
            """
            
            # Execute for each record
            for record in records:
                self.db_manager.execute_query(query, record)
                
            return True
        except Exception as e:
            st.error(f"Error importing {data_type}: {str(e)}")
            return False
    
    def cleanup_old_data(self, data_type: str, days: int) -> bool:
        """Clean up old data"""
        try:
            if data_type == "jobs":
                query = """
                DELETE FROM job_listings
                WHERE scraped_date < NOW() - INTERVAL '%(days)s days'
                """
            elif data_type == "filtered":
                query = """
                DELETE FROM filtered_jobs
                WHERE created_at < NOW() - INTERVAL '%(days)s days'
                """
            else:
                return False
                
            self.db_manager.execute_query(query, {'days': days})
            return True
        except Exception as e:
            st.error(f"Error cleaning up {data_type}: {str(e)}")
            return False
    
    def clear_all_data(self) -> dict:
        """Clear all data from the database"""
        try:
            result = {
                'job_listings': 0,
                'applications': 0,
                'offers': 0,
                'emails': 0,
                'filtered_jobs': 0,
                'ignored_jobs': 0
            }
            
            # Clear job offers first (they reference applications)
            offers_query = "DELETE FROM job_offers"
            self.db_manager.execute_query(offers_query)
            
            # Clear applications (they reference job_listings)
            applications_query = "DELETE FROM applications"
            self.db_manager.execute_query(applications_query)
            
            # Clear job applications (they reference job_listings)
            job_applications_query = "DELETE FROM job_applications"
            self.db_manager.execute_query(job_applications_query)
            
            # Clear filtered jobs
            filtered_query = "DELETE FROM filtered_jobs"
            self.db_manager.execute_query(filtered_query)
            
            # Clear ignored jobs (they reference job_listings)
            ignored_query = "DELETE FROM ignored_jobs"
            self.db_manager.execute_query(ignored_query)
            
            # Clear all job listings
            listings_query = "DELETE FROM job_listings"
            self.db_manager.execute_query(listings_query)
            
            # Get counts for reporting
            try:
                # Count what was deleted (these will be 0 now, but we can get the counts from before)
                result['job_listings'] = self.db_manager.execute_query("SELECT COUNT(*) FROM job_listings", fetch='one')[0] if self.db_manager.execute_query("SELECT COUNT(*) FROM job_listings", fetch='one') else 0
                result['applications'] = self.db_manager.execute_query("SELECT COUNT(*) FROM applications", fetch='one')[0] if self.db_manager.execute_query("SELECT COUNT(*) FROM applications", fetch='one') else 0
                result['offers'] = self.db_manager.execute_query("SELECT COUNT(*) FROM job_offers", fetch='one')[0] if self.db_manager.execute_query("SELECT COUNT(*) FROM job_offers", fetch='one') else 0
                result['emails'] = 0  # Email analysis table removed
            except:
                pass
            
            return result
            
        except Exception as e:
            st.error(f"Error clearing all data: {str(e)}")
            raise
    
    def get_data_stats(self) -> dict:
        """Get statistics about the data"""
        try:
            stats = {}
            
            # Jobs stats
            jobs_query = """
            SELECT 
                COUNT(*) as total,
                MIN(scraped_date) as oldest,
                MAX(scraped_date) as newest,
                COUNT(DISTINCT company) as companies
            FROM job_listings
            """
            jobs_stats = self.db_manager.execute_query(jobs_query, fetch='one')
            stats['jobs'] = {
                'total': jobs_stats[0] if jobs_stats else 0,
                'oldest': jobs_stats[1] if jobs_stats else None,
                'newest': jobs_stats[2] if jobs_stats else None,
                'companies': jobs_stats[3] if jobs_stats else 0
            }
            
            # Applications stats
            apps_query = """
            SELECT 
                COUNT(*) as total,
                COUNT(DISTINCT company) as companies,
                COUNT(*) FILTER (WHERE status = 'applied') as applied,
                COUNT(*) FILTER (WHERE status = 'interview') as interviews
            FROM applications
            """
            apps_stats = self.db_manager.execute_query(apps_query, fetch='one')
            stats['applications'] = {
                'total': apps_stats[0] if apps_stats else 0,
                'companies': apps_stats[1] if apps_stats else 0,
                'applied': apps_stats[2] if apps_stats else 0,
                'interviews': apps_stats[3] if apps_stats else 0
            }
            
            # Offers stats
            offers_query = """
            SELECT 
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE status = 'active') as active,
                COUNT(*) FILTER (WHERE status = 'accepted') as accepted
            FROM job_offers
            """
            offers_stats = self.db_manager.execute_query(offers_query, fetch='one')
            stats['offers'] = {
                'total': offers_stats[0] if offers_stats else 0,
                'active': offers_stats[1] if offers_stats else 0,
                'accepted': offers_stats[2] if offers_stats else 0
            }
            
            return stats
        except Exception as e:
            st.error(f"Error getting stats: {str(e)}")
            return {}
    
    def get_download_link(self, df: pd.DataFrame, filename: str) -> str:
        """Generate download link for DataFrame"""
        csv = df.to_csv(index=False)
        b64 = base64.b64encode(csv.encode()).decode()
        href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">Download {filename}</a>'
        return href
    
    def show_data_stats(self, stats: dict):
        """Show data statistics"""
        st.markdown("### 📊 Data Statistics")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if 'jobs' in stats:
                self.ui.show_metric_card(
                    "Total Jobs",
                    stats['jobs']['total'],
                    f"From {stats['jobs']['companies']} companies"
                )
        
        with col2:
            if 'applications' in stats:
                self.ui.show_metric_card(
                    "Applications",
                    stats['applications']['total'],
                    f"{stats['applications']['interviews']} interviews"
                )
        
        with col3:
            if 'offers' in stats:
                self.ui.show_metric_card(
                    "Job Offers",
                    stats['offers']['total'],
                    f"{stats['offers']['active']} active"
                )
    
    def show(self):
        """Show data management interface"""
        self.ui.show_header("Data Management", "🗄️")
        
        # Get data statistics
        stats = self.get_data_stats()
        self.show_data_stats(stats)
        
        # Export section
        self.ui.show_export_import_section("Export Data")
        
        col1, col2 = st.columns(2)
        
        with col1:
            export_type = st.selectbox(
                "Select Data to Export",
                ["Jobs", "Applications", "Offers", "Filtered Jobs"]
            )
        
        with col2:
            if st.button("Export"):
                data_type = export_type.lower().replace(" ", "_")
                df = self.export_data(data_type.replace("_jobs", ""))
                
                if not df.empty:
                    st.markdown(
                        self.get_download_link(df, f"{data_type}_{datetime.now().strftime('%Y%m%d')}.csv"),
                        unsafe_allow_html=True
                    )
                    st.success(f"Successfully exported {len(df)} records!")
        
        # Import section
        st.markdown("### 📥 Import Data")
        
        import_type = st.selectbox(
            "Select Data to Import",
            ["Jobs", "Applications", "Offers", "Filtered Jobs"]
        )
        
        uploaded_file = st.file_uploader("Choose CSV file", type="csv")
        
        if uploaded_file is not None:
            try:
                df = pd.read_csv(uploaded_file)
                if st.button("Import Data"):
                    data_type = import_type.lower().replace(" ", "_")
                    if self.import_data(data_type.replace("_jobs", ""), df):
                        st.success(f"Successfully imported {len(df)} records!")
            except Exception as e:
                st.error(f"Error reading file: {str(e)}")
        
        # Cleanup section
        st.markdown("### 🧹 Data Cleanup")
        
        col1, col2 = st.columns(2)
        
        with col1:
            cleanup_type = st.selectbox(
                "Select Data to Clean",
                ["Old Jobs", "Old Filtered Jobs"]
            )
        
        with col2:
            days = st.number_input("Days to Keep", min_value=1, value=30)
        
        if st.button("Clean Up"):
            data_type = cleanup_type.lower().replace("old ", "")
            if self.cleanup_old_data(data_type.replace("_jobs", ""), days):
                st.success(f"Successfully cleaned up {cleanup_type}!") 
        
        # Email Data Cleanup
        st.markdown("### 📧 Email Data Management")
        st.warning("⚠️ Warning: This will permanently delete all email analysis data!")
        
        if 'confirm_email_clear' not in st.session_state:
            st.session_state.confirm_email_clear = False
            
        if not st.session_state.confirm_email_clear:
            if st.button("Clear All Email Data", type="secondary"):
                st.session_state.confirm_email_clear = True
        else:
            st.error("⚠️ Are you sure? This action cannot be undone!")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Yes, Clear Email Data", type="primary"):
                    try:
                        deleted_count = self.db_manager.clear_email_data()
                        st.success(f"Successfully cleared {deleted_count} email records!")
                        st.session_state.confirm_email_clear = False
                    except Exception as e:
                        st.error(f"Error clearing email data: {str(e)}")
            with col2:
                if st.button("No, Cancel", type="secondary"):
                    st.session_state.confirm_email_clear = False
        
        # Complete Data Cleanup
        st.markdown("### 🗑️ Complete Data Cleanup")
        st.error("🚨 **DANGER ZONE** - This will permanently delete ALL data from the database!")
        
        if 'confirm_complete_clear' not in st.session_state:
            st.session_state.confirm_complete_clear = False
            
        if not st.session_state.confirm_complete_clear:
            if st.button("🗑️ Clean Out Everything", type="secondary", help="This will delete ALL jobs, applications, offers, and email data"):
                st.session_state.confirm_complete_clear = True
        else:
            st.error("🚨 **FINAL WARNING**: This will permanently delete ALL data from the database. This action cannot be undone!")
            st.info("This will clear:")
            st.markdown("""
            - All job listings
            - All job applications  
            - All job offers
            - All email analysis data
            - All filtered jobs
            - All ignored jobs
            - All application data
            """)
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🚨 YES, DELETE EVERYTHING", type="primary"):
                    try:
                        result = self.clear_all_data()
                        st.success(f"Successfully cleared all data!")
                        st.info(f"Deleted: {result['job_listings']} job listings, {result['applications']} applications, {result['offers']} offers, {result['emails']} email records")
                        st.session_state.confirm_complete_clear = False
                        st.rerun()  # Refresh the page to show updated stats
                    except Exception as e:
                        st.error(f"Error clearing all data: {str(e)}")
            with col2:
                if st.button("❌ Cancel", type="secondary"):
                    st.session_state.confirm_complete_clear = False 