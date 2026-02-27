"""Rule-based scoring engine for job-resume matching."""
import re
from typing import List, Dict, Optional
from dataclasses import dataclass

from .base_matcher import BaseMatcher, MatchResult
from resume.resume_model import Resume
from scrapers.base_scraper import JobPosting
from config import config
from utils import get_logger


@dataclass
class RuleWeights:
    """Weights for different matching rules."""
    skills: float = 0.40
    experience: float = 0.30
    education: float = 0.15
    location: float = 0.10
    job_type: float = 0.05


class RuleBasedMatcher(BaseMatcher):
    """
    Rule-based matcher using explicit matching rules.
    Good for interpretable, deterministic scoring.
    """
    
    def __init__(self, weights: RuleWeights = None):
        super().__init__("rule_based")
        self.logger = get_logger("rule_based_matcher")
        self.weights = weights or RuleWeights()
    
    def match(
        self,
        resume: Resume,
        job: JobPosting
    ) -> MatchResult:
        """
        Calculate match score using rule-based approach.
        """
        self.logger.debug(f"Matching resume to job: {job.title}")
        
        # Calculate individual component scores
        skill_score, matching_skills, missing_skills = self._calculate_skill_score(
            resume, job
        )
        
        experience_score = self._calculate_experience_score(resume, job)
        education_score = self._calculate_education_score(resume, job)
        location_score = self._calculate_location_score(resume, job)
        job_type_score = self._calculate_job_type_score(resume, job)
        
        # Calculate weighted overall score
        overall_score = (
            skill_score * self.weights.skills +
            experience_score * self.weights.experience +
            education_score * self.weights.education +
            location_score * self.weights.location +
            job_type_score * self.weights.job_type
        )
        
        # Generate explanation
        explanation = self._generate_explanation(
            skill_score,
            experience_score,
            matching_skills,
            missing_skills
        )
        
        return MatchResult(
            job_id=job.id,
            resume_id=str(id(resume)),
            overall_score=round(overall_score, 3),
            rule_based_score=round(overall_score, 3),
            skill_match_score=round(skill_score, 3),
            experience_match_score=round(experience_score, 3),
            education_match_score=round(education_score, 3),
            matching_skills=matching_skills,
            missing_skills=missing_skills,
            skill_gaps=missing_skills,
            explanation=explanation,
            matcher_version=self.version
        )
    
    def match_batch(
        self,
        resume: Resume,
        jobs: List[JobPosting]
    ) -> List[MatchResult]:
        """Match resume against multiple jobs."""
        results = []
        
        for job in jobs:
            result = self.match(resume, job)
            results.append(result)
        
        # Sort by overall score descending
        results.sort(key=lambda x: x.overall_score, reverse=True)
        
        return results
    
    def _calculate_skill_score(
        self,
        resume: Resume,
        job: JobPosting
    ) -> tuple:
        """
        Calculate skill match score.
        
        Returns:
            (score, matching_skills, missing_skills)
        """
        # Get skills from resume
        resume_skills = [s.name for s in resume.skills]
        
        # Also extract from raw text
        text_skills = self._extract_skills_from_text(resume.raw_text)
        resume_skills = list(set(resume_skills + text_skills))
        
        # Get job skills
        job_skills = job.skills_required or []
        if not job_skills:
            # Extract from job description
            job_skills = self._extract_skills_from_text(
                job.description + " " + " ".join(job.requirements)
            )
        
        return self._calculate_skill_match(resume_skills, job_skills)
    
    def _calculate_experience_score(
        self,
        resume: Resume,
        job: JobPosting
    ) -> float:
        """Calculate experience match score."""
        score = 0.5  # Default neutral score
        
        # Get resume experience years
        resume_years = resume.get_total_experience_years()
        
        # Try to extract years from job description
        job_years = self._extract_required_years(job.description)
        
        if job_years and resume_years:
            if resume_years >= job_years:
                score = 1.0
            elif resume_years >= job_years * 0.7:
                score = 0.8
            elif resume_years >= job_years * 0.5:
                score = 0.6
            else:
                score = 0.3
        
        # Check experience level match
        if job.experience_level:
            level_score = self._check_experience_level_match(
                resume, job.experience_level
            )
            score = (score + level_score) / 2
        
        return score
    
    def _calculate_education_score(
        self,
        resume: Resume,
        job: JobPosting
    ) -> float:
        """Calculate education match score."""
        # Default score if no education requirements
        score = 0.7
        
        # Check if job mentions education requirements
        job_text = job.description.lower()
        
        education_keywords = {
            'bachelor': ['bachelor', 'bs', 'ba', 'b.s.', 'b.a.'],
            'master': ['master', 'ms', 'ma', 'm.s.', 'm.a.', 'mba'],
            'phd': ['phd', 'ph.d', 'doctorate']
        }
        
        required_level = None
        for level, keywords in education_keywords.items():
            if any(kw in job_text for kw in keywords):
                required_level = level
                break
        
        if not required_level:
            return score
        
        # Check resume education
        if not resume.education:
            return 0.4
        
        # Find highest degree
        highest_level = 'none'
        for edu in resume.education:
            degree = edu.degree.lower()
            if any(kw in degree for kw in education_keywords['phd']):
                highest_level = 'phd'
                break
            elif any(kw in degree for kw in education_keywords['master']):
                highest_level = 'master'
            elif any(kw in degree for kw in education_keywords['bachelor']):
                if highest_level not in ['master', 'phd']:
                    highest_level = 'bachelor'
        
        # Score based on match
        level_order = ['none', 'bachelor', 'master', 'phd']
        required_idx = level_order.index(required_level)
        highest_idx = level_order.index(highest_level)
        
        if highest_idx >= required_idx:
            score = 1.0
        elif highest_idx == required_idx - 1:
            score = 0.6
        else:
            score = 0.3
        
        return score
    
    def _calculate_location_score(
        self,
        resume: Resume,
        job: JobPosting
    ) -> float:
        """Calculate location match score."""
        # If job is remote, full score
        if job.remote:
            return 1.0
        
        # If no location info, neutral
        if not job.location:
            return 0.7
        
        # Check if resume mentions location
        # This is a simplified check - in production, use structured location data
        job_location = job.location.lower()
        resume_text = resume.raw_text.lower()
        
        # Extract city/state from job location
        location_parts = job_location.replace(',', ' ').split()
        
        matches = sum(1 for part in location_parts if part in resume_text)
        
        if matches > 0:
            return 0.8 + (0.2 * matches / len(location_parts))
        
        return 0.5
    
    def _calculate_job_type_score(
        self,
        resume: Resume,
        job: JobPosting
    ) -> float:
        """Calculate job type match score."""
        if not job.job_type:
            return 0.7
        
        # Default to neutral
        return 0.7
    
    def _extract_required_years(self, text: str) -> Optional[int]:
        """Extract required years of experience from job text."""
        patterns = [
            r'(\d+)\+?\s*years?\s*(?:of\s*)?experience',
            r'(\d+)\+?\s*years?',
            r'minimum\s*(?:of\s*)?(\d+)\s*years?'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                return int(matches[0])
        
        return None
    
    def _check_experience_level_match(
        self,
        resume: Resume,
        job_level: str
    ) -> float:
        """Check if experience level matches."""
        level_order = ['Entry-Level', 'Junior', 'Mid-Level', 'Senior', 'Lead', 'Principal']
        
        job_level_normalized = job_level.lower()
        
        # Determine resume level from experience
        resume_years = resume.get_total_experience_years()
        
        if resume_years < 2:
            resume_level = 'entry-level'
        elif resume_years < 4:
            resume_level = 'junior'
        elif resume_years < 7:
            resume_level = 'mid-level'
        elif resume_years < 10:
            resume_level = 'senior'
        else:
            resume_level = 'lead'
        
        # Simple matching
        if resume_level in job_level_normalized:
            return 1.0
        
        # Check adjacent levels
        try:
            job_idx = next(i for i, l in enumerate(level_order) if l.lower() in job_level_normalized)
            resume_idx = next(i for i, l in enumerate(level_order) if l.lower() == resume_level)
            
            diff = abs(job_idx - resume_idx)
            if diff == 1:
                return 0.7
            elif diff == 2:
                return 0.4
        except:
            pass
        
        return 0.5
    
    def _generate_explanation(
        self,
        skill_score: float,
        experience_score: float,
        matching_skills: List[str],
        missing_skills: List[str]
    ) -> str:
        """Generate human-readable explanation."""
        parts = []
        
        if skill_score >= 0.8:
            parts.append(f"Strong skill match with {len(matching_skills)} matching skills.")
        elif skill_score >= 0.5:
            parts.append(f"Good skill match with {len(matching_skills)} matching skills.")
        else:
            parts.append(f"Limited skill match. Only {len(matching_skills)} skills align.")
        
        if missing_skills:
            parts.append(f"Missing skills: {', '.join(missing_skills[:5])}.")
        
        if experience_score >= 0.8:
            parts.append("Experience level is a strong match.")
        elif experience_score >= 0.5:
            parts.append("Experience level is acceptable.")
        else:
            parts.append("Experience level may not meet requirements.")
        
        return " ".join(parts)
