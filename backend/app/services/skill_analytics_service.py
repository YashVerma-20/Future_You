"""Skill Analytics Service for market demand analysis and skill gap detection."""
from typing import Dict, List, Optional
from collections import Counter
from dataclasses import dataclass
import structlog

from app.extensions import db
from app.models.job import Job
from app.models.resume import Resume
from app.models.user import UserSkill

logger = structlog.get_logger()


@dataclass
class SkillGap:
    """Represents a skill gap with market context."""
    skill: str
    demand_percentage: float
    job_count: int
    priority: str  # 'high', 'medium', 'low'


class SkillAnalyticsService:
    """
    Analyzes skill demand in the job market and identifies user skill gaps.
    """

    @staticmethod
    def analyze_market_demand(limit: Optional[int] = None) -> Dict[str, dict]:
        """
        Analyze market demand for skills across all jobs.
        
        Args:
            limit: Maximum number of skills to return (default: all)
            
        Returns:
            Dictionary mapping skill names to demand statistics
        """
        try:
            # Get all active jobs with required skills
            jobs = Job.query.filter_by(is_active=True).all()
            total_jobs = len(jobs)

            if total_jobs == 0:
                return {}

            # Count skill occurrences
            skill_counter = Counter()
            for job in jobs:
                if job.required_skills:
                    # Normalize skill names
                    skills = [s.lower().strip() for s in job.required_skills]
                    skill_counter.update(skills)

            # Calculate demand percentages
            skill_demand = {}
            for skill, count in skill_counter.most_common(limit):
                percentage = round((count / total_jobs) * 100, 1)
                skill_demand[skill] = {
                    'demand_percentage': percentage,
                    'job_count': count,
                    'total_jobs': total_jobs
                }

            logger.info(
                "Market demand analysis complete",
                total_jobs=total_jobs,
                unique_skills=len(skill_counter)
            )

            return skill_demand

        except Exception as e:
            logger.error(f"Failed to analyze market demand: {e}")
            return {}

    @classmethod
    def get_top_demanded_skills(cls, top_n: int = 20) -> List[Dict]:
        """
        Get the top N most demanded skills.
        
        Args:
            top_n: Number of top skills to return
            
        Returns:
            List of skill demand dictionaries sorted by demand
        """
        demand = cls.analyze_market_demand(limit=top_n)
        return [
            {
                'skill': skill,
                **stats
            }
            for skill, stats in demand.items()
        ]

    @classmethod
    def get_user_skills(cls, user_id: str) -> set:
        """
        Get all skills for a user from both resume and user skills.
        
        Args:
            user_id: User ID
            
        Returns:
            Set of normalized skill names
        """
        user_skills = set()

        # Get skills from UserSkill model
        db_skills = UserSkill.query.filter_by(user_id=user_id).all()
        for us in db_skills:
            if us.skill:
                user_skills.add(us.skill.name.lower().strip())

        # Get skills from latest resume
        resume = (
            Resume.query
            .filter_by(user_id=user_id, processing_status='completed')
            .order_by(Resume.created_at.desc())
            .first()
        )

        if resume and resume.extracted_skills:
            for skill in resume.extracted_skills:
                name = skill.get('normalized_name', skill.get('name', ''))
                if name:
                    user_skills.add(name.lower().strip())

        return user_skills

    @classmethod
    def analyze_user_skill_gaps(
        cls,
        user_id: str,
        min_demand_threshold: float = 10.0
    ) -> List[SkillGap]:
        """
        Analyze skill gaps for a user based on market demand.
        
        Args:
            user_id: User ID
            min_demand_threshold: Minimum demand % to consider a skill
            
        Returns:
            List of SkillGap objects sorted by priority
        """
        try:
            # Get market demand
            market_demand = cls.analyze_market_demand()

            # Get user skills
            user_skills = cls.get_user_skills(user_id)

            # Find gaps
            gaps = []
            for skill, stats in market_demand.items():
                if stats['demand_percentage'] < min_demand_threshold:
                    continue

                if skill.lower() not in user_skills:
                    # Determine priority based on demand
                    demand = stats['demand_percentage']
                    if demand >= 50:
                        priority = 'high'
                    elif demand >= 25:
                        priority = 'medium'
                    else:
                        priority = 'low'

                    gaps.append(SkillGap(
                        skill=skill,
                        demand_percentage=demand,
                        job_count=stats['job_count'],
                        priority=priority
                    ))

            # Sort by demand percentage (highest first)
            gaps.sort(key=lambda x: x.demand_percentage, reverse=True)

            logger.info(
                "User skill gap analysis complete",
                user_id=user_id,
                gaps_found=len(gaps),
                user_skill_count=len(user_skills)
            )

            return gaps

        except Exception as e:
            logger.error(f"Failed to analyze user skill gaps: {e}")
            return []

    @classmethod
    def get_skill_gap_analysis(cls, user_id: str) -> Dict:
        """
        Get comprehensive skill gap analysis for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Complete skill gap analysis with market context
        """
        market_demand = cls.analyze_market_demand(limit=50)
        gaps = cls.analyze_user_skill_gaps(user_id)
        user_skills = cls.get_user_skills(user_id)

        # Calculate coverage
        high_demand_skills = [
            s for s, stats in market_demand.items()
            if stats['demand_percentage'] >= 20
        ]
        covered_skills = [s for s in high_demand_skills if s in user_skills]
        coverage_percentage = (
            round((len(covered_skills) / len(high_demand_skills)) * 100, 1)
            if high_demand_skills else 0
        )

        return {
            'market_demand': market_demand,
            'user_skills': list(user_skills),
            'skill_coverage': {
                'percentage': coverage_percentage,
                'covered_count': len(covered_skills),
                'total_high_demand': len(high_demand_skills)
            },
            'gaps': [
                {
                    'skill': gap.skill,
                    'demand_percentage': gap.demand_percentage,
                    'job_count': gap.job_count,
                    'priority': gap.priority
                }
                for gap in gaps[:20]  # Top 20 gaps
            ],
            'top_opportunities': [
                {
                    'skill': gap.skill,
                    'demand_percentage': gap.demand_percentage,
                    'potential_jobs': gap.job_count
                }
                for gap in gaps[:5]  # Top 5 opportunities
            ]
        }

    @classmethod
    def get_jobs_requiring_skill(cls, skill: str, limit: int = 10) -> List[Dict]:
        """
        Get jobs that require a specific skill.
        
        Args:
            skill: Skill name to search for
            limit: Maximum number of jobs to return
            
        Returns:
            List of job dictionaries
        """
        try:
            jobs = Job.query.filter_by(is_active=True).all()
            matching_jobs = []

            skill_lower = skill.lower()
            for job in jobs:
                if job.required_skills:
                    job_skills = [s.lower() for s in job.required_skills]
                    if skill_lower in job_skills:
                        matching_jobs.append(job.to_dict())
                        if len(matching_jobs) >= limit:
                            break

            return matching_jobs

        except Exception as e:
            logger.error(f"Failed to get jobs requiring skill: {e}")
            return []
