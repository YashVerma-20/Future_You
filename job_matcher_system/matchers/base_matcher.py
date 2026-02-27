"""Base matcher interface."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from datetime import datetime

from resume.resume_model import Resume
from scrapers.base_scraper import JobPosting


@dataclass
class MatchResult:
    """Result of a job-resume match."""
    job_id: str
    resume_id: str
    overall_score: float  # 0-1 scale
    
    # Component scores
    rule_based_score: Optional[float] = None
    tfidf_score: Optional[float] = None
    semantic_score: Optional[float] = None
    
    # Detailed breakdown
    skill_match_score: Optional[float] = None
    experience_match_score: Optional[float] = None
    education_match_score: Optional[float] = None
    
    # Matching details
    matching_skills: List[str] = None
    missing_skills: List[str] = None
    skill_gaps: List[str] = None
    
    # Explanation
    explanation: str = ""
    
    # Metadata
    matched_at: datetime = None
    matcher_version: str = "1.0"
    
    def __post_init__(self):
        if self.matched_at is None:
            self.matched_at = datetime.now()
        if self.matching_skills is None:
            self.matching_skills = []
        if self.missing_skills is None:
            self.missing_skills = []
        if self.skill_gaps is None:
            self.skill_gaps = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'job_id': self.job_id,
            'resume_id': self.resume_id,
            'overall_score': self.overall_score,
            'rule_based_score': self.rule_based_score,
            'tfidf_score': self.tfidf_score,
            'semantic_score': self.semantic_score,
            'skill_match_score': self.skill_match_score,
            'experience_match_score': self.experience_match_score,
            'education_match_score': self.education_match_score,
            'matching_skills': self.matching_skills,
            'missing_skills': self.missing_skills,
            'skill_gaps': self.skill_gaps,
            'explanation': self.explanation,
            'matched_at': self.matched_at.isoformat() if self.matched_at else None,
            'matcher_version': self.matcher_version
        }


class BaseMatcher(ABC):
    """Abstract base class for job-resume matchers."""
    
    def __init__(self, name: str):
        self.name = name
        self.version = "1.0"
    
    @abstractmethod
    def match(
        self,
        resume: Resume,
        job: JobPosting
    ) -> MatchResult:
        """
        Calculate match score between resume and job.
        
        Args:
            resume: Parsed resume
            job: Job posting
            
        Returns:
            MatchResult with scores and details
        """
        pass
    
    @abstractmethod
    def match_batch(
        self,
        resume: Resume,
        jobs: List[JobPosting]
    ) -> List[MatchResult]:
        """
        Match resume against multiple jobs.
        
        Args:
            resume: Parsed resume
            jobs: List of job postings
            
        Returns:
            List of MatchResult objects sorted by score
        """
        pass
    
    def _extract_skills_from_text(self, text: str) -> List[str]:
        """Extract skills from text."""
        # Common technical skills
        common_skills = [
            'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'go', 'rust',
            'ruby', 'php', 'swift', 'kotlin', 'scala', 'r', 'matlab',
            'react', 'angular', 'vue', 'svelte', 'next.js', 'django', 'flask',
            'fastapi', 'spring', 'express', 'nestjs',
            'sql', 'postgresql', 'mysql', 'mongodb', 'redis', 'elasticsearch',
            'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'terraform',
            'machine learning', 'deep learning', 'nlp', 'data science',
            'git', 'github', 'gitlab', 'jenkins', 'ci/cd',
            'agile', 'scrum', 'kanban'
        ]
        
        text_lower = text.lower()
        found_skills = []
        
        for skill in common_skills:
            if skill in text_lower:
                found_skills.append(skill)
        
        return found_skills
    
    def _calculate_skill_match(
        self,
        resume_skills: List[str],
        job_skills: List[str]
    ) -> tuple:
        """
        Calculate skill match metrics.
        
        Returns:
            (match_score, matching_skills, missing_skills)
        """
        if not job_skills:
            return 1.0, [], []
        
        resume_skills_lower = set(s.lower() for s in resume_skills)
        job_skills_lower = set(s.lower() for s in job_skills)
        
        matching = resume_skills_lower & job_skills_lower
        missing = job_skills_lower - resume_skills_lower
        
        match_score = len(matching) / len(job_skills_lower) if job_skills_lower else 1.0
        
        return match_score, list(matching), list(missing)
