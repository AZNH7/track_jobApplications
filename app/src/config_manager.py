#!/usr/bin/env python3
"""
Configuration Manager for Job Tracker Application
Handles persistent settings and preferences.
"""

import json
import os
from typing import Dict, Any, Optional
import shutil


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
                    content = f.read()
                    self._config_data = json.loads(content)
                    self._replace_env_placeholders(self._config_data)
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
    
    
            "scraping": {
                "use_flaresolverr": True,
                "flaresolverr_url": "http://localhost:8191/v1",
                "default_headless": True,
                "default_timeout": 60
            },
            "filters": {
                "language_filter_enabled": True,
                "location_filter_enabled": True,
                "preferred_languages": ["en", "de"]
            },
            "llm": {
                "enable_ollama": True,
                "ollama_host": "http://localhost:11434",
                "ollama_model": "gpt-oss:latest",
                "ollama_timeout": 120,
                "ollama_max_retries": 3,
                "enable_job_analysis": True,
        
                "enable_application_insights": True
            },
            "database": {
                "host": "localhost",
                "port": 5432,
                "database": "jobtracker",
                "user": "user",
                "password": "password",
                "connection_timeout": 30
            },
            "flaresolverr": {
                "url": "http://flaresolverr:8191/v1",
                "timeout": 60
            }
        }
        self._replace_env_placeholders(self._config_data)
        return self._config_data

    def _replace_env_placeholders(self, config: Dict[str, Any]) -> None:
        """Recursively replace environment variable placeholders."""
        for key, value in config.items():
            if isinstance(value, dict):
                self._replace_env_placeholders(value)
            elif isinstance(value, str) and value.startswith('${') and value.endswith('}'):
                env_var = value[2:-1]
                config[key] = os.getenv(env_var, '')
    
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
        d = self._config_data
        for k in keys[:-1]:
            d = d.setdefault(k, {})
        d[keys[-1]] = value

    def save_config(self) -> bool:
        """Saves the current configuration data to the config file."""
        try:
            # Create a backup.
            if os.path.exists(self.config_file):
                shutil.copy(self.config_file, self.config_file + '.bak')
            
            with open(self.config_file, 'w') as f:
                json.dump(self._config_data, f, indent=2)
            
            print(f"✅ Configuration saved to {self.config_file}")
            return True
        except Exception as e:
            print(f"❌ Error saving configuration: {e}")
            # Restore from backup if something went wrong.
            if os.path.exists(self.config_file + '.bak'):
                shutil.move(self.config_file + '.bak', self.config_file)
            return False
    
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

    def reload_config(self) -> bool:
        """Reload configuration from file, clearing cached data."""
        try:
            # Clear cached data
            self._config_data = {}
            # Reload from file
            self._load_config()
            return True
        except Exception as e:
            print(f"❌ Error reloading config: {e}")
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