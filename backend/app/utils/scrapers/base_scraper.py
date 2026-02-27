"""Base scraper interface."""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from datetime import datetime
import structlog

logger = structlog.get_logger()


class BaseScraper(ABC):
    """Base class for job scrapers."""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logger.bind(scraper=name)
    
    @abstractmethod
    def search_jobs(
        self,
        query: str,
        location: Optional[str] = None,
        page: int = 1,
        limit: int = 20
    ) -> List[Dict]:
        """
        Search for jobs.
        
        Args:
            query: Search query
            location: Location filter
            page: Page number
            limit: Results per page
            
        Returns:
            List of job dictionaries
        """
        pass
    
    @abstractmethod
    def get_job_details(self, job_id: str) -> Optional[Dict]:
        """
        Get detailed information about a specific job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            Job details dictionary or None
        """
        pass
    
    def normalize_job(self, raw_job: Dict) -> Dict:
        """
        Normalize raw job data to standard format.
        
        Args:
            raw_job: Raw job data from source
            
        Returns:
            Normalized job dictionary
        """
        return {
            'title': raw_job.get('title', ''),
            'company': {
                'name': raw_job.get('company', ''),
                'description': raw_job.get('company_description', ''),
                'website': raw_job.get('company_website', ''),
            },
            'description': raw_job.get('description', ''),
            'requirements': raw_job.get('requirements', ''),
            'responsibilities': raw_job.get('responsibilities', ''),
            'location': raw_job.get('location', ''),
            'is_remote': raw_job.get('is_remote', False),
            'is_hybrid': raw_job.get('is_hybrid', False),
            'salary_min': raw_job.get('salary_min'),
            'salary_max': raw_job.get('salary_max'),
            'salary_currency': raw_job.get('salary_currency', 'USD'),
            'employment_type': raw_job.get('employment_type', 'full-time'),
            'experience_level': raw_job.get('experience_level'),
            'source_url': raw_job.get('source_url', ''),
            'source_platform': self.name,
            'external_id': raw_job.get('id', ''),
            'posted_at': raw_job.get('posted_at'),
            'required_skills': raw_job.get('required_skills', []),
        }
    
    def validate_job(self, job: Dict) -> bool:
        """
        Validate job data.
        
        Args:
            job: Job dictionary
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = ['title', 'description']
        return all(job.get(field) for field in required_fields)
