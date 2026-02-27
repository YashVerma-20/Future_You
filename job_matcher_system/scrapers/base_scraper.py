"""Base scraper interface."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Dict
from datetime import datetime
import json
from pathlib import Path


@dataclass
class JobPosting:
    """Standardized job posting data structure."""
    id: str
    title: str
    company: str
    location: str
    description: str
    requirements: List[str]
    skills_required: List[str]
    experience_level: Optional[str] = None
    salary_range: Optional[str] = None
    job_type: Optional[str] = None  # full-time, part-time, contract
    remote: Optional[bool] = None
    posted_date: Optional[datetime] = None
    url: Optional[str] = None
    source: Optional[str] = None
    raw_text: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'title': self.title,
            'company': self.company,
            'location': self.location,
            'description': self.description,
            'requirements': self.requirements,
            'skills_required': self.skills_required,
            'experience_level': self.experience_level,
            'salary_range': self.salary_range,
            'job_type': self.job_type,
            'remote': self.remote,
            'posted_date': self.posted_date.isoformat() if self.posted_date else None,
            'url': self.url,
            'source': self.source,
            'raw_text': self.raw_text
        }
    
    def save(self, directory: Path):
        """Save job posting to file."""
        filepath = directory / f"{self.id}.json"
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)


class BaseJobScraper(ABC):
    """Abstract base class for job scrapers."""
    
    def __init__(self, source_name: str):
        self.source_name = source_name
        self.logger = None  # Set by concrete implementations
    
    @abstractmethod
    def search_jobs(
        self,
        query: str,
        location: Optional[str] = None,
        max_results: int = 10
    ) -> List[JobPosting]:
        """
        Search for jobs.
        
        Args:
            query: Job search query (e.g., "python developer")
            location: Optional location filter
            max_results: Maximum number of results to return
            
        Returns:
            List of JobPosting objects
        """
        pass
    
    @abstractmethod
    def get_job_details(self, job_id: str) -> Optional[JobPosting]:
        """
        Get detailed information about a specific job.
        
        Args:
            job_id: Unique job identifier
            
        Returns:
            JobPosting object or None if not found
        """
        pass
    
    def extract_skills_from_text(self, text: str) -> List[str]:
        """
        Extract skills from job description text.
        Override in subclasses for source-specific extraction.
        """
        # Basic implementation - can be enhanced
        common_skills = [
            'python', 'javascript', 'java', 'c++', 'c#', 'go', 'rust',
            'react', 'angular', 'vue', 'django', 'flask', 'fastapi',
            'sql', 'postgresql', 'mysql', 'mongodb', 'redis',
            'aws', 'azure', 'gcp', 'docker', 'kubernetes',
            'machine learning', 'data science', 'ai', 'nlp',
            'git', 'agile', 'scrum'
        ]
        
        text_lower = text.lower()
        found_skills = []
        
        for skill in common_skills:
            if skill in text_lower:
                found_skills.append(skill)
        
        return found_skills
