"""Selenium-based base scraper with anti-detection measures."""
import time
import random
from typing import Optional, List
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

from .base_scraper import BaseJobScraper, JobPosting
from config import config
from utils import get_logger


class SeleniumJobScraper(BaseJobScraper):
    """
    Base scraper using Selenium with anti-detection measures.
    """
    
    def __init__(self, source_name: str):
        super().__init__(source_name)
        self.logger = get_logger(f"scraper.{source_name}")
        self.driver: Optional[webdriver.Chrome] = None
        self.wait: Optional[WebDriverWait] = None
        self._init_driver()
    
    def _init_driver(self):
        """Initialize Chrome driver with anti-detection settings."""
        chrome_options = Options()
        
        if config.scraping.headless:
            chrome_options.add_argument("--headless=new")
        
        # Anti-detection measures
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # User agent
        chrome_options.add_argument(
            f"--user-agent={config.scraping.user_agent}"
        )
        
        # Window size
        chrome_options.add_argument("--window-size=1920,1080")
        
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Execute CDP commands to prevent detection
            self.driver.execute_cdp_cmd(
                'Page.addScriptToEvaluateOnNewDocument',
                {
                    'source': '''
                        Object.defineProperty(navigator, 'webdriver', {
                            get: () => undefined
                        })
                    '''
                }
            )
            
            self.wait = WebDriverWait(
                self.driver, 
                config.scraping.timeout
            )
            
            self.logger.info("Chrome driver initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize driver: {e}")
            raise
    
    def _random_delay(self, min_seconds: float = None, max_seconds: float = None):
        """Add random delay to mimic human behavior."""
        min_delay = min_seconds or config.scraping.request_delay
        max_delay = max_seconds or min_delay * 2
        delay = random.uniform(min_delay, max_delay)
        time.sleep(delay)
    
    def _safe_find_element(self, by: By, value: str, timeout: int = None) -> Optional:
        """Safely find an element with timeout."""
        try:
            wait_time = timeout or config.scraping.timeout
            return WebDriverWait(self.driver, wait_time).until(
                EC.presence_of_element_located((by, value))
            )
        except TimeoutException:
            return None
    
    def _safe_find_elements(self, by: By, value: str) -> List:
        """Safely find multiple elements."""
        try:
            return self.driver.find_elements(by, value)
        except NoSuchElementException:
            return []
    
    def _scroll_page(self, scroll_pause: float = 1.0):
        """Scroll page to load lazy content."""
        last_height = self.driver.execute_script(
            "return document.body.scrollHeight"
        )
        
        while True:
            # Scroll down
            self.driver.execute_script(
                "window.scrollTo(0, document.body.scrollHeight);"
            )
            time.sleep(scroll_pause)
            
            # Calculate new scroll height
            new_height = self.driver.execute_script(
                "return document.body.scrollHeight"
            )
            
            if new_height == last_height:
                break
            
            last_height = new_height
    
    def get_page(self, url: str) -> bool:
        """
        Navigate to URL with error handling.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.driver.get(url)
            self._random_delay()
            return True
        except Exception as e:
            self.logger.error(f"Failed to load page {url}: {e}")
            return False
    
    def close(self):
        """Close the driver."""
        if self.driver:
            self.driver.quit()
            self.logger.info("Driver closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False
    
    # Abstract methods to be implemented by subclasses
    def search_jobs(
        self,
        query: str,
        location: Optional[str] = None,
        max_results: int = 10
    ) -> List[JobPosting]:
        """Search for jobs - implement in subclass."""
        raise NotImplementedError
    
    def get_job_details(self, job_id: str) -> Optional[JobPosting]:
        """Get job details - implement in subclass."""
        raise NotImplementedError
