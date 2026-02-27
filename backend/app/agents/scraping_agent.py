"""Job Scraping Agent."""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import asyncio
import structlog
from dataclasses import dataclass
import json
import re
import time
import random

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup

from app.extensions import db
from app.models.job import Job, Company
from app.agents.job_agent import get_job_agent

logger = structlog.get_logger()


@dataclass
class ScrapedJob:
    """Data class for scraped job data."""
    title: str
    company_name: str
    description: str
    location: Optional[str] = None
    is_remote: bool = False
    is_hybrid: bool = False
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_currency: str = "USD"
    employment_type: Optional[str] = None
    experience_level: Optional[str] = None
    source_url: Optional[str] = None
    source_platform: str = "unknown"
    external_id: Optional[str] = None
    posted_at: Optional[datetime] = None
    requirements: Optional[str] = None
    responsibilities: Optional[str] = None
    company_description: Optional[str] = None
    company_industry: Optional[str] = None
    company_website: Optional[str] = None


class JobScrapingAgent:
    """
    Job Scraping Agent responsible for:
    - Scraping jobs from multiple job boards using Selenium + BeautifulSoup
    - Normalizing job data
    - Deduplicating jobs
    - Processing and storing scraped jobs
    """

    def __init__(self):
        self.job_agent = get_job_agent()
        self.driver: Optional[webdriver.Chrome] = None

    def _get_driver(self, headless: bool = True) -> webdriver.Chrome:
        """Get or create Selenium WebDriver."""
        # Check if existing driver is still alive
        if self.driver is not None:
            try:
                # Test if driver is responsive by checking current URL
                self.driver.current_url
            except Exception:
                logger.warning("Existing WebDriver is unresponsive, creating new instance")
                self._close_driver()
        
        if self.driver is None:
            chrome_options = Options()
            
            if headless:
                # Run headless for production
                chrome_options.add_argument('--headless')
            
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            
            # Set user agent to avoid detection
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            # Additional options to avoid detection
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            if headless:
                # Disable images, CSS, and JavaScript to speed up loading (only for headless)
                chrome_prefs = {
                    "profile.managed_default_content_settings.images": 2,
                    "profile.default_content_setting_values.notifications": 2,
                    "profile.managed_default_content_settings.stylesheets": 2,
                    "profile.managed_default_content_settings.fonts": 2,
                }
                chrome_options.experimental_options["prefs"] = chrome_prefs
                
                # Additional performance optimizations
                chrome_options.add_argument('--disable-extensions')
                chrome_options.add_argument('--disable-javascript')
                chrome_options.add_argument('--blink-settings=imagesEnabled=false')
                chrome_options.add_argument('--disk-cache-size=0')
                chrome_options.add_argument('--media-cache-size=0')
            else:
                # For non-headless (Internshala), use realistic window size
                chrome_options.add_argument('--window-size=1920,1080')
                chrome_options.add_argument('--start-maximized')
            
            try:
                self.driver = webdriver.Chrome(options=chrome_options)
                
                # Execute CDP commands to avoid detection
                if not headless:
                    self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                        'source': '''
                            Object.defineProperty(navigator, 'webdriver', {
                                get: () => undefined
                            })
                        '''
                    })
                
                logger.info(f"Selenium WebDriver initialized (headless={headless})")
            except Exception as e:
                logger.error(f"Failed to initialize WebDriver: {e}")
                raise
        
        return self.driver

    def _close_driver(self):
        """Close the WebDriver."""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Selenium WebDriver closed")
            except Exception as e:
                logger.warning(f"Error closing WebDriver: {e}")
            finally:
                self.driver = None

    def _is_driver_alive(self) -> bool:
        """Check if the WebDriver is still responsive."""
        if self.driver is None:
            return False
        try:
            self.driver.current_url
            return True
        except Exception:
            return False

    def _random_delay(self, min_seconds: float = 0.5, max_seconds: float = 1.5):
        """Add random delay to avoid being blocked."""
        time.sleep(random.uniform(min_seconds, max_seconds))

    def scrape_linkedin_jobs(
        self,
        keywords: List[str],
        location: Optional[str] = None,
        max_results: int = 25
    ) -> List[ScrapedJob]:
        """
        Scrape jobs from LinkedIn using Selenium.
        
        Args:
            keywords: List of job keywords to search
            location: Location filter
            max_results: Maximum number of results
            
        Returns:
            List of scraped jobs
        """
        jobs = []
        
        for keyword in keywords:
            # Check driver health before each keyword
            if not self._is_driver_alive():
                logger.info("WebDriver not alive, reinitializing...")
                self._close_driver()
            
            driver = self._get_driver()
            
            try:
                # Build search URL
                search_url = f"https://www.linkedin.com/jobs/search?keywords={keyword.replace(' ', '%20')}"
                if location:
                    search_url += f"&location={location.replace(' ', '%20')}"
                
                logger.info(f"Scraping LinkedIn: {search_url}")
                driver.get(search_url)
                
                # Wait for job cards to load
                wait = WebDriverWait(driver, 10)
                wait.until(EC.presence_of_element_located((By.CLASS_NAME, "job-search-card")))
                
                self._random_delay(2, 4)
                
                # Scroll to load more jobs
                for _ in range(min(max_results // 10, 3)):
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    self._random_delay(1, 2)
                
                # Parse page with BeautifulSoup
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                job_cards = soup.find_all('div', class_='job-search-card')
                
                for card in job_cards[:max_results]:
                    job = self._parse_linkedin_job_card(card)
                    if job:
                        jobs.append(job)
                
                logger.info(f"Scraped {len(job_cards)} LinkedIn jobs for keyword '{keyword}'")
                
            except TimeoutException:
                logger.warning(f"Timeout scraping LinkedIn for '{keyword}'")
            except Exception as e:
                logger.error(f"Failed to scrape LinkedIn for '{keyword}': {e}")
                self._close_driver()
            
            self._random_delay(3, 5)  # Delay between keywords
        
        return jobs

    def _parse_linkedin_job_card(self, card) -> Optional[ScrapedJob]:
        """Parse a LinkedIn job card into ScrapedJob."""
        try:
            # Extract title
            title_elem = card.find('h3', class_='base-search-card__title')
            title = title_elem.text.strip() if title_elem else ""
            
            # Extract company
            company_elem = card.find('h4', class_='base-search-card__subtitle')
            company_name = company_elem.text.strip() if company_elem else "Unknown"
            
            # Extract location
            location_elem = card.find('span', class_='job-search-card__location')
            location = location_elem.text.strip() if location_elem else ""
            
            # Extract link
            link_elem = card.find('a', class_='base-card__full-link')
            job_url = link_elem['href'] if link_elem else ""
            
            # Check for remote/hybrid
            title_lower = title.lower()
            location_lower = location.lower()
            is_remote = "remote" in title_lower or "remote" in location_lower
            is_hybrid = "hybrid" in title_lower or "hybrid" in location_lower
            
            # Extract metadata
            metadata_elem = card.find('div', class_='base-search-card__metadata')
            metadata = metadata_elem.text.strip() if metadata_elem else ""
            
            # Parse employment type and experience level
            employment_type = self._detect_employment_type(title_lower + " " + metadata.lower())
            experience_level = self._detect_experience_level(title_lower)
            
            # Extract posted date
            time_elem = card.find('time')
            posted_at = None
            if time_elem and time_elem.get('datetime'):
                try:
                    posted_at = datetime.fromisoformat(time_elem['datetime'].replace('Z', '+00:00'))
                except:
                    pass
            
            return ScrapedJob(
                title=title,
                company_name=company_name,
                description=f"Job posted on LinkedIn. Location: {location}. {metadata}",
                location=location if not is_remote else None,
                is_remote=is_remote,
                is_hybrid=is_hybrid,
                employment_type=employment_type,
                experience_level=experience_level,
                source_url=job_url,
                source_platform="linkedin",
                external_id=self._extract_job_id_from_url(job_url, "linkedin"),
                posted_at=posted_at,
            )
            
        except Exception as e:
            logger.error(f"Failed to parse LinkedIn job card: {e}")
            return None

    def scrape_indeed_jobs(
        self,
        keywords: List[str],
        location: Optional[str] = None,
        max_results: int = 25,
        max_pages: int = 3
    ) -> List[ScrapedJob]:
        """
        Scrape jobs from Indeed using Selenium.
        Only scrapes jobs from Indeed India (indeed.co.in).
        
        Args:
            keywords: List of job keywords to search
            location: Location filter (defaults to India if not provided)
            max_results: Maximum number of results per page
            max_pages: Maximum number of pages to scrape (default: 3)
            
        Returns:
            List of scraped jobs from India only
        """
        jobs = []
        
        # Always use Indeed India domain to ensure only India jobs are scraped
        indeed_domain = "https://www.indeed.co.in"
        
        # Default to India if no location provided
        if not location:
            location = "India"
        
        for keyword in keywords:
            # Check driver health before each keyword
            if not self._is_driver_alive():
                logger.info("WebDriver not alive, reinitializing...")
                self._close_driver()
            
            driver = self._get_driver()
            
            # Scrape multiple pages (up to max_pages)
            for page in range(max_pages):
                try:
                    # Build search URL with pagination
                    start = page * 10  # Indeed uses 10 results per page
                    search_url = f"{indeed_domain}/jobs?q={keyword.replace(' ', '+')}"
                    if location:
                        search_url += f"&l={location.replace(' ', '+')}"
                    if start > 0:
                        search_url += f"&start={start}"
                    
                    logger.info(f"Scraping Indeed page {page + 1}/{max_pages}: {search_url}")
                    driver.get(search_url)
                    
                    # Wait for job cards to load - try multiple selectors
                    wait = WebDriverWait(driver, 8)
                    
                    # Try different selectors for job cards (indeed.com vs indeed.co.in)
                    selectors = [
                        (By.CLASS_NAME, "job_seen_beacon"),
                        (By.CLASS_NAME, "slider_container"),
                        (By.CSS_SELECTOR, "[data-testid='jobTitle']"),
                        (By.CLASS_NAME, "result"),
                        (By.CLASS_NAME, "jobsearch-SerpJobCard"),
                        (By.CSS_SELECTOR, "[class*='jobCard']"),
                        (By.CSS_SELECTOR, "[class*='job']"),
                    ]
                    
                    job_cards_found = False
                    for selector_type, selector_value in selectors:
                        try:
                            wait.until(EC.presence_of_element_located((selector_type, selector_value)))
                            job_cards_found = True
                            logger.debug(f"Found job cards using selector: {selector_value}")
                            break
                        except TimeoutException:
                            continue
                    
                    if not job_cards_found:
                        logger.warning(f"No job cards found for '{keyword}' page {page + 1}")
                        logger.debug(f"Page title: {driver.title}")
                        # Try to save page source for debugging
                        try:
                            page_text = driver.find_element(By.TAG_NAME, "body").text[:500]
                            logger.debug(f"Page body preview: {page_text}")
                        except:
                            pass
                        break  # Stop pagination if no cards found
                    
                    self._random_delay(2, 4)
                    
                    # Parse page with BeautifulSoup
                    soup = BeautifulSoup(driver.page_source, 'html.parser')
                    
                    # Try multiple selectors for job cards
                    job_cards = []
                    for card_class in ['job_seen_beacon', 'slider_container', 'result', 'jobsearch-SerpJobCard', 'jobCard']:
                        job_cards = soup.find_all('div', class_=lambda x: x and card_class in x if x else False)
                        if job_cards:
                            logger.debug(f"Found {len(job_cards)} cards with class containing '{card_class}'")
                            break
                    
                    # Also try CSS selectors and table rows (older Indeed layout)
                    if not job_cards:
                        job_cards = soup.find_all('a', {'data-testid': 'jobTitle'})
                        if job_cards:
                            logger.debug(f"Found {len(job_cards)} cards with data-testid='jobTitle'")
                    
                    if not job_cards:
                        job_cards = soup.find_all('tr', class_=lambda x: x and 'job' in x.lower() if x else False)
                        if job_cards:
                            logger.debug(f"Found {len(job_cards)} table row job cards")
                    
                    if not job_cards:
                        # Last resort: find any link that looks like a job title
                        job_cards = soup.find_all('a', href=lambda x: x and ('job' in x or 'jk=' in x or 'viewjob' in x))
                        if job_cards:
                            logger.debug(f"Found {len(job_cards)} job links by href pattern")
                    
                    page_job_count = 0
                    for card in job_cards[:max_results]:
                        job = self._parse_indeed_job_card(card, indeed_domain)
                        if job:
                            jobs.append(job)
                            page_job_count += 1
                    
                    logger.info(f"Scraped {page_job_count} Indeed jobs for '{keyword}' page {page + 1}")
                    
                    # Stop if no jobs found on this page
                    if page_job_count == 0:
                        break
                    
                    # Delay between pages
                    if page < max_pages - 1:
                        self._random_delay(3, 5)
                    
                except TimeoutException:
                    logger.warning(f"Timeout scraping Indeed for '{keyword}' page {page + 1}")
                    break
                except Exception as e:
                    logger.error(f"Failed to scrape Indeed for '{keyword}' page {page + 1}: {e}")
                    self._close_driver()
                    break
            
            self._random_delay(3, 5)
        
        return jobs

    def _parse_indeed_job_card(self, card, domain: str = "https://www.indeed.com") -> Optional[ScrapedJob]:
        """Parse an Indeed job card into ScrapedJob."""
        try:
            # Extract title - try multiple selectors
            title_elem = None
            for selector in ['h2', 'a']:
                title_elem = card.find(selector, class_=lambda x: x and 'jobTitle' in x) if not title_elem else title_elem
            if not title_elem:
                title_elem = card.find('a', {'data-testid': 'jobTitle'})
            if not title_elem and card.name == 'a' and card.get('data-testid') == 'jobTitle':
                title_elem = card
            title = title_elem.text.strip() if title_elem else ""
            
            # Extract company - try multiple selectors
            company_elem = card.find('span', {'data-testid': 'company-name'})
            if not company_elem:
                company_elem = card.find('span', class_=lambda x: x and 'company' in x.lower() if x else False)
            if not company_elem:
                company_elem = card.find('span', class_='companyName')
            company_name = company_elem.text.strip() if company_elem else "Unknown"
            
            # Extract location - try multiple selectors for Indeed India and global
            location = ""  # Initialize location
            location_elem = card.find('div', {'data-testid': 'job-location'})
            if not location_elem:
                location_elem = card.find('div', class_=lambda x: x and 'location' in x.lower() if x else False)
            if not location_elem:
                location_elem = card.find('div', class_='companyLocation')
            if not location_elem:
                # Try to find location in parent container
                parent = card.find_parent('td', class_='resultContent')
                if parent:
                    location_elem = parent.find('div', class_=lambda x: x and 'location' in x.lower() if x else False)
            
            if location_elem:
                location = location_elem.text.strip()
            else:
                # Look for any text that looks like a location (contains common city names)
                all_text = card.get_text(separator=' ')
                for city in ['Ahmedabad', 'Bangalore', 'Mumbai', 'Delhi', 'Pune', 'Hyderabad', 'Chennai', 'Kolkata', 'Gurgaon', 'Noida', 'Remote']:
                    if city in all_text:
                        location = city
                        break
            
            # Extract salary if available
            salary_elem = card.find('div', class_=lambda x: x and 'salary' in x.lower() if x else False)
            if not salary_elem:
                salary_elem = card.find('span', class_=lambda x: x and 'salary' in x.lower() if x else False)
            salary_text = salary_elem.text.strip() if salary_elem else ""
            salary_min, salary_max = self._extract_salary_from_text(salary_text)
            
            # Extract job snippet/summary
            snippet_elem = card.find('div', class_=lambda x: x and 'snippet' in x.lower() if x else False)
            if not snippet_elem:
                snippet_elem = card.find('div', class_='job-snippet')
            if not snippet_elem:
                snippet_elem = card.find('td', class_='resultContent')
            snippet = snippet_elem.text.strip() if snippet_elem else ""
            
            # Extract link
            link_elem = card.find('a', class_=lambda x: x and 'jobTitle' in x if x else False)
            if not link_elem:
                link_elem = card.find('a', {'data-testid': 'jobTitle'})
            if not link_elem and card.name == 'a':
                link_elem = card
            job_url = ""
            if link_elem and link_elem.get('href'):
                href = link_elem['href']
                if href.startswith('/'):
                    job_url = domain + href
                elif href.startswith('http'):
                    job_url = href
                else:
                    job_url = domain + '/' + href
            
            # Check for remote/hybrid
            title_lower = title.lower()
            location_lower = location.lower()
            is_remote = "remote" in title_lower or "remote" in location_lower
            is_hybrid = "hybrid" in title_lower or "hybrid" in location_lower
            
            # Parse employment type and experience level
            employment_type = self._detect_employment_type(title_lower + " " + snippet.lower())
            experience_level = self._detect_experience_level(title_lower)
            
            # Extract posted date
            date_elem = card.find('span', class_='date')
            posted_at = None
            if date_elem:
                posted_at = self._parse_relative_date(date_elem.text)
            
            # Build comprehensive description
            description_parts = []
            description_parts.append(f"Position: {title}")
            description_parts.append("")
            
            if snippet:
                description_parts.append(snippet)
                description_parts.append("")
            
            # Extract tech keywords from title for skills
            tech_keywords = self._extract_tech_keywords(title)
            if tech_keywords:
                description_parts.append(f"Key Technologies: {', '.join(tech_keywords)}")
                description_parts.append("")
            
            if location:
                description_parts.append(f"Location: {location}")
            
            if salary_text:
                description_parts.append(f"Compensation: {salary_text}")
            
            if is_remote:
                description_parts.append("Work Type: Remote")
            elif is_hybrid:
                description_parts.append("Work Type: Hybrid")
            
            full_description = "\n".join(description_parts)
            
            # Build requirements from extracted info
            requirements_parts = []
            if tech_keywords:
                requirements_parts.append(f"- Proficiency in: {', '.join(tech_keywords[:5])}")
            if experience_level:
                requirements_parts.append(f"- Experience level: {experience_level}")
            
            requirements = "\n".join(requirements_parts) if requirements_parts else None
            
            return ScrapedJob(
                title=title,
                company_name=company_name,
                description=full_description,
                requirements=requirements,
                location=location if not is_remote else None,
                is_remote=is_remote,
                is_hybrid=is_hybrid,
                salary_min=salary_min,
                salary_max=salary_max,
                employment_type=employment_type,
                experience_level=experience_level,
                source_url=job_url,
                source_platform="indeed",
                external_id=self._extract_job_id_from_url(job_url, "indeed"),
                posted_at=posted_at,
            )
            
        except Exception as e:
            logger.error(f"Failed to parse Indeed job card: {e}")
            return None

    def scrape_glassdoor_jobs(
        self,
        keywords: List[str],
        location: Optional[str] = None,
        max_results: int = 25
    ) -> List[ScrapedJob]:
        """
        Scrape jobs from Glassdoor using Selenium.
        
        Args:
            keywords: List of job keywords to search
            location: Location filter
            max_results: Maximum number of results
            
        Returns:
            List of scraped jobs
        """
        jobs = []
        
        for keyword in keywords:
            # Check driver health before each keyword
            if not self._is_driver_alive():
                logger.info("WebDriver not alive, reinitializing...")
                self._close_driver()
            
            driver = self._get_driver()
            
            try:
                # Build search URL
                search_url = f"https://www.glassdoor.com/Job/jobs.htm?sc.keyword={keyword.replace(' ', '%20')}"
                if location:
                    search_url += f"&locT=C&locName={location.replace(' ', '%20')}"
                
                logger.info(f"Scraping Glassdoor: {search_url}")
                driver.get(search_url)
                
                # Wait for job listings to load
                wait = WebDriverWait(driver, 10)
                wait.until(EC.presence_of_element_located((By.CLASS_NAME, "react-job-listing")))
                
                self._random_delay(2, 4)
                
                # Parse page with BeautifulSoup
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                job_cards = soup.find_all('li', class_='react-job-listing')
                
                for card in job_cards[:max_results]:
                    job = self._parse_glassdoor_job_card(card)
                    if job:
                        jobs.append(job)
                
                logger.info(f"Scraped {len(job_cards)} Glassdoor jobs for keyword '{keyword}'")
                
            except TimeoutException:
                logger.warning(f"Timeout scraping Glassdoor for '{keyword}'")
            except Exception as e:
                logger.error(f"Failed to scrape Glassdoor for '{keyword}': {e}")
                self._close_driver()
            
            self._random_delay(3, 5)
        
        return jobs

    def scrape_naukri_jobs(
        self,
        keywords: List[str],
        location: Optional[str] = None,
        max_results: int = 25,
        max_pages: int = 3
    ) -> List[ScrapedJob]:
        """
        Scrape jobs from Naukri.com using Selenium.
        Naukri is one of India's largest job portals.
        
        Args:
            keywords: List of job keywords to search
            location: Location filter
            max_results: Maximum number of results per page
            max_pages: Maximum number of pages to scrape
            
        Returns:
            List of scraped jobs
        """
        jobs = []
        
        for keyword in keywords:
            # Check driver health before each keyword
            if not self._is_driver_alive():
                logger.info("WebDriver not alive, reinitializing...")
                self._close_driver()
            
            driver = self._get_driver()
            
            # Scrape multiple pages
            for page in range(max_pages):
                try:
                    # Build search URL for Naukri
                    # Naukri URL format: https://www.naukri.com/{keyword}-jobs-in-{location}
                    keyword_slug = keyword.replace(' ', '-').lower()
                    
                    if page == 0:
                        if location:
                            location_slug = location.replace(' ', '-').lower()
                            search_url = f"https://www.naukri.com/{keyword_slug}-jobs-in-{location_slug}"
                        else:
                            search_url = f"https://www.naukri.com/{keyword_slug}-jobs"
                    else:
                        # Naukri uses pagination with page numbers
                        if location:
                            location_slug = location.replace(' ', '-').lower()
                            search_url = f"https://www.naukri.com/{keyword_slug}-jobs-in-{location_slug}-{page + 1}"
                        else:
                            search_url = f"https://www.naukri.com/{keyword_slug}-jobs-{page + 1}"
                    
                    logger.info(f"Scraping Naukri page {page + 1}/{max_pages}: {search_url}")
                    driver.get(search_url)
                    
                    # Wait for job cards to load
                    wait = WebDriverWait(driver, 10)
                    
                    # Try multiple selectors for Naukri job cards
                    selectors = [
                        (By.CLASS_NAME, "jobTuple"),
                        (By.CLASS_NAME, "list"),
                        (By.CSS_SELECTOR, "[class*='jobTuple']"),
                        (By.CSS_SELECTOR, "[data-job-id]"),
                    ]
                    
                    job_cards_found = False
                    for selector_type, selector_value in selectors:
                        try:
                            wait.until(EC.presence_of_element_located((selector_type, selector_value)))
                            job_cards_found = True
                            logger.debug(f"Found Naukri cards using selector: {selector_value}")
                            break
                        except TimeoutException:
                            continue
                    
                    if not job_cards_found:
                        logger.warning(f"No Naukri cards found for '{keyword}' page {page + 1}")
                        logger.debug(f"Page title: {driver.title}")
                        break
                    
                    self._random_delay(2, 4)
                    
                    # Scroll to load more jobs
                    for _ in range(min(max_results // 10, 3)):
                        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        self._random_delay(1, 2)
                    
                    # Parse page with BeautifulSoup
                    soup = BeautifulSoup(driver.page_source, 'html.parser')
                    
                    # Try multiple selectors for job cards
                    job_cards = []
                    for card_class in ['jobTuple', 'list', 'job tuple']:
                        job_cards = soup.find_all('div', class_=card_class)
                        if job_cards:
                            logger.debug(f"Found {len(job_cards)} Naukri cards with class '{card_class}'")
                            break
                    
                    # If still no cards, try data attribute
                    if not job_cards:
                        job_cards = soup.find_all('div', attrs={'data-job-id': True})
                        logger.debug(f"Found {len(job_cards)} Naukri cards with data-job-id")
                    
                    page_job_count = 0
                    for card in job_cards[:max_results]:
                        job = self._parse_naukri_job_card(card)
                        if job:
                            jobs.append(job)
                            page_job_count += 1
                    
                    logger.info(f"Scraped {page_job_count} Naukri jobs for '{keyword}' page {page + 1}")
                    
                    # Stop if no jobs found on this page
                    if page_job_count == 0:
                        break
                    
                    # Delay between pages
                    if page < max_pages - 1:
                        self._random_delay(3, 5)
                    
                except TimeoutException:
                    logger.warning(f"Timeout scraping Naukri for '{keyword}' page {page + 1}")
                    break
                except Exception as e:
                    logger.error(f"Failed to scrape Naukri for '{keyword}' page {page + 1}: {e}")
                    self._close_driver()
                    break
            
            self._random_delay(3, 5)
        
        return jobs

    def _parse_naukri_job_card(self, card) -> Optional[ScrapedJob]:
        """Parse a Naukri job card into ScrapedJob."""
        try:
            # Extract title
            title_elem = card.find('a', class_='title')
            if not title_elem:
                title_elem = card.find('a', class_=lambda x: x and 'title' in x.lower() if x else False)
            title = title_elem.text.strip() if title_elem else ""
            
            # Extract job URL
            job_url = ""
            if title_elem and title_elem.get('href'):
                href = title_elem['href']
                if href.startswith('/'):
                    job_url = "https://www.naukri.com" + href
                elif href.startswith('http'):
                    job_url = href
            
            # Extract company
            company_elem = card.find('a', class_='subTitle')
            if not company_elem:
                company_elem = card.find('span', class_=lambda x: x and 'company' in x.lower() if x else False)
            company_name = company_elem.text.strip() if company_elem else "Unknown"
            
            # Extract location
            location_elem = card.find('span', class_='locWdth')
            if not location_elem:
                location_elem = card.find('span', class_=lambda x: x and 'location' in x.lower() if x else False)
            location = location_elem.text.strip() if location_elem else ""
            
            # Check for remote/hybrid
            title_lower = title.lower()
            location_lower = location.lower()
            is_remote = "remote" in title_lower or "remote" in location_lower or "work from home" in location_lower
            is_hybrid = "hybrid" in title_lower or "hybrid" in location_lower
            
            # Extract experience
            exp_elem = card.find('span', class_='expWdth')
            experience_text = exp_elem.text.strip() if exp_elem else ""
            
            # Extract salary if available
            salary_elem = card.find('span', class_='salary')
            salary_text = salary_elem.text.strip() if salary_elem else ""
            salary_min, salary_max = self._extract_salary_from_text(salary_text)
            
            # Extract job description/snippet
            desc_elem = card.find('span', class_='job-desc')
            if not desc_elem:
                desc_elem = card.find('div', class_=lambda x: x and 'description' in x.lower() if x else False)
            description = desc_elem.text.strip() if desc_elem else ""
            
            # Build comprehensive description with all available info
            description_parts = []
            
            # Add title as context
            description_parts.append(f"Position: {title}")
            description_parts.append("")
            
            # Add main description if available
            if description:
                description_parts.append(description)
                description_parts.append("")
            
            # Add key skills from title (extract common tech skills)
            tech_keywords = self._extract_tech_keywords(title)
            if tech_keywords:
                description_parts.append(f"Key Technologies: {', '.join(tech_keywords)}")
                description_parts.append("")
            
            # Add experience requirements
            if experience_text:
                description_parts.append(f"Experience Required: {experience_text}")
            
            # Add salary info
            if salary_text:
                description_parts.append(f"Compensation: {salary_text}")
            
            # Add location context
            if location:
                description_parts.append(f"Location: {location}")
            
            # Add remote/hybrid info
            if is_remote:
                description_parts.append("Work Type: Remote")
            elif is_hybrid:
                description_parts.append("Work Type: Hybrid")
            
            full_description = "\n".join(description_parts)
            
            # Parse experience level
            experience_level = self._detect_experience_level(title_lower + " " + experience_text.lower())
            
            # Extract posted date if available
            posted_elem = card.find('span', class_=lambda x: x and 'posted' in x.lower() if x else False)
            posted_at = None
            if posted_elem:
                posted_at = self._parse_relative_date(posted_elem.text)
            
            # Build requirements from extracted info
            requirements_parts = []
            if experience_text:
                requirements_parts.append(f"- {experience_text} of relevant experience")
            if tech_keywords:
                requirements_parts.append(f"- Proficiency in: {', '.join(tech_keywords[:5])}")
            
            requirements = "\n".join(requirements_parts) if requirements_parts else None
            
            return ScrapedJob(
                title=title,
                company_name=company_name,
                description=full_description,
                requirements=requirements,
                location=location if not is_remote else None,
                is_remote=is_remote,
                is_hybrid=is_hybrid,
                salary_min=salary_min,
                salary_max=salary_max,
                salary_currency="INR" if salary_min else "USD",
                employment_type="full-time",
                experience_level=experience_level,
                source_url=job_url,
                source_platform="naukri",
                external_id=self._extract_job_id_from_url(job_url, "naukri"),
                posted_at=posted_at,
            )
            
        except Exception as e:
            logger.error(f"Failed to parse Naukri job card: {e}")
            return None

    def scrape_internshala_jobs(
        self,
        keywords: List[str],
        location: Optional[str] = None,
        max_results: int = 25,
        max_pages: int = 3
    ) -> List[ScrapedJob]:
        """
        Scrape jobs/internships from Internshala using Selenium.
        Uses non-headless browser to avoid detection.
        Scrapes up to max_pages pages per keyword.
        
        Args:
            keywords: List of job keywords to search
            location: Location filter
            max_results: Maximum number of results per page
            max_pages: Maximum number of pages to scrape (default: 3)
            
        Returns:
            List of scraped jobs
        """
        jobs = []
        
        # Use a separate driver instance for Internshala (non-headless)
        internshala_driver = None
        
        try:
            # Initialize non-headless driver for Internshala
            chrome_options = Options()
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--start-maximized')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            internshala_driver = webdriver.Chrome(options=chrome_options)
            
            # Execute CDP commands to avoid detection
            internshala_driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    })
                '''
            })
            
            logger.info("Internshala WebDriver initialized (non-headless)")
            
            for keyword in keywords:
                # Scrape multiple pages (up to max_pages)
                for page in range(max_pages):
                    try:
                        # Build search URL for Internshala with pagination
                        page_num = page + 1
                        keyword_slug = keyword.replace(' ', '-').lower()
                        location_slug = location.replace(' ', '-').lower() if location else None
                        
                        if page == 0:
                            if location_slug:
                                search_url = f"https://internshala.com/internships/{keyword_slug}-internship-in-{location_slug}/"
                            else:
                                search_url = f"https://internshala.com/internships/{keyword_slug}-internship/"
                        else:
                            if location_slug:
                                search_url = f"https://internshala.com/internships/page-{page_num}/{keyword_slug}-internship-in-{location_slug}/"
                            else:
                                search_url = f"https://internshala.com/internships/page-{page_num}/{keyword_slug}-internship/"
                        
                        logger.info(f"Scraping Internshala page {page + 1}/{max_pages}: {search_url}")
                        internshala_driver.get(search_url)
                        
                        # Wait longer for Internshala to load (JavaScript-heavy)
                        wait = WebDriverWait(internshala_driver, 15)
                        
                        # Try multiple selectors for job cards
                        selectors = [
                            (By.CLASS_NAME, "individual_internship"),
                            (By.CLASS_NAME, "internship_meta"),
                            (By.CSS_SELECTOR, "[class*='internship']"),
                            (By.XPATH, "//div[contains(@class, 'internship')]"),
                        ]
                        
                        job_cards_found = False
                        for selector_type, selector_value in selectors:
                            try:
                                wait.until(EC.presence_of_element_located((selector_type, selector_value)))
                                job_cards_found = True
                                logger.debug(f"Found Internshala cards using selector: {selector_value}")
                                break
                            except TimeoutException:
                                continue
                        
                        if not job_cards_found:
                            logger.warning(f"No Internshala cards found for '{keyword}' page {page + 1}")
                            logger.debug(f"Page title: {internshala_driver.title}")
                            logger.debug(f"Page URL: {internshala_driver.current_url}")
                            # Take screenshot for debugging
                            try:
                                screenshot_path = f"/tmp/internshala_debug_{keyword.replace(' ', '_')}_page{page}.png"
                                internshala_driver.save_screenshot(screenshot_path)
                                logger.debug(f"Screenshot saved: {screenshot_path}")
                            except:
                                pass
                            break
                        
                        # Longer delay for Internshala
                        time.sleep(random.uniform(3, 5))
                        
                        # Scroll to load all content
                        for _ in range(3):
                            internshala_driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                            time.sleep(1)
                        
                        # Parse page with BeautifulSoup
                        soup = BeautifulSoup(internshala_driver.page_source, 'html.parser')
                        
                        # Try multiple selectors for job cards
                        job_cards = []
                        for card_class in ['individual_internship', 'internship_meta']:
                            job_cards = soup.find_all('div', class_=card_class)
                            if job_cards:
                                logger.debug(f"Found {len(job_cards)} Internshala cards with class '{card_class}'")
                                break
                        
                        # If still no cards, try broader search
                        if not job_cards:
                            job_cards = soup.find_all('div', class_=lambda x: x and 'internship' in str(x).lower() if x else False)
                            logger.debug(f"Found {len(job_cards)} Internshala cards with broad search")
                        
                        page_job_count = 0
                        for card in job_cards[:max_results]:
                            job = self._parse_internshala_job_card(card)
                            if job:
                                jobs.append(job)
                                page_job_count += 1
                        
                        logger.info(f"Scraped {page_job_count} Internshala jobs for '{keyword}' page {page + 1}")
                        
                        # Stop if no jobs found on this page
                        if page_job_count == 0:
                            break
                        
                        # Delay between pages
                        if page < max_pages - 1:
                            time.sleep(random.uniform(3, 5))
                    
                    except TimeoutException:
                        logger.warning(f"Timeout scraping Internshala for '{keyword}' page {page + 1}")
                        break
                    except Exception as e:
                        logger.error(f"Failed to scrape Internshala for '{keyword}' page {page + 1}: {e}")
                        break
                
                # Delay between keywords
                time.sleep(random.uniform(3, 5))
        
        finally:
            # Close Internshala driver
            if internshala_driver:
                try:
                    internshala_driver.quit()
                    logger.info("Internshala WebDriver closed")
                except:
                    pass
        
        return jobs

    def _parse_glassdoor_job_card(self, card) -> Optional[ScrapedJob]:
        """Parse a Glassdoor job card into ScrapedJob."""
        try:
            # Extract title
            title_elem = card.find('a', class_='jobLink')
            title = title_elem.text.strip() if title_elem else ""
            job_url = title_elem['href'] if title_elem else ""
            if job_url and not job_url.startswith('http'):
                job_url = "https://www.glassdoor.com" + job_url
            
            # Extract company
            company_elem = card.find('a', class_='job-search-8wag7x')
            if not company_elem:
                company_elem = card.find('div', class_='d-flex')
            company_name = company_elem.text.strip() if company_elem else "Unknown"
            
            # Extract location
            location_elem = card.find('span', class_='job-search-8wag7x')
            location = location_elem.text.strip() if location_elem else ""
            
            # Extract salary if available
            salary_elem = card.find('span', {'data-test': 'detailSalary'})
            salary_text = salary_elem.text.strip() if salary_elem else ""
            salary_min, salary_max = self._extract_salary_from_text(salary_text)
            
            # Check for remote/hybrid
            title_lower = title.lower()
            location_lower = location.lower()
            is_remote = "remote" in title_lower or "remote" in location_lower
            is_hybrid = "hybrid" in title_lower or "hybrid" in location_lower
            
            # Parse employment type and experience level
            employment_type = self._detect_employment_type(title_lower)
            experience_level = self._detect_experience_level(title_lower)
            
            return ScrapedJob(
                title=title,
                company_name=company_name,
                description=f"Job posted on Glassdoor. Location: {location}.",
                location=location if not is_remote else None,
                is_remote=is_remote,
                is_hybrid=is_hybrid,
                salary_min=salary_min,
                salary_max=salary_max,
                employment_type=employment_type,
                experience_level=experience_level,
                source_url=job_url,
                source_platform="glassdoor",
                external_id=self._extract_job_id_from_url(job_url, "glassdoor"),
            )
            
        except Exception as e:
            logger.error(f"Failed to parse Glassdoor job card: {e}")
            return None

    def _parse_internshala_job_card(self, card) -> Optional[ScrapedJob]:
        """Parse an Internshala job/internship card into ScrapedJob."""
        try:
            # Extract title
            title_elem = card.find('h3', class_='job-heading')
            if not title_elem:
                title_elem = card.find('a', class_='view_detail_button')
            title = title_elem.text.strip() if title_elem else ""
            
            # Extract company
            company_elem = card.find('h4', class_='company-name')
            if not company_elem:
                company_elem = card.find('a', class_='link_display_like_text')
            company_name = company_elem.text.strip() if company_elem else "Unknown"
            
            # Extract location
            location_elem = card.find('a', id='location_names')
            if not location_elem:
                location_elem = card.find('span', class_='location_link')
            location = location_elem.text.strip() if location_elem else ""
            
            # Check for work from home / remote
            wfh_elem = card.find('div', class_='work_from_home')
            location_lower = location.lower()
            title_lower = title.lower()
            is_remote = wfh_elem is not None or "work from home" in location_lower or "remote" in title_lower
            is_hybrid = "hybrid" in title_lower or "hybrid" in location_lower
            
            # Extract job type (internship/job)
            job_type_elem = card.find('div', class_='job-type')
            job_type = job_type_elem.text.strip().lower() if job_type_elem else ""
            is_internship = "internship" in job_type or "internship" in title_lower
            
            # Extract duration/stipend info
            duration_elem = card.find('div', class_='internship_other_details')
            duration_text = duration_elem.text.strip() if duration_elem else ""
            
            # Extract CTC/stipend
            ctc_elem = card.find('span', class_='stipend')
            ctc_text = ctc_elem.text.strip() if ctc_elem else ""
            salary_min, salary_max = self._extract_salary_from_text(ctc_text)
            
            # Extract job detail URL
            detail_link = card.find('a', class_='view_detail_button')
            job_url = ""
            if detail_link and detail_link.get('href'):
                job_url = "https://internshala.com" + detail_link['href']
            
            # Parse experience level (Internshala mainly has internships = entry level)
            experience_level = "entry" if is_internship else self._detect_experience_level(title_lower)
            employment_type = "internship" if is_internship else "full-time"
            
            # Extract tech keywords from title
            tech_keywords = self._extract_tech_keywords(title)
            
            # Build comprehensive description
            description_parts = []
            description_parts.append(f"Position: {title}")
            description_parts.append("")
            
            if is_internship:
                description_parts.append(f"Internship opportunity at {company_name}")
            else:
                description_parts.append(f"Job opportunity at {company_name}")
            description_parts.append("")
            
            if tech_keywords:
                description_parts.append(f"Key Technologies: {', '.join(tech_keywords)}")
                description_parts.append("")
            
            if duration_text:
                description_parts.append(f"Duration/Details: {duration_text}")
            if ctc_text:
                description_parts.append(f"Stipend/CTC: {ctc_text}")
            if location:
                description_parts.append(f"Location: {location}")
            
            if is_remote:
                description_parts.append("Work Type: Work From Home/Remote")
            elif is_hybrid:
                description_parts.append("Work Type: Hybrid")
            
            description = "\n".join(description_parts)
            
            # Build requirements
            requirements_parts = []
            if tech_keywords:
                requirements_parts.append(f"- Proficiency in: {', '.join(tech_keywords[:5])}")
            if is_internship:
                requirements_parts.append("- Open to students and fresh graduates")
            
            requirements = "\n".join(requirements_parts) if requirements_parts else None
            
            return ScrapedJob(
                title=title,
                company_name=company_name,
                description=description,
                requirements=requirements,
                location=location if not is_remote else None,
                is_remote=is_remote,
                is_hybrid=is_hybrid,
                salary_min=salary_min,
                salary_max=salary_max,
                salary_currency="INR" if not salary_min else "USD",
                employment_type=employment_type,
                experience_level=experience_level,
                source_url=job_url,
                source_platform="internshala",
                external_id=self._extract_job_id_from_url(job_url, "internshala"),
            )
            
        except Exception as e:
            logger.error(f"Failed to parse Internshala job card: {e}")
            return None

    def _extract_job_id_from_url(self, url: str, platform: str) -> Optional[str]:
        """Extract job ID from URL."""
        if not url:
            return None
        
        try:
            if platform == "linkedin":
                # LinkedIn URLs: /jobs/view/1234567890
                match = re.search(r'/view/(\d+)', url)
                return match.group(1) if match else None
            elif platform == "indeed":
                # Indeed URLs: jk=abc123
                match = re.search(r'jk=([a-zA-Z0-9]+)', url)
                return match.group(1) if match else None
            elif platform == "glassdoor":
                # Glassdoor URLs: jobListingId=123456
                match = re.search(r'jobListingId=(\d+)', url)
                return match.group(1) if match else None
            elif platform == "internshala":
                # Internshala URLs: /internship/detail/job-slug-12345678/
                match = re.search(r'/(\d+)/?$', url)
                if match:
                    return match.group(1)
                # Alternative pattern: job-slug-12345678
                match = re.search(r'-([a-zA-Z0-9]+)/?$', url)
                return match.group(1) if match else None
            elif platform == "naukri":
                # Naukri URLs: /job-listings-job-slug-12345678
                match = re.search(r'-([a-zA-Z0-9]+)/?$', url)
                if match:
                    return match.group(1)
                # Alternative: jobId=123456
                match = re.search(r'jobId=(\d+)', url)
                return match.group(1) if match else None
        except:
            pass
        
        return None

    def _parse_relative_date(self, date_text: str) -> Optional[datetime]:
        """Parse relative date like '2 days ago' into datetime."""
        try:
            date_text = date_text.lower()
            now = datetime.now()
            
            if 'today' in date_text or 'just now' in date_text:
                return now
            elif 'yesterday' in date_text:
                return now - timedelta(days=1)
            elif 'day' in date_text:
                match = re.search(r'(\d+)', date_text)
                if match:
                    days = int(match.group(1))
                    return now - timedelta(days=days)
            elif 'hour' in date_text:
                match = re.search(r'(\d+)', date_text)
                if match:
                    hours = int(match.group(1))
                    return now - timedelta(hours=hours)
            elif 'minute' in date_text:
                match = re.search(r'(\d+)', date_text)
                if match:
                    minutes = int(match.group(1))
                    return now - timedelta(minutes=minutes)
        except:
            pass
        
        return None

    async def scrape_mock_jobs(
        self,
        keywords: List[str],
        max_results: int = 20
    ) -> List[ScrapedJob]:
        """
        Generate mock jobs for testing/demo purposes.
        
        Args:
            keywords: List of job keywords
            max_results: Maximum number of mock jobs
            
        Returns:
            List of mock scraped jobs
        """
        jobs = []
        
        mock_companies = [
            {"name": "TechCorp Inc.", "industry": "Technology", "website": "https://techcorp.com"},
            {"name": "DataSystems LLC", "industry": "Data Analytics", "website": "https://datasystems.com"},
            {"name": "CloudNine Solutions", "industry": "Cloud Computing", "website": "https://cloudnine.io"},
            {"name": "AI Innovations", "industry": "Artificial Intelligence", "website": "https://ai-innovations.com"},
            {"name": "StartupXYZ", "industry": "Software", "website": "https://startupxyz.com"},
        ]
        
        mock_locations = ["San Francisco, CA", "New York, NY", "Austin, TX", "Seattle, WA", "Remote"]
        
        for i, keyword in enumerate(keywords[:5]):
            for j in range(min(max_results // len(keywords), 4)):
                company = mock_companies[(i + j) % len(mock_companies)]
                location = mock_locations[(i + j) % len(mock_locations)]
                is_remote = location == "Remote"
                
                job = ScrapedJob(
                    title=f"{keyword.title()} Engineer",
                    company_name=company["name"],
                    description=self._generate_mock_description(keyword),
                    location=location if not is_remote else None,
                    is_remote=is_remote,
                    is_hybrid=not is_remote and j % 3 == 0,
                    salary_min=80000 + (j * 20000),
                    salary_max=120000 + (j * 25000),
                    employment_type="full-time" if j % 2 == 0 else "contract",
                    experience_level=["entry", "mid", "senior"][j % 3],
                    source_platform="mock",
                    external_id=f"mock_{keyword}_{j}",
                    posted_at=datetime.now() - timedelta(days=j),
                    company_industry=company["industry"],
                    company_website=company["website"],
                    requirements=f"- 3+ years of {keyword} experience\n- Strong problem-solving skills",
                    responsibilities=f"- Develop {keyword} solutions\n- Collaborate with cross-functional teams",
                )
                jobs.append(job)
        
        logger.info(f"Generated {len(jobs)} mock jobs")
        return jobs

    def _generate_mock_description(self, keyword: str) -> str:
        """Generate a mock job description."""
        return f"""We are looking for a talented {keyword.title()} Engineer to join our growing team.

In this role, you will be responsible for designing, developing, and maintaining {keyword}-based solutions. You will work closely with product managers, designers, and other engineers to deliver high-quality software.

Key Responsibilities:
- Design and implement {keyword} applications and services
- Write clean, maintainable, and efficient code
- Collaborate with cross-functional teams
- Participate in code reviews and technical discussions
- Mentor junior team members

Requirements:
- 3+ years of professional {keyword} development experience
- Strong understanding of software engineering principles
- Experience with modern development tools and practices
- Excellent communication and teamwork skills
- Bachelor's degree in Computer Science or related field

We offer competitive compensation, comprehensive benefits, and a collaborative work environment."""

    def _extract_salary_from_text(self, text: str) -> tuple:
        """Extract salary range from text."""
        # Look for patterns like "$80,000 - $120,000" or "$80k-$120k"
        patterns = [
            r'\$([\d,]+)\s*-\s*\$([\d,]+)',
            r'\$([\d]+)k?\s*-\s*\$([\d]+)k?',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                min_str = match.group(1).replace(',', '').replace('k', '000')
                max_str = match.group(2).replace(',', '').replace('k', '000')
                try:
                    return int(min_str), int(max_str)
                except:
                    pass
        
        return None, None

    def _extract_tech_keywords(self, text: str) -> List[str]:
        """
        Extract technology keywords from job title or description.
        Returns a list of tech skills found in the text.
        """
        if not text:
            return []
        
        text_lower = text.lower()
        
        # Comprehensive tech keywords mapping
        tech_keywords = {
            # Programming Languages
            'python', 'javascript', 'typescript', 'java', 'c++', 'c#', 'go', 'golang', 'rust',
            'ruby', 'php', 'swift', 'kotlin', 'scala', 'r', 'matlab', 'perl', 'shell', 'bash',
            'sql', 'html', 'css', 'sass', 'less', 'dart', 'julia', 'groovy', 'lua',
            
            # Frameworks & Libraries
            'react', 'reactjs', 'vue', 'vuejs', 'angular', 'svelte', 'nextjs', 'next.js', 
            'nuxt', 'django', 'flask', 'fastapi', 'spring', 'spring boot', 'laravel', 
            'express', 'expressjs', 'nestjs', 'nest.js', 'rails', 'aspnet', 'aspnet.core',
            'bootstrap', 'tailwind', 'material-ui', 'mui', 'antd', 'chakra', 'jquery',
            'tensorflow', 'pytorch', 'keras', 'scikit-learn', 'sklearn', 'pandas', 'numpy',
            'matplotlib', 'seaborn', 'opencv', 'nltk', 'spacy', 'huggingface', 'transformers',
            
            # Databases
            'postgresql', 'postgres', 'mysql', 'mongodb', 'redis', 'elasticsearch', 
            'cassandra', 'dynamodb', 'sqlite', 'oracle', 'sql server', 'mssql', 'firebase',
            'couchdb', 'neo4j', 'cockroachdb', 'supabase', 'prisma', 'typeorm',
            
            # Cloud & DevOps
            'aws', 'amazon web services', 'azure', 'gcp', 'google cloud', 'heroku', 
            'digitalocean', 'vercel', 'netlify', 'cloudflare', 'docker', 'kubernetes', 
            'k8s', 'terraform', 'ansible', 'jenkins', 'github actions', 'gitlab ci',
            'circleci', 'travis', 'pulumi', 'vagrant', 'puppet', 'chef',
            
            # Tools & Platforms
            'git', 'github', 'gitlab', 'bitbucket', 'jira', 'confluence', 'slack', 
            'trello', 'notion', 'asana', 'linear', 'figma', 'sketch', 'adobe xd',
            'postman', 'insomnia', 'swagger', 'openapi', 'graphql', 'rest api',
            
            # Data & Analytics
            'tableau', 'powerbi', 'power bi', 'looker', 'snowflake', 'bigquery', 
            'redshift', 'databricks', 'apache spark', 'spark', 'hadoop', 'kafka',
            'airflow', 'dbt', 'fivetran', 'stitch', 'segment',
            
            # Mobile
            'react native', 'flutter', 'ios', 'android', 'swift', 'objective-c',
            'xamarin', 'ionic', 'cordova', 'phonegap',
            
            # Testing
            'jest', 'mocha', 'cypress', 'selenium', 'playwright', 'junit', 'pytest',
            'unittest', 'testing', 'tdd', 'bdd',
            
            # Concepts & Methodologies
            'machine learning', 'deep learning', 'ai', 'artificial intelligence',
            'data science', 'data engineering', 'data analysis', 'nlp', 'computer vision',
            'blockchain', 'web3', 'devops', 'sre', 'site reliability', 'microservices',
            'serverless', 'ci/cd', 'agile', 'scrum', 'kanban', 'oop', 'functional programming',
            'system design', 'architecture', 'api design', 'ui/ux', 'frontend', 'backend',
            'fullstack', 'full stack', 'web development', 'mobile development',
        }
        
        found_keywords = []
        for keyword in tech_keywords:
            # Use word boundaries for matching
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, text_lower):
                found_keywords.append(keyword)
        
        return found_keywords

    def _normalize_employment_type(self, contract_type: str) -> Optional[str]:
        """Normalize employment type."""
        contract_lower = contract_type.lower()
        
        if "full" in contract_lower or "permanent" in contract_lower:
            return "full-time"
        elif "part" in contract_lower:
            return "part-time"
        elif "contract" in contract_lower or "freelance" in contract_lower:
            return "contract"
        elif "intern" in contract_lower:
            return "internship"
        
        return None

    def _detect_employment_type(self, text: str) -> Optional[str]:
        """Detect employment type from text."""
        text_lower = text.lower()
        
        if "full-time" in text_lower or "full time" in text_lower:
            return "full-time"
        elif "part-time" in text_lower or "part time" in text_lower:
            return "part-time"
        elif "contract" in text_lower:
            return "contract"
        elif "intern" in text_lower:
            return "internship"
        
        return "full-time"  # Default

    def _detect_experience_level(self, text: str) -> Optional[str]:
        """Detect experience level from text."""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ["senior", "sr.", "lead", "principal", "staff"]):
            return "senior"
        elif any(word in text_lower for word in ["mid", "intermediate", "experienced"]):
            return "mid"
        elif any(word in text_lower for word in ["junior", "jr.", "entry", "associate", "fresh"]):
            return "entry"
        elif "executive" in text_lower or "director" in text_lower or "vp" in text_lower:
            return "executive"
        
        return None

    def _is_duplicate_job(self, job: ScrapedJob) -> bool:
        """Check if a job is already in the database."""
        # Check by external_id if available
        if job.external_id:
            existing = Job.query.filter_by(
                external_id=job.external_id,
                source_platform=job.source_platform
            ).first()
            if existing:
                return True
        
        # Check by title + company combination (within last 30 days)
        thirty_days_ago = datetime.now() - timedelta(days=30)
        existing = Job.query.filter(
            Job.title.ilike(job.title),
            Job.created_at >= thirty_days_ago
        ).join(Company).filter(
            Company.name.ilike(job.company_name)
        ).first()
        
        return existing is not None

    def store_scraped_job(self, scraped_job: ScrapedJob) -> Optional[Job]:
        """
        Store a scraped job in the database.
        
        Args:
            scraped_job: Scraped job data
            
        Returns:
            Created Job object or None if duplicate
        """
        # Check for duplicates
        if self._is_duplicate_job(scraped_job):
            logger.debug(f"Skipping duplicate job: {scraped_job.title} at {scraped_job.company_name}")
            return None
        
        try:
            # Prepare job data
            job_data = {
                "title": scraped_job.title,
                "description": scraped_job.description,
                "requirements": scraped_job.requirements,
                "responsibilities": scraped_job.responsibilities,
                "location": scraped_job.location,
                "is_remote": scraped_job.is_remote,
                "is_hybrid": scraped_job.is_hybrid,
                "salary_min": scraped_job.salary_min,
                "salary_max": scraped_job.salary_max,
                "salary_currency": scraped_job.salary_currency,
                "employment_type": scraped_job.employment_type,
                "experience_level": scraped_job.experience_level,
                "source_url": scraped_job.source_url,
                "source_platform": scraped_job.source_platform,
                "external_id": scraped_job.external_id,
                "posted_at": scraped_job.posted_at.isoformat() if scraped_job.posted_at else None,
                "company": {
                    "name": scraped_job.company_name,
                    "description": scraped_job.company_description,
                    "industry": scraped_job.company_industry,
                    "website": scraped_job.company_website,
                } if any([scraped_job.company_description, scraped_job.company_industry, scraped_job.company_website]) else {"name": scraped_job.company_name},
            }
            
            # Use JobAgent to create the job (handles embedding generation)
            job = self.job_agent.create_job(job_data)
            
            logger.info(f"Stored scraped job: {job.title} ({job.id})")
            return job
            
        except Exception as e:
            logger.error(f"Failed to store scraped job: {e}")
            return None

    def _calculate_job_quality_score(self, job: ScrapedJob) -> float:
        """
        Calculate a quality score for a job to help rank top jobs.
        Higher score = better job quality.
        """
        score = 0.0
        
        # Has salary info (good signal)
        if job.salary_min or job.salary_max:
            score += 2.0
        
        # Has location info
        if job.location:
            score += 1.0
        
        # Remote work option (valuable)
        if job.is_remote:
            score += 1.5
        elif job.is_hybrid:
            score += 1.0
        
        # Has employment type specified
        if job.employment_type:
            score += 0.5
        
        # Has experience level specified
        if job.experience_level:
            score += 0.5
        
        # Recent posting (freshness)
        if job.posted_at:
            days_ago = (datetime.now() - job.posted_at).days
            if days_ago <= 7:
                score += 2.0  # Very fresh
            elif days_ago <= 30:
                score += 1.0  # Moderately fresh
        
        # Has detailed description
        if job.description and len(job.description) > 100:
            score += 1.0
        
        return score

    def scrape_and_store(
        self,
        keywords: List[str],
        location: Optional[str] = None,
        sources: Optional[List[str]] = None,
        max_results_per_source: int = 25,
        max_pages: int = 3,
        top_n: int = 10
    ) -> Dict:
        """
        Scrape jobs from multiple sources and store them.
        Scrapes up to max_pages from each source, then filters top N jobs.
        
        Args:
            keywords: List of job keywords to search
            location: Location filter
            sources: List of sources to scrape (linkedin, indeed, glassdoor, mock). Defaults to indeed, internshala.
            max_results_per_source: Maximum results per page
            max_pages: Maximum pages to scrape per source (default: 3)
            top_n: Number of top jobs to store after filtering (default: 10)
            
        Returns:
            Summary of scraping results
        """
        if sources is None:
            sources = ["indeed", "internshala"]  # Default to real job sources
        
        all_scraped_jobs: List[ScrapedJob] = []
        results_by_source: Dict[str, int] = {}
        
        logger.info(f"Starting job scraping for keywords: {keywords}, max_pages={max_pages}, top_n={top_n}")
        
        try:
            # Scrape from each source using Selenium (up to max_pages per source)
            for source in sources:
                scraped_jobs = []
                
                try:
                    if source == "linkedin":
                        scraped_jobs = self.scrape_linkedin_jobs(
                            keywords, location, max_results_per_source, max_pages
                        )
                    elif source == "indeed":
                        scraped_jobs = self.scrape_indeed_jobs(
                            keywords, location, max_results_per_source, max_pages
                        )
                    elif source == "glassdoor":
                        scraped_jobs = self.scrape_glassdoor_jobs(
                            keywords, location, max_results_per_source
                        )
                    elif source == "naukri":
                        scraped_jobs = self.scrape_naukri_jobs(
                            keywords, location, max_results_per_source, max_pages
                        )
                    elif source == "internshala":
                        scraped_jobs = self.scrape_internshala_jobs(
                            keywords, location, max_results_per_source, max_pages
                        )
                    elif source == "mock":
                        # Run async mock scraper in sync context
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            scraped_jobs = loop.run_until_complete(
                                self.scrape_mock_jobs(keywords, max_results_per_source)
                            )
                        finally:
                            loop.close()
                    
                    all_scraped_jobs.extend(scraped_jobs)
                    results_by_source[source] = len(scraped_jobs)
                    logger.info(f"Scraped {len(scraped_jobs)} jobs from {source}")
                    
                except Exception as e:
                    logger.error(f"Failed to scrape from {source}: {e}")
                    results_by_source[source] = 0
            
            # Remove duplicates from scraped jobs (by title + company)
            unique_jobs: List[ScrapedJob] = []
            seen = set()
            for job in all_scraped_jobs:
                key = f"{job.title.lower()}|{job.company_name.lower()}"
                if key not in seen:
                    seen.add(key)
                    unique_jobs.append(job)
            
            logger.info(f"Removed duplicates: {len(all_scraped_jobs)} -> {len(unique_jobs)} unique jobs")
            
            # Sort by quality score and select top N
            unique_jobs.sort(key=self._calculate_job_quality_score, reverse=True)
            top_jobs = unique_jobs[:top_n]
            
            logger.info(f"Selected top {len(top_jobs)} jobs from {len(unique_jobs)} unique jobs")
            
            # Store top jobs (synchronous - database operations)
            stored_count = 0
            duplicate_count = 0
            
            # Import Flask app here to ensure we have app context
            from flask import current_app
            
            # Check if we're in an app context, if not, we can't store jobs
            if not current_app:
                logger.error("No Flask application context available for storing jobs")
                return {
                    "success": False,
                    "error": "No Flask application context available",
                    "total_scraped": len(all_scraped_jobs),
                    "by_source": results_by_source,
                }
            
            for scraped_job in top_jobs:
                try:
                    job = self.store_scraped_job(scraped_job)
                    if job:
                        stored_count += 1
                    else:
                        duplicate_count += 1
                except Exception as store_error:
                    logger.error(f"Failed to store job {scraped_job.title}: {store_error}")
                    duplicate_count += 1
            
            return {
                "success": True,
                "total_scraped": len(all_scraped_jobs),
                "unique_jobs": len(unique_jobs),
                "top_jobs_selected": len(top_jobs),
                "stored": stored_count,
                "duplicates": duplicate_count,
                "by_source": results_by_source,
            }
            
        except Exception as e:
            logger.error(f"Scraping failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "total_scraped": len(all_scraped_jobs),
                "by_source": results_by_source,
            }
        
        finally:
            # Close WebDriver
            self._close_driver()

    def close(self):
        """Close the scraping agent."""
        self._close_driver()


# Global instance
_scraping_agent = None


def get_scraping_agent() -> JobScrapingAgent:
    """Get or create JobScrapingAgent instance."""
    global _scraping_agent
    if _scraping_agent is None:
        _scraping_agent = JobScrapingAgent()
    return _scraping_agent
