"""Indeed job scraper implementation."""
import re
import hashlib
from typing import List, Optional
from urllib.parse import quote_plus
from datetime import datetime, timedelta

from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

from .selenium_scraper import SeleniumJobScraper, JobPosting


class IndeedScraper(SeleniumJobScraper):
    """
    Scraper for Indeed.com job listings.
    """
    
    BASE_URL = "https://www.indeed.com"
    
    def __init__(self):
        super().__init__("indeed")
    
    def _build_search_url(
        self,
        query: str,
        location: Optional[str] = None,
        start: int = 0
    ) -> str:
        """Build Indeed search URL."""
        encoded_query = quote_plus(query)
        url = f"{self.BASE_URL}/jobs?q={encoded_query}"
        
        if location:
            encoded_location = quote_plus(location)
            url += f"&l={encoded_location}"
        
        if start > 0:
            url += f"&start={start}"
        
        return url
    
    def _parse_job_card(self, card_element) -> Optional[JobPosting]:
        """Parse a single job card element."""
        try:
            # Extract job ID
            job_id = card_element.get_attribute('data-jk')
            if not job_id:
                # Try to extract from href
                link_elem = card_element.find_element(
                    By.CSS_SELECTOR, 
                    'a[data-jk]'
                )
                job_id = link_elem.get_attribute('data-jk')
            
            if not job_id:
                return None
            
            # Extract title
            try:
                title_elem = card_element.find_element(
                    By.CSS_SELECTOR,
                    'h2.jobTitle span[title]'
                )
                title = title_elem.get_attribute('title')
            except NoSuchElementException:
                title = "Unknown Title"
            
            # Extract company
            try:
                company_elem = card_element.find_element(
                    By.CSS_SELECTOR,
                    '[data-testid="company-name"]'
                )
                company = company_elem.text.strip()
            except NoSuchElementException:
                company = "Unknown Company"
            
            # Extract location
            try:
                location_elem = card_element.find_element(
                    By.CSS_SELECTOR,
                    '[data-testid="text-location"]'
                )
                location = location_elem.text.strip()
            except NoSuchElementException:
                location = "Unknown Location"
            
            # Extract salary if available
            salary_range = None
            try:
                salary_elem = card_element.find_element(
                    By.CSS_SELECTOR,
                    '[data-testid="job-salary"]'
                )
                salary_range = salary_elem.text.strip()
            except NoSuchElementException:
                pass
            
            # Check for remote
            remote = False
            try:
                metadata_elem = card_element.find_element(
                    By.CSS_SELECTOR,
                    '[data-testid="job-metadata"]'
                )
                if 'remote' in metadata_elem.text.lower():
                    remote = True
            except NoSuchElementException:
                pass
            
            # Build job posting (without full description)
            job = JobPosting(
                id=f"indeed_{job_id}",
                title=title,
                company=company,
                location=location,
                description="",  # Will be fetched separately
                requirements=[],
                skills_required=[],
                salary_range=salary_range,
                remote=remote,
                url=f"{self.BASE_URL}/viewjob?jk={job_id}",
                source="indeed"
            )
            
            return job
            
        except Exception as e:
            self.logger.warning(f"Failed to parse job card: {e}")
            return None
    
    def search_jobs(
        self,
        query: str,
        location: Optional[str] = None,
        max_results: int = 10
    ) -> List[JobPosting]:
        """
        Search for jobs on Indeed.
        """
        jobs = []
        start = 0
        page_size = 15  # Indeed shows 15 jobs per page
        
        while len(jobs) < max_results:
            url = self._build_search_url(query, location, start)
            
            if not self.get_page(url):
                break
            
            # Find job cards
            job_cards = self._safe_find_elements(
                By.CSS_SELECTOR,
                'div[data-testid="job-title"]'
            )
            
            if not job_cards:
                # Try alternative selector
                job_cards = self._safe_find_elements(
                    By.CSS_SELECTOR,
                    '.job_seen_beacon'
                )
            
            if not job_cards:
                self.logger.info("No more jobs found")
                break
            
            self.logger.info(f"Found {len(job_cards)} job cards on page")
            
            for card in job_cards:
                if len(jobs) >= max_results:
                    break
                
                job = self._parse_job_card(card)
                if job:
                    # Fetch full details
                    detailed_job = self.get_job_details(job.id.replace('indeed_', ''))
                    if detailed_job:
                        jobs.append(detailed_job)
                    else:
                        jobs.append(job)
                
                self._random_delay(1.0, 2.0)
            
            start += page_size
            self._random_delay(2.0, 4.0)
        
        self.logger.info(f"Total jobs collected: {len(jobs)}")
        return jobs[:max_results]
    
    def get_job_details(self, job_id: str) -> Optional[JobPosting]:
        """
        Get detailed job information.
        """
        try:
            url = f"{self.BASE_URL}/viewjob?jk={job_id}"
            
            if not self.get_page(url):
                return None
            
            self._random_delay(1.0, 2.0)
            
            # Extract description
            try:
                desc_elem = self._safe_find_element(
                    By.CSS_SELECTOR,
                    '#jobDescriptionText'
                )
                description = desc_elem.text if desc_elem else ""
            except:
                description = ""
            
            # Extract requirements from description
            requirements = self._extract_requirements(description)
            
            # Extract skills
            skills = self.extract_skills_from_text(description)
            
            # Detect experience level
            experience_level = self._detect_experience_level(description)
            
            # Create job posting
            job = JobPosting(
                id=f"indeed_{job_id}",
                title="",  # Would be filled from search results
                company="",
                location="",
                description=description,
                requirements=requirements,
                skills_required=skills,
                experience_level=experience_level,
                url=url,
                source="indeed",
                raw_text=description
            )
            
            return job
            
        except Exception as e:
            self.logger.error(f"Failed to get job details: {e}")
            return None
    
    def _extract_requirements(self, description: str) -> List[str]:
        """Extract requirements from job description."""
        requirements = []
        
        # Common patterns for requirements
        patterns = [
            r'(?:Requirements|Qualifications|What You Need|Must Have)[\s\S]*?(?=\n\n|\Z)',
            r'(?:Required Skills|Required Experience)[\s\S]*?(?=\n\n|\Z)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, description, re.IGNORECASE)
            for match in matches:
                # Split into bullet points
                bullets = re.split(r'[\n•\-]+', match)
                for bullet in bullets:
                    bullet = bullet.strip()
                    if bullet and len(bullet) > 10:
                        requirements.append(bullet)
        
        return requirements[:10]  # Limit to top 10
    
    def _detect_experience_level(self, description: str) -> Optional[str]:
        """Detect experience level from description."""
        text_lower = description.lower()
        
        # Keywords for each level
        levels = {
            'Senior': ['senior', 'sr.', '5+ years', '7+ years', '8+ years'],
            'Mid-Level': ['mid-level', 'intermediate', '3-5 years', '2-5 years'],
            'Junior': ['junior', 'jr.', 'entry level', '0-2 years', '1-2 years'],
            'Lead': ['lead', 'principal', 'staff', 'architect']
        }
        
        for level, keywords in levels.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return level
        
        return None
