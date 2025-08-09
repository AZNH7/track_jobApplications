"""
Browser Automation with Selenium

Handles browser automation tasks for scraping, with a focus on allowing
manual user intervention for CAPTCHAs.
"""

import time
import logging
from typing import Dict, Any
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium_stealth import stealth

class BrowserAutomation:
    """
    Manages a Selenium browser instance for web scraping, optimized for
    manual CAPTCHA solving by running in a visible (non-headless) mode.
    """
    
    def __init__(self, debug: bool = False, headless: bool = False):
        """
        Initializes the browser automation manager.
        
        Args:
            debug: Enable debug logging.
            headless: If True, runs the browser in headless mode. 
                      Set to False to allow for manual CAPTCHA solving.
        """
        self.debug = debug
        self.headless = headless
        self.driver = self._initialize_driver()
        
    def _initialize_driver(self) -> webdriver.Chrome:
        """
        Sets up and initializes the Chrome WebDriver with stealth options.
        
        Returns:
            A configured Selenium WebDriver instance.
        """
        logging.info("🔧 Initializing Chrome WebDriver...")
        
        options = Options()
        if self.headless:
            options.add_argument("--headless")
        
        # Standard browser-like arguments
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--start-maximized")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            
            # Apply stealth settings to make the browser less detectable
            stealth(driver,
                    languages=["en-US", "en"],
                    vendor="Google Inc.",
                    platform="Win32",
                    webgl_vendor="Intel Inc.",
                    renderer="Intel Iris OpenGL Engine",
                    fix_hairline=True,
                    )
            
            logging.info("✅ WebDriver initialized successfully.")
            return driver
        except Exception as e:
            logging.error(f"❌ Failed to initialize WebDriver: {e}")
            raise

    def get_page_with_browser(self, url: str, max_wait: int = 60) -> Dict[str, Any]:
        """
        Navigates to a URL and waits for the user to solve a CAPTCHA if necessary.
        
        Args:
            url: The URL to navigate to.
            max_wait: The maximum time in seconds to wait for the user 
                      to solve the CAPTCHA and for the page to load.
                      
        Returns:
            A dictionary containing the page source and status.
        """
        try:
            logging.info(f"Navigating to {url}...")
            self.driver.get(url)
            
            # Inform the user to solve the CAPTCHA
            print("\n" + "="*50)
            print("❗ ACTION REQUIRED: Please solve the CAPTCHA in the browser window.")
            print(f"   You have {max_wait} seconds to solve it.")
            print("="*50 + "\n")
            
            # Wait for the user to solve the CAPTCHA
            # A simple time.sleep is used here, but more advanced solutions
            # could wait for a specific element to appear after the CAPTCHA is solved.
            time.sleep(max_wait)
            
            logging.info("✅ Continuing after wait time.")
            return {
                "status": "ok",
                "solution": {
                    "response": self.driver.page_source
                }
            }
        except Exception as e:
            logging.error(f"❌ An error occurred during browser navigation: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
            
    def close(self):
        """Closes the browser and quits the driver."""
        if self.driver:
            logging.info("Closing WebDriver.")
            self.driver.quit() 