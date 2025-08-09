#!/usr/bin/env python3
"""
Configuration Manager for Job Tracker Application
Handles persistent settings and preferences.
"""

import json
import os
from typing import Dict, Any, Optional


class ConfigManager:
    """Manages application configuration settings."""
    
    _instance = None
    _config_data = {}  # Initialize as empty dict instead of None
    
    def __init__(self, config_file: str = "job_tracker_config.json"):
        """Initialize instance attributes."""
        self.config_file = config_file
        if not self._config_data:
            self._load_config()
    
    def __new__(cls, config_file: str = "job_tracker_config.json"):
        """Implement singleton pattern to prevent multiple instances."""
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
        return cls._instance
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default config."""
        if self._config_data:
            return self._config_data
            
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    self._config_data = json.load(f)
                    return self._config_data
        except Exception as e:
            print(f"⚠️ Error loading config: {e}")
        
        # Set default configuration
        self._config_data = {
            "job_search": {
                "enable_indeed": True,
                "indeed_country": "de",
                "enable_linkedin": True,
                "enable_alternative_sources": True,
                "default_max_pages": 3
            },
            "job_titles": [
                "System Administrator",
                "IT System Administrator",
                "Systems Engineer",
                "IT Engineer",
                "Technical Support Engineer",
                "IT Support Specialist",
                "IT Operations Engineer",
                "System Integration Engineer",
                "IT Integration",
                "Technical Operations Engineer",
                "IT Infrastructure Engineer",
                "Senior IT system",
                "Senior IT engineer",
                "Senior IT Admin",
                "Senior system admin",
                "Senior system administrator",
                "IT system",
                "IT engineer",
                "IT Admin"
            ],
            "default_job_titles": [
                "System Administrator",
                "IT System Administrator",
                "Systems Engineer",
                "IT Engineer",
                "Technical Support Engineer",
                "IT Support Specialist",
                "IT Operations Engineer",
                "System Integration Engineer",
                "IT Integration",
                "Technical Operations Engineer",
                "IT Infrastructure Engineer",
                "Senior IT system",
                "Senior IT engineer",
                "Senior IT Admin",
                "Senior system admin",
                "Senior system administrator",
                "IT system",
                "IT engineer",
                "IT Admin"
            ],
            "scraping": {
                "use_flaresolverr": True,
                "flaresolverr_url": "http://flaresolverr-balancer:8190/v1",
                "default_headless": True,
                "default_timeout": 300
            },
            "filters": {
                "language_filter_enabled": True,
                "location_filter_enabled": True,
                "preferred_languages": ["en", "de"]
            },
            "llm": {
                "enable_ollama": True,
                "ollama_host": "http://localhost:11434",
                "ollama_model": "llama3:8b",
                "ollama_timeout": 300,
                "ollama_max_retries": 3,
                "enable_job_analysis": True,
                "enable_cv_scoring": True,
                "enable_application_insights": True
            },
            "database": {
                "host": "localhost",
                "port": 5432,
                "database": "jobtracker",
                "user": "jobtracker",
                "password": "jobtracker",
                "connection_timeout": 30
            },
            "flaresolverr": {
                "url": "http://flaresolverr:8191/v1",
                "timeout": 60
            }
        }
        return self._config_data
    
    def get_value(self, key: str, default: Any = None) -> Any:
        """Get a configuration setting using dot notation."""
        try:
            keys = key.split('.')
            value = self._config_data
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set_value(self, key: str, value: Any) -> None:
        """Set a configuration setting using dot notation."""
        keys = key.split('.')
        config = self._config_data
        for k in keys[:-1]:
            config = config.setdefault(k, {})
        config[keys[-1]] = value
    
    def save_config(self) -> None:
        """Save configuration to file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self._config_data, f, indent=2)
        except Exception as e:
            print(f"⚠️ Error saving config: {e}")
    
    def get_setting(self, section: str, default: Any = None) -> Any:
        """Get a configuration section."""
        return self._config_data.get(section, default)
    
    def get_job_search_config(self) -> Dict[str, Any]:
        """Get all job search related configuration."""
        return self._config_data.get("job_search", {})
    
    def get_scraping_config(self) -> Dict[str, Any]:
        """Get all scraping related configuration."""
        return self._config_data.get("scraping", {})
    
    def is_indeed_enabled(self) -> bool:
        """Check if Indeed search is enabled."""
        return self.get_setting("job_search.enable_indeed", True)
    
    def set_indeed_enabled(self, enabled: bool) -> bool:
        """Enable or disable Indeed search."""
        self.set_value("job_search.enable_indeed", enabled)
        return True
    
    def get_indeed_country(self) -> str:
        """Get the configured Indeed country (always Germany)."""
        return "de"
    
    def set_indeed_country(self, country: str) -> bool:
        """Set the Indeed country (only Germany is supported)."""
        if country != "de":
            print(f"⚠️ Warning: Only Germany (de) is supported. Country '{country}' ignored.")
            return False
        self.set_value("job_search.indeed_country", "de")
        return True
    
    def reset_to_defaults(self) -> bool:
        """Reset configuration to default values."""
        self._config_data = self._load_config.__func__(self)  # Call the method directly to get defaults
        self.save_config()
        return True
    
    def export_config(self, export_file: str) -> bool:
        """Export current configuration to a file."""
        try:
            with open(export_file, 'w') as f:
                json.dump(self._config_data, f, indent=2)
            return True
        except Exception as e:
            print(f"❌ Error exporting config: {e}")
            return False
    
    def import_config(self, import_file: str) -> bool:
        """Import configuration from a file."""
        try:
            with open(import_file, 'r') as f:
                imported_config = json.load(f)
            
            self._config_data = imported_config
            self.save_config()
            return True
            
        except Exception as e:
            print(f"❌ Error importing config: {e}")
            return False


# Global configuration manager instance
_config_manager = None

def get_config_manager() -> ConfigManager:
    """Get the global configuration manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


if __name__ == "__main__":
    # Test the configuration manager
    config = ConfigManager()
    
    print("🧪 Testing Configuration Manager")
    print("=" * 40)
    
    # Test getting values
    print(f"Indeed enabled: {config.is_indeed_enabled()}")
    print(f"Indeed country: {config.get_indeed_country()}")
    print(f"Max pages: {config.get_value('job_search.default_max_pages', 2)}")
    
    # Test setting values
    config.set_indeed_enabled(False)
    config.set_indeed_country("com")
    print(f"After changes - Indeed enabled: {config.is_indeed_enabled()}")
    print(f"After changes - Indeed country: {config.get_indeed_country()}")
    
    # Reset and test again
    config.reset_to_defaults()
    print(f"After reset - Indeed enabled: {config.is_indeed_enabled()}")
    print(f"After reset - Indeed country: {config.get_indeed_country()}")
    
    print("✅ Configuration manager test completed!") 