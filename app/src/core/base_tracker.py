"""
Base class for Job Tracker functionality
"""

import os
import time
from datetime import datetime, timedelta
import streamlit as st

from src.database.database_manager import get_db_manager
from enhanced_job_processor import EnhancedJobProcessor
from scrapers import JobScraperOrchestrator
from config_manager import ConfigManager
from ollama_job_analyzer import OllamaJobAnalyzer

class BaseJobTracker:
    def __init__(self):
        # Initialize database manager in session state
        if 'db_manager' not in st.session_state:
            st.session_state.db_manager = get_db_manager()
        self.db_manager = st.session_state.db_manager
        
        # Initialize config manager in session state
        if 'config_manager' not in st.session_state:
            st.session_state.config_manager = ConfigManager()
        self.config_manager = st.session_state.config_manager
        
        # Get LLM configuration
        ollama_config = self.config_manager.get_setting("llm", {})
        ollama_host = os.getenv("OLLAMA_HOST", ollama_config.get("ollama_host", "http://localhost:11434"))
        ollama_model = os.getenv("OLLAMA_MODEL", ollama_config.get("ollama_model", "llama3:8b"))
        
        # Get FlareSolverr URL from config
        flaresolverr_config = self.config_manager.get_setting("flaresolverr", {})
        flaresolverr_url = os.getenv("FLARESOLVERR_URL", flaresolverr_config.get("url", "http://flaresolverr:8191/v1"))
        
        # Initialize Ollama analyzer in session state if enabled
        if 'ollama_analyzer' not in st.session_state:
            if ollama_config.get("enable_ollama", True):
                try:
                    st.session_state.ollama_analyzer = OllamaJobAnalyzer(ollama_host, ollama_model)
                except Exception as e:
                    st.warning(f"⚠️ Failed to initialize Ollama analyzer: {e}")
                    st.session_state.ollama_analyzer = None
            else:
                st.session_state.ollama_analyzer = None
        self.ollama_analyzer = st.session_state.ollama_analyzer
        
        # Initialize job processing components in session state
        if 'enhanced_processor' not in st.session_state:
            st.session_state.enhanced_processor = EnhancedJobProcessor(ollama_host, ollama_model)
        self.enhanced_processor = st.session_state.enhanced_processor
        
        if 'job_scraper_orchestrator' not in st.session_state:
            st.session_state.job_scraper_orchestrator = JobScraperOrchestrator(
                debug=True,  # Enable debug logging
                use_flaresolverr=True
            )
        self.job_scraper_orchestrator = st.session_state.job_scraper_orchestrator
        
    def show_real_time_progress(self, message, progress=None):
        """Show real-time progress with optional progress bar"""
        if progress is not None:
            st.progress(progress, text=message)
        else:
            st.info(message)
            time.sleep(0.1)  # Small delay for visual feedback 