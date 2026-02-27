"""Manager for coordinating multiple scrapers."""
from typing import List, Dict, Optional
from pathlib import Path
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

from .base_scraper import BaseJobScraper, JobPosting
from .indeed_scraper import IndeedScraper
from utils import get_logger
from config import config


class ScraperManager:
    """
    Manages multiple job scrapers and aggregates results.
    """
    
    def __init__(self, jobs_dir: Path = None):
        self.logger = get_logger("scraper_manager")
        self.jobs_dir = jobs_dir or config.paths.jobs_dir
        self.scrapers: Dict[str, BaseJobScraper] = {}
        self._register_default_scrapers()
    
    def _register_default_scrapers(self):
        """Register default scrapers."""
        # Register Indeed scraper
        try:
            self.register_scraper("indeed", IndeedScraper())
        except Exception as e:
            self.logger.warning(f"Failed to register Indeed scraper: {e}")
        
        # Add more scrapers here as they're implemented
        # self.register_scraper("linkedin", LinkedInScraper())
        # self.register_scraper("glassdoor", GlassdoorScraper())
    
    def register_scraper(self, name: str, scraper: BaseJobScraper):
        """Register a new scraper."""
        self.scrapers[name] = scraper
        self.logger.info(f"Registered scraper: {name}")
    
    def search_all(
        self,
        query: str,
        location: Optional[str] = None,
        max_results_per_source: int = 10,
        sources: List[str] = None
    ) -> List[JobPosting]:
        """
        Search across all enabled scrapers.
        
        Args:
            query: Job search query
            location: Optional location
            max_results_per_source: Max results from each source
            sources: Specific sources to use (None = all)
            
        Returns:
            Combined list of job postings
        """
        all_jobs = []
        sources_to_use = sources or list(self.scrapers.keys())
        
        for source_name in sources_to_use:
            if source_name not in self.scrapers:
                self.logger.warning(f"Unknown scraper: {source_name}")
                continue
            
            scraper = self.scrapers[source_name]
            
            try:
                self.logger.info(f"Searching {source_name}...")
                jobs = scraper.search_jobs(
                    query=query,
                    location=location,
                    max_results=max_results_per_source
                )
                
                self.logger.info(f"Found {len(jobs)} jobs from {source_name}")
                all_jobs.extend(jobs)
                
            except Exception as e:
                self.logger.error(f"Error scraping {source_name}: {e}")
        
        # Deduplicate by job ID
        seen_ids = set()
        unique_jobs = []
        
        for job in all_jobs:
            if job.id not in seen_ids:
                seen_ids.add(job.id)
                unique_jobs.append(job)
        
        self.logger.info(f"Total unique jobs: {len(unique_jobs)}")
        return unique_jobs
    
    def search_parallel(
        self,
        query: str,
        location: Optional[str] = None,
        max_results_per_source: int = 10,
        sources: List[str] = None,
        max_workers: int = 3
    ) -> List[JobPosting]:
        """
        Search across sources in parallel.
        
        Note: Use with caution as parallel scraping may trigger rate limits.
        """
        all_jobs = []
        sources_to_use = sources or list(self.scrapers.keys())
        
        def scrape_source(source_name: str) -> List[JobPosting]:
            scraper = self.scrapers.get(source_name)
            if not scraper:
                return []
            
            try:
                return scraper.search_jobs(
                    query=query,
                    location=location,
                    max_results=max_results_per_source
                )
            except Exception as e:
                self.logger.error(f"Error in {source_name}: {e}")
                return []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(scrape_source, source): source
                for source in sources_to_use
            }
            
            for future in as_completed(futures):
                source_name = futures[future]
                try:
                    jobs = future.result()
                    all_jobs.extend(jobs)
                    self.logger.info(f"Completed {source_name}: {len(jobs)} jobs")
                except Exception as e:
                    self.logger.error(f"Future error for {source_name}: {e}")
        
        # Deduplicate
        seen_ids = set()
        unique_jobs = []
        
        for job in all_jobs:
            if job.id not in seen_ids:
                seen_ids.add(job.id)
                unique_jobs.append(job)
        
        return unique_jobs
    
    def save_jobs(self, jobs: List[JobPosting], filename: str = None):
        """Save jobs to disk."""
        if filename is None:
            from datetime import datetime
            filename = f"jobs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        filepath = self.jobs_dir / filename
        
        data = {
            'count': len(jobs),
            'jobs': [job.to_dict() for job in jobs]
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Saved {len(jobs)} jobs to {filepath}")
        return filepath
    
    def load_jobs(self, filename: str) -> List[JobPosting]:
        """Load jobs from disk."""
        filepath = self.jobs_dir / filename
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        jobs = []
        for job_data in data.get('jobs', []):
            # Convert posted_date string back to datetime
            if job_data.get('posted_date'):
                from datetime import datetime
                job_data['posted_date'] = datetime.fromisoformat(
                    job_data['posted_date']
                )
            
            job = JobPosting(**job_data)
            jobs.append(job)
        
        self.logger.info(f"Loaded {len(jobs)} jobs from {filepath}")
        return jobs
    
    def close_all(self):
        """Close all scrapers."""
        for name, scraper in self.scrapers.items():
            try:
                if hasattr(scraper, 'close'):
                    scraper.close()
                    self.logger.info(f"Closed scraper: {name}")
            except Exception as e:
                self.logger.error(f"Error closing {name}: {e}")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close_all()
        return False
