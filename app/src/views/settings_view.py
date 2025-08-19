#!/usr/bin/env python3
"""
Settings View for the Job Tracker Application
"""
import streamlit as st
from .base_view import BaseView
from config_manager import get_config_manager

class SettingsView(BaseView):
    """A view to manage application settings."""

    def __init__(self):
        """Initialize the settings view with config manager."""
        super().__init__()
        self.config_manager = get_config_manager()

    def show(self):
        """Show the settings view."""
        self.display()

    def display(self):
        """Render the settings page."""
        st.header("⚙️ Application Settings")

        # Create tabs for different settings categories
        tab1, tab2, tab3 = st.tabs(["Job Search", "Platforms", "LLM & Database"])

        with tab1:
            self._display_job_search_settings()
        
        with tab2:
            self._display_platform_settings()

        with tab3:
            self._display_llm_and_db_settings()

        if st.button("Save Settings"):
            self._save_settings()

    def _save_settings(self):
        """Save the settings to the config file."""
        # Job Search Settings
        # Removed predefined job titles functionality

        self.config_manager.set_value('job_search.default_max_pages', st.session_state.default_max_pages)
        self.config_manager.set_value('job_search.enable_indeed', st.session_state.enable_indeed)
        self.config_manager.set_value('job_search.enable_linkedin', st.session_state.enable_linkedin)
        self.config_manager.set_value('job_search.enable_stepstone', st.session_state.enable_stepstone)
        self.config_manager.set_value('job_search.enable_xing', st.session_state.enable_xing)

        # Platform Settings
        self.config_manager.set_value('scraping.flaresolverr_url', st.session_state.flaresolverr_url)
        for platform in ["indeed", "linkedin", "stepstone", "xing"]:
            self.config_manager.set_value(f'scraping.platform_settings.{platform}.use_flaresolverr', st.session_state[f"{platform}_use_flaresolverr"])

        # LLM and Database Settings
        self.config_manager.set_value('llm.enable_ollama', st.session_state.enable_ollama)
        self.config_manager.set_value('llm.ollama_host', st.session_state.ollama_host)
        self.config_manager.set_value('llm.ollama_model', st.session_state.ollama_model)
        self.config_manager.set_value('llm.ollama_timeout', st.session_state.ollama_timeout)
        self.config_manager.set_value('database.host', st.session_state.db_host)
        self.config_manager.set_value('database.user', st.session_state.db_user)
        self.config_manager.set_value('database.password', st.session_state.db_password)

        if self.config_manager.save_config():
            st.success("Settings saved successfully!")
            st.experimental_rerun()
        else:
            st.error("Failed to save settings.")

    def _display_job_search_settings(self):
        """Display job search settings."""
        st.subheader("Job Search Configuration")
        
        config = self.config_manager.get_setting('job_search', {})
        
        st.info("💡 Job titles are now managed through saved search parameters in the Enhanced Job Search view.")
        
        st.slider(
            "Default Max Pages to Scrape",
            min_value=1,
            max_value=10,
            value=config.get('default_max_pages', 2),
            key="default_max_pages"
        )

        st.checkbox("Enable Indeed", value=config.get('enable_indeed', True), key="enable_indeed")
        st.checkbox("Enable LinkedIn", value=config.get('enable_linkedin', True), key="enable_linkedin")
        st.checkbox("Enable StepStone", value=config.get('enable_stepstone', True), key="enable_stepstone")
        st.checkbox("Enable Xing", value=config.get('enable_xing', True), key="enable_xing")

    def _display_platform_settings(self):
        """Display platform-specific settings."""
        st.subheader("Platform Configuration")
        
        scraping_config = self.config_manager.get_setting('scraping', {})
        st.text_input("FlareSolverr URL", value=scraping_config.get('flaresolverr_url', ''), key="flaresolverr_url")

        platform_settings = scraping_config.get('platform_settings', {})
        for platform in ["indeed", "linkedin", "stepstone", "xing"]:
            st.checkbox(f"Use FlareSolverr for {platform.title()}", 
                        value=platform_settings.get(platform, {}).get('use_flaresolverr', False),
                        key=f"{platform}_use_flaresolverr")

    def _display_llm_and_db_settings(self):
        """Display LLM and Database settings."""
        st.subheader("LLM and Database Configuration")

        llm_config = self.config_manager.get_setting('llm', {})
        st.checkbox("Enable Ollama", value=llm_config.get('enable_ollama', True), key="enable_ollama")
        st.text_input("Ollama Host", value=llm_config.get('ollama_host', ''), key="ollama_host")
        st.text_input("Ollama Model", value=llm_config.get('ollama_model', ''), key="ollama_model")
        st.number_input("Ollama Timeout", value=llm_config.get('ollama_timeout', 300), key="ollama_timeout")

        db_config = self.config_manager.get_setting('database', {})
        st.text_input("Database Host", value=db_config.get('host', ''), key="db_host")
        st.text_input("Database User", value=db_config.get('user', ''), key="db_user")
        st.text_input("Database Password", value=db_config.get('password', ''), key="db_password", type="password")