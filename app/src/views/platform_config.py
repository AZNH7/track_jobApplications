"""
Platform configuration view for Job Tracker
"""

import streamlit as st
import json
import time

from core.base_tracker import BaseJobTracker
from utils.ui_components import UIComponents
from utils.platform_utils import PlatformUtils

class PlatformConfigView(BaseJobTracker):
    def __init__(self):
        super().__init__()
        self.ui = UIComponents()
        self.platform_utils = PlatformUtils(self.db_manager)
    
    def show(self):
        """Show platform configuration interface"""
        self.ui.show_header("Platform Configuration", "⚙️")
        
        # Platform settings
        st.markdown("### 🔧 Platform Settings")
        
        # Load current config
        job_search_config = self.config_manager.get_job_search_config()
        
        with st.form("platform_config_form"):
            # Indeed settings
            st.subheader("Indeed Settings")
            indeed_enabled = st.checkbox(
                "Enable Indeed",
                value=self.config_manager.is_indeed_enabled()
            )
            
            if indeed_enabled:
                indeed_country = st.selectbox(
                    "Indeed Country",
                    ["de"],  # Only Germany is supported
                    index=0
                )
                
                indeed_language = st.selectbox(
                    "Indeed Language",
                    ["en", "de"],
                    index=1 if job_search_config.get("preferred_language") == "de" else 0
                )
            
            # LinkedIn settings
            st.subheader("LinkedIn Settings")
            linkedin_enabled = st.checkbox(
                "Enable LinkedIn",
                value=job_search_config.get("enable_linkedin", True)
            )
            
            if linkedin_enabled:
                linkedin_region = st.selectbox(
                    "LinkedIn Region",
                    ["de"],  # Only Germany is supported
                    index=0
                )
            

            
            # Save button
            submitted = st.form_submit_button("Save Configuration")
            
            if submitted:
                # Update config
                self.config_manager.set("job_search.enable_indeed", indeed_enabled)
                self.config_manager.set("job_search.indeed_country", "de")  # Always Germany
                self.config_manager.set("job_search.preferred_language", indeed_language if indeed_enabled else "de")
                self.config_manager.set("job_search.enable_linkedin", linkedin_enabled)

                
                st.success("Configuration saved successfully!")
                time.sleep(1)  # Give user time to see the success message
                st.rerun()  # Refresh the page to show updated settings
        
        # Platform testing
        st.markdown("### 🧪 Platform Testing")
        
        with st.form("platform_test_form"):
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                keywords = st.text_input(
                    "Test Keywords",
                    placeholder="e.g. Software Engineer Python"
                )
            
            with col2:
                location = st.text_input(
                    "Test Location",
                    placeholder="e.g. Berlin, Germany"
                )
            
            with col3:
                max_pages = st.number_input(
                    "Max Pages",
                    min_value=1,
                    value=1
                )
            
            english_only = st.checkbox("English Jobs Only")
            
            test_submitted = st.form_submit_button("Run Platform Tests")
            
            if test_submitted:
                if not keywords or not location:
                    st.error("Please enter both keywords and location")
                    return
                
                self.run_platform_tests(keywords, location, max_pages, english_only)
    
    def run_platform_tests(self, keywords, location, max_pages, english_only):
        """Run tests for all enabled platforms"""
        try:
            # Get enabled platforms
            job_search_config = self.config_manager.get_job_search_config()
            platforms = []
            
            if job_search_config.get("enable_indeed", True):
                platforms.append("indeed")
            if job_search_config.get("enable_linkedin", True):
                platforms.append("linkedin")

            
            if not platforms:
                st.warning("No platforms enabled for testing")
                return
            
            # Initialize progress
            progress_text = st.empty()
            progress_bar = st.progress(0)
            
            total_steps = len(platforms)
            current_step = 0
            
            results = {}
            
            for platform in platforms:
                progress_text.text(f"Testing {platform.title()}...")
                
                try:
                    # Run test
                    platform_results = self.platform_utils.test_platform(
                        platform,
                        keywords,
                        location,
                        max_pages,
                        english_only
                    )
                    
                    results[platform] = platform_results
                    
                except Exception as e:
                    results[platform] = {
                        "success": False,
                        "error": str(e),
                        "jobs_found": 0
                    }
                
                current_step += 1
                progress_bar.progress(current_step / total_steps)
                time.sleep(1)  # Small delay for visual feedback
            
            progress_text.text("Testing completed!")
            progress_bar.progress(1.0)
            
            # Show results
            st.markdown("### 📊 Test Results")
            
            for platform, result in results.items():
                with st.expander(f"{platform.title()} Results"):
                    if result.get("success"):
                        st.success(f"Successfully found {result.get('jobs_found', 0)} jobs")
                        if result.get("sample_jobs"):
                            st.markdown("#### Sample Jobs")
                            for job in result["sample_jobs"][:3]:
                                self.ui.show_job_card(job)
                    else:
                        st.error(f"Test failed: {result.get('error', 'Unknown error')}")
            
        except Exception as e:
            st.error(f"Error during platform testing: {str(e)}") 