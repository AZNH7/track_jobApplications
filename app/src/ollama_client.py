#!/usr/bin/env python3
"""
Centralized Ollama Client with robust error handling and retry logic
"""

import os
import time
import logging
import requests
import socket
from typing import Dict, Optional, Any
from tenacity import retry, stop_after_attempt, wait_exponential

class OllamaClient:
    """
    Centralized client for Ollama API interactions with robust error handling
    """
    
    def __init__(self):
        # Get configuration from environment variables
        # Get configuration
        from config_manager import get_config_manager
        config_manager = get_config_manager()
        self.host = os.getenv('OLLAMA_HOST', config_manager.get_value('llm.ollama_host', 'http://localhost:11434')).rstrip('/')
        self.timeout = int(os.getenv('OLLAMA_TIMEOUT', config_manager.get_value('llm.ollama_timeout', 300)))
        self.max_retries = int(os.getenv('OLLAMA_MAX_RETRIES', config_manager.get_value('llm.ollama_max_retries', 3)))
        self.retry_delay = int(os.getenv('OLLAMA_RETRY_DELAY', 5))
        self.batch_size = int(os.getenv('OLLAMA_BATCH_SIZE', 8))
        # Get configuration
        from config_manager import get_config_manager
        config_manager = get_config_manager()
        self.max_tokens = int(os.getenv('OLLAMA_MAX_TOKENS', config_manager.get_value('llm.ollama_max_tokens', 1000)))
        self.temperature = float(os.getenv('OLLAMA_TEMPERATURE', 0.1))
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        
        # Try to resolve host.docker.internal if it's in the host
        if 'host.docker.internal' in self.host:
            try:
                host_ip = socket.gethostbyname('host.docker.internal')
                self.logger.info(f"Resolved host.docker.internal to {host_ip}")
                self.host = self.host.replace('host.docker.internal', host_ip)
            except socket.gaierror as e:
                self.logger.warning(f"Could not resolve host.docker.internal: {e}")
        
        # Test connection on initialization with retries
        self.available = False
        for i in range(self.max_retries):
            if self.test_connection():
                self.available = True
                break
            if i < self.max_retries - 1:  # Don't sleep on the last attempt
                time.sleep(self.retry_delay)
        
        if not self.available:
            self.logger.warning(
                f"Could not connect to Ollama at {self.host} after {self.max_retries} attempts. "
                "LLM features will be disabled."
            )
    
    def test_connection(self) -> bool:
        """Test connection to Ollama server"""
        try:
            response = requests.get(
                f"{self.host}/api/tags",
                timeout=10,
                headers={'Connection': 'close'}  # Prevent connection pooling issues
            )
            if response.status_code == 200:
                self.logger.info(f"Successfully connected to Ollama at {self.host}")
                return True
            else:
                self.logger.warning(
                    f"Ollama server returned status code {response.status_code}"
                )
                return False
        except requests.exceptions.ConnectionError as e:
            self.logger.warning(f"Connection error to Ollama server: {e}")
            return False
        except requests.exceptions.Timeout as e:
            self.logger.warning(f"Timeout connecting to Ollama server: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error testing Ollama connection: {e}")
            return False
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True
    )
    def _make_request(self, endpoint: str, payload: Optional[Dict] = None, method: str = 'POST') -> Optional[Dict]:
        """Make a request to Ollama API with retry logic"""
        try:
            url = f"{self.host}/api/{endpoint}"
            headers = {
                'Connection': 'close',  # Prevent connection pooling issues
                'Content-Type': 'application/json'
            }
            
            if method == 'GET':
                response = requests.get(url, timeout=self.timeout, headers=headers)
            else:
                response = requests.post(url, json=payload, timeout=self.timeout, headers=headers)
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.Timeout:
            self.logger.error(f"Request to {endpoint} timed out after {self.timeout}s")
            raise
        except requests.exceptions.ConnectionError as e:
            self.logger.error(f"Connection error to {endpoint}: {e}")
            raise
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request to {endpoint} failed: {e}")
            raise
    
    def generate(self, 
                prompt: str, 
                system_prompt: str = "", 
                max_tokens: Optional[int] = None,
                temperature: Optional[float] = None,
                model: str = None) -> Optional[str]:
        """
        Generate text using Ollama with fallback handling
        """
        if not self.available:
            self.logger.warning("Ollama is not available. Skipping generation.")
            return None
            
        try:
            # Get configuration for default model
            from config_manager import get_config_manager
            config_manager = get_config_manager()
            default_model = model or config_manager.get_value('llm.ollama_model', 'llama3:8b')
            
            payload = {
                "model": default_model,
                "prompt": prompt,
                "system": system_prompt,
                "stream": False,
                "options": {
                    "num_predict": max_tokens or self.max_tokens,
                    "temperature": temperature or self.temperature,
                    "top_p": 0.9,
                    "repeat_penalty": 1.1,
                    "batch_size": self.batch_size
                }
            }
            
            result = self._make_request("generate", payload)
            if result and 'response' in result:
                return result['response'].strip()
            else:
                self.logger.warning("No response in Ollama result")
                return None
            
        except Exception as e:
            self.logger.error(f"Error in generate(): {e}")
            return None
    
    def get_models(self) -> Optional[Dict]:
        """Get list of available models"""
        if not self.available:
            return None
            
        try:
            return self._make_request("tags", method='GET')
        except Exception as e:
            self.logger.error(f"Error getting models: {e}")
            return None
    
    def pull_model(self, model_name: str) -> bool:
        """Pull a model from Ollama"""
        if not self.available:
            return False
            
        try:
            payload = {"name": model_name}
            self._make_request("pull", payload)
            return True
        except Exception as e:
            self.logger.error(f"Error pulling model {model_name}: {e}")
            return False

# Create a singleton instance
ollama_client = OllamaClient()

def reinitialize_ollama_client():
    """Reinitialize the Ollama client with updated settings."""
    global ollama_client
    # Clear the singleton instance
    OllamaClient._instance = None
    # Create a new instance
    ollama_client = OllamaClient()
    return ollama_client
