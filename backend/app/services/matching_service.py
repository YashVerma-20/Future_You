"""Semantic Job Matching Service."""
from typing import List, Dict, Optional
from datetime import datetime, timezone
import structlog

from app.models.resume import Resume
from app.models.job import Job
from app.models.user import User
from app.agents.job_agent import get_job_agent
from app.extensions import db

logger = structlog.get_logger()


class MatchingService:
    """
    Handles semantic job matching using hybrid scoring:
    - Semantic similarity (60%)
    - Skill overlap (20%)
    - Freshness (10%)
    - Experience level match (10%)
    """

    # New weighted scoring formula
    SEMANTIC_WEIGHT = 0.6
    SKILL_WEIGHT = 0.2
    FRESHNESS_WEIGHT = 0.1
    EXPERIENCE_WEIGHT = 0.1

    # Experience level mapping
    EXPERIENCE_LEVELS = {
        'entry': 1,
        'junior': 2,
        'mid': 3,
        'mid-level': 3,
        'senior': 4,
        'lead': 5,
        'principal': 6,
        'executive': 7
    }

    @staticmethod
    def _get_latest_completed_resume(user_id: str) -> Resume:
        resume = (
            Resume.query
            .filter_by(user_id=user_id, processing_status='completed')
            .order_by(Resume.created_at.desc())
            .first()
        )

        if not resume:
            raise ValueError("No processed resume found. Please upload and process a resume first.")

        return resume

    @staticmethod
    def _calculate_skill_overlap(resume_skills: List[Dict], job_skills: List[str]) -> tuple[float, List[str], List[str]]:
        """
        Calculate skill overlap between resume and job.
        
        Returns:
            Tuple of (overlap_ratio, matching_skills, missing_skills)
        """
        if not job_skills:
            return 0.0, [], []

        resume_skill_names = {
            skill.get("normalized_name", "").lower()
            for skill in resume_skills
        }

        job_skill_set = {s.lower() for s in job_skills}

        matching = resume_skill_names.intersection(job_skill_set)
        missing = job_skill_set - resume_skill_names

        overlap_ratio = len(matching) / len(job_skill_set) if job_skill_set else 0.0

        return overlap_ratio, list(matching), list(missing)

    @classmethod
    def _calculate_freshness_score(cls, posted_at: Optional[datetime]) -> float:
        """
        Calculate freshness score based on job posting date.
        
        Score decreases linearly:
        - 0-7 days: 1.0 (perfect)
        - 8-30 days: 0.8 (good)
        - 31-60 days: 0.6 (fair)
        - 61-90 days: 0.4 (stale)
        - 90+ days: 0.2 (very stale)
        """
        if not posted_at:
            return 0.5  # Neutral score if no date

        now = datetime.now(timezone.utc)
        if posted_at.tzinfo is None:
            posted_at = posted_at.replace(tzinfo=timezone.utc)

        days_old = (now - posted_at).days

        if days_old <= 7:
            return 1.0
        elif days_old <= 30:
            return 0.8
        elif days_old <= 60:
            return 0.6
        elif days_old <= 90:
            return 0.4
        else:
            return 0.2

    @classmethod
    def _calculate_experience_match(
        cls,
        resume_experience: List[Dict],
        job_experience_level: Optional[str]
    ) -> tuple[float, str]:
        """
        Calculate experience level match score.
        
        Returns:
            Tuple of (match_score, alignment_description)
        """
        if not job_experience_level:
            return 0.5, "unknown"

        # Extract years from resume experience
        total_years = 0.0
        for exp in resume_experience:
            years = exp.get('years', 0)
            if years:
                total_years += years

        # Determine resume seniority level
        if total_years < 2:
            resume_level = 2  # junior
        elif total_years < 5:
            resume_level = 3  # mid-level
        elif total_years < 8:
            resume_level = 4  # senior
        else:
            resume_level = 5  # lead/principal

        # Parse job experience level
        job_level_str = job_experience_level.lower()
        job_level = 3  # default to mid-level
        for level_name, level_value in cls.EXPERIENCE_LEVELS.items():
            if level_name in job_level_str:
                job_level = level_value
                break

        # Calculate match
        level_diff = abs(resume_level - job_level)

        if level_diff == 0:
            return 1.0, "perfect"
        elif level_diff == 1:
            return 0.8, "strong"
        elif level_diff == 2:
            return 0.5, "moderate"
        else:
            return 0.2, "weak"

    @classmethod
    def _generate_explanation(
        cls,
        matching_skills: List[str],
        missing_skills: List[str],
        skill_overlap: float,
        experience_alignment: str,
        freshness_days: int
    ) -> str:
        """Generate human-readable explanation for the match."""
        parts = []

        # Skill match explanation
        if skill_overlap >= 0.7:
            parts.append("Excellent skill match")
        elif skill_overlap >= 0.5:
            parts.append("Good skill match")
        elif skill_overlap >= 0.3:
            parts.append("Moderate skill match")
        else:
            parts.append("Limited skill overlap")

        # Add matching skills detail
        if matching_skills:
            top_skills = matching_skills[:3]
            parts.append(f"with {', '.join(top_skills)}")

        # Experience alignment
        if experience_alignment == "perfect":
            parts.append("at your experience level")
        elif experience_alignment == "strong":
            parts.append("close to your experience level")

        # Missing skills warning
        if missing_skills:
            top_missing = missing_skills[:2]
            parts.append(f". Consider learning {', '.join(top_missing)}")

        # Freshness note
        if freshness_days <= 7:
            parts.append(". Posted recently")

        return "".join(parts)

    @classmethod
    def match_jobs(cls, user_id: str, limit: int = 10, respect_location: bool = True) -> List[Dict]:
        """
        Main matching pipeline with full explanation engine:
        1. Fetch latest resume and user preferences
        2. Generate embedding
        3. Vector search
        4. Hybrid scoring (semantic + skills + freshness + experience)
        5. Filter by location preferences
        6. Generate detailed explanations
        
        Args:
            user_id: User ID
            limit: Number of results to return
            respect_location: Whether to filter by user's location preference
        """

        resume = cls._get_latest_completed_resume(user_id)

        if not resume.raw_text:
            raise ValueError("Resume text not available.")

        # Get user preferences for location filtering
        user = User.query.get(user_id)
        user_location = user.location if user else None
        preferred_work_type = user.preferred_work_type if user else None

        job_agent = get_job_agent()

        # Generate resume embedding
        query_vector = job_agent.generate_embedding(resume.raw_text)

        # Step 1 — Vector similarity search (fetch extra for filtering)
        vector_results = job_agent.search_jobs_by_vector(
            query_vector=query_vector,
            limit=limit * 5  # fetch extra for filtering and reranking
        )

        # Filter by location preferences if enabled
        # PHASE 1: Only show India-based jobs
        INDIA_LOCATIONS = [
            'india', 'bangalore', 'bengaluru', 'mumbai', 'delhi', 'pune', 
            'hyderabad', 'chennai', 'kolkata', 'gurgaon', 'gurugram', 'noida',
            'ahmedabad', 'jaipur', 'lucknow', 'kanpur', 'nagpur', 'indore',
            'thane', 'bhopal', 'visakhapatnam', 'vadodara', 'firozabad',
            'ludhiana', 'rajkot', 'agra', 'siliguri', 'durgapur', 'chandigarh',
            'coimbatore', 'mysore', 'trivandrum', 'kochi', 'goa'
        ]
        
        if respect_location:
            filtered_results = []
            for result in vector_results:
                job_data = result["job"]
                job_obj = Job.query.get(job_data["id"])
                
                if not job_obj:
                    continue
                
                # Skip mock jobs - only show real jobs from Indeed/Internshala
                if job_obj.source_platform == 'mock':
                    continue
                
                # PHASE 1: Only show jobs in India
                job_location = (job_obj.location or '').lower()
                
                # Check if it's an India job or remote job
                is_india_job = any(loc in job_location for loc in INDIA_LOCATIONS)
                is_remote = job_obj.is_remote or 'remote' in job_location or 'work from home' in job_location
                
                # Accept jobs that are:
                # 1. Located in India, OR
                # 2. Marked as remote, OR  
                # 3. Have no location specified (assume India since we scraped from India-focused sources)
                if not job_location:
                    # Jobs with no location - assume India for India-focused platforms
                    if job_obj.source_platform in ['indeed', 'internshala', 'naukri']:
                        is_india_job = True
                
                # Internshala is India-focused, so all Internshala jobs are India jobs
                if job_obj.source_platform == 'internshala':
                    is_india_job = True
                
                if not (is_india_job or is_remote):
                    continue
                
                # Check work type preference
                if preferred_work_type:
                    if preferred_work_type == "remote" and not (job_obj.is_remote or job_obj.is_hybrid):
                        continue
                    if preferred_work_type == "onsite" and job_obj.is_remote:
                        continue
                    # hybrid matches hybrid or remote jobs
                
                # Check location match with user's preferred city
                if user_location and job_obj.location:
                    user_loc_lower = user_location.lower()
                    job_loc_lower = job_obj.location.lower()
                    
                    # Check for location match (exact or partial)
                    location_match = (
                        user_loc_lower in job_loc_lower or 
                        job_loc_lower in user_loc_lower or
                        job_obj.is_remote  # Remote jobs match any location
                    )
                    
                    if not location_match:
                        continue
                
                filtered_results.append(result)
            
            vector_results = filtered_results

        ranked_results = []

        for result in vector_results:
            job_data = result["job"]
            vector_score = result["score"]

            job_obj = Job.query.get(job_data["id"])
            job_skills = job_obj.required_skills or []

            # Calculate skill overlap with matching/missing skills
            skill_overlap, matching_skills, missing_skills = cls._calculate_skill_overlap(
                resume.extracted_skills or [],
                job_skills
            )

            # Calculate freshness score
            freshness_score = cls._calculate_freshness_score(job_obj.posted_at)
            
            # Calculate freshness days with timezone handling
            if job_obj.posted_at:
                now = datetime.now(timezone.utc)
                posted_at = job_obj.posted_at
                if posted_at.tzinfo is None:
                    posted_at = posted_at.replace(tzinfo=timezone.utc)
                freshness_days = (now - posted_at).days
            else:
                freshness_days = None

            # Calculate experience match
            experience_score, experience_alignment = cls._calculate_experience_match(
                resume.extracted_experience or [],
                job_obj.experience_level
            )

            # Calculate weighted final score
            final_score = (
                (vector_score * cls.SEMANTIC_WEIGHT) +
                (skill_overlap * cls.SKILL_WEIGHT) +
                (freshness_score * cls.FRESHNESS_WEIGHT) +
                (experience_score * cls.EXPERIENCE_WEIGHT)
            )

            # Generate explanation
            explanation = cls._generate_explanation(
                matching_skills=matching_skills,
                missing_skills=missing_skills,
                skill_overlap=skill_overlap,
                experience_alignment=experience_alignment,
                freshness_days=freshness_days or 0
            )

            ranked_results.append({
                "job": job_data,
                "final_score": round(final_score, 4),
                "breakdown": {
                    "semantic_score": round(vector_score, 4),
                    "skill_overlap": round(skill_overlap, 4),
                    "freshness_score": round(freshness_score, 4),
                    "experience_match": round(experience_score, 4)
                },
                "matching_skills": matching_skills,
                "missing_skills": missing_skills,
                "freshness_days": freshness_days,
                "experience_alignment": experience_alignment,
                "explanation": explanation
            })

        # Sort by final score
        ranked_results.sort(key=lambda x: x["final_score"], reverse=True)

        return ranked_results[:limit]