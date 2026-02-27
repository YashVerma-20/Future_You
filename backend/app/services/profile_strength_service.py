"""Profile Strength Service for calculating dynamic profile scores."""
from typing import Dict, List, Optional
from dataclasses import dataclass
import structlog

from app.models.resume import Resume
from app.models.user import UserSkill
from app.services.matching_service import MatchingService
from app.services.skill_analytics_service import SkillAnalyticsService
from app.services.domain_detection_service import DomainDetectionService

logger = structlog.get_logger()


@dataclass
class ProfileStrengthResult:
    """Result of profile strength calculation."""
    profile_strength: int
    improvement_potential: int
    breakdown: Dict[str, int]
    suggestions: List[str]


class ProfileStrengthService:
    """
    Calculates dynamic profile strength based on multiple factors:
    - Resume completeness (30%)
    - Skill coverage vs market (30%)
    - Match rate average (20%)
    - Market alignment (20%)
    """

    # Weight factors
    RESUME_WEIGHT = 0.30
    SKILL_COVERAGE_WEIGHT = 0.30
    MATCH_RATE_WEIGHT = 0.20
    MARKET_ALIGNMENT_WEIGHT = 0.20

    @classmethod
    def _calculate_resume_completeness(cls, resume: Resume) -> int:
        """
        Calculate resume completeness score (0-100).
        
        Factors:
        - Has raw text: 20 points
        - Has extracted skills: 20 points
        - Has experience entries: 20 points
        - Has education entries: 20 points
        - Parsed data present: 20 points
        """
        score = 0
        
        if resume.raw_text and len(resume.raw_text) > 100:
            score += 20
        
        if resume.extracted_skills and len(resume.extracted_skills) >= 3:
            score += 20
        
        if resume.extracted_experience and len(resume.extracted_experience) >= 1:
            score += 20
        
        if resume.extracted_education and len(resume.extracted_education) >= 1:
            score += 20
        
        if resume.parsed_data and len(resume.parsed_data) > 0:
            score += 20
        
        return score

    @classmethod
    def _calculate_skill_coverage(cls, user_id: str) -> int:
        """
        Calculate skill coverage against high-demand market skills.
        
        Returns percentage of high-demand skills the user has.
        """
        try:
            analysis = SkillAnalyticsService.get_skill_gap_analysis(user_id)
            return int(analysis.get('skill_coverage', {}).get('percentage', 0))
        except Exception as e:
            logger.error(f"Failed to calculate skill coverage: {e}")
            return 0

    @classmethod
    def _calculate_match_rate(cls, user_id: str) -> int:
        """
        Calculate average match rate from job recommendations.
        
        Returns average match score (0-100).
        """
        try:
            matches = MatchingService.match_jobs(user_id, limit=20)
            if not matches:
                return 0
            
            total_score = sum(m['final_score'] for m in matches)
            avg_score = (total_score / len(matches)) * 100
            return min(100, int(avg_score))
        except Exception as e:
            logger.error(f"Failed to calculate match rate: {e}")
            return 0

    @classmethod
    def _calculate_market_alignment(cls, user_id: str, resume: Resume) -> int:
        """
        Calculate market alignment score.
        
        Factors:
        - Domain detection confidence
        - Skill relevance to market
        """
        score = 50  # Base score
        
        try:
            # Domain confidence contributes up to 30 points
            if resume.raw_text:
                domain_result = DomainDetectionService.detect_domain(resume.raw_text)
                if domain_result:
                    score += int(domain_result.primary_confidence * 30)
            
            # Skill relevance contributes up to 20 points
            user_skills = SkillAnalyticsService.get_user_skills(user_id)
            if len(user_skills) >= 5:
                score += 20
            elif len(user_skills) >= 3:
                score += 10
            
            return min(100, score)
        except Exception as e:
            logger.error(f"Failed to calculate market alignment: {e}")
            return 50

    @classmethod
    def _generate_suggestions(
        cls,
        resume_score: int,
        skill_coverage: int,
        match_rate: int,
        market_alignment: int,
        gaps: List[Dict]
    ) -> List[str]:
        """Generate improvement suggestions based on scores."""
        suggestions = []
        
        if resume_score < 80:
            if resume_score < 60:
                suggestions.append("Add more detail to your resume - include project descriptions and achievements")
            else:
                suggestions.append("Consider adding more skills or education details to your resume")
        
        if skill_coverage < 50:
            top_gaps = [g['skill'] for g in gaps[:3]]
            if top_gaps:
                suggestions.append(f"High-demand skills to consider: {', '.join(top_gaps)}")
        
        if match_rate < 60:
            suggestions.append("Your match rate could improve - try adding more relevant skills to your profile")
        
        if market_alignment < 60:
            suggestions.append("Your profile alignment with market needs can be improved")
        
        if not suggestions:
            suggestions.append("Great profile! Keep your skills updated to maintain your competitive edge")
        
        return suggestions

    @classmethod
    def calculate_strength(cls, user_id: str) -> ProfileStrengthResult:
        """
        Calculate comprehensive profile strength.
        
        Args:
            user_id: User ID
            
        Returns:
            ProfileStrengthResult with score and breakdown
        """
        try:
            # Get latest resume
            resume = (
                Resume.query
                .filter_by(user_id=user_id, processing_status='completed')
                .order_by(Resume.created_at.desc())
                .first()
            )
            
            if not resume:
                return ProfileStrengthResult(
                    profile_strength=0,
                    improvement_potential=100,
                    breakdown={
                        'resume_completeness': 0,
                        'skill_coverage': 0,
                        'match_rate': 0,
                        'market_alignment': 0
                    },
                    suggestions=["Upload a resume to get your profile strength score"]
                )
            
            # Calculate individual scores
            resume_score = cls._calculate_resume_completeness(resume)
            skill_coverage = cls._calculate_skill_coverage(user_id)
            match_rate = cls._calculate_match_rate(user_id)
            market_alignment = cls._calculate_market_alignment(user_id, resume)
            
            # Calculate weighted final score
            final_score = (
                resume_score * cls.RESUME_WEIGHT +
                skill_coverage * cls.SKILL_COVERAGE_WEIGHT +
                match_rate * cls.MATCH_RATE_WEIGHT +
                market_alignment * cls.MARKET_ALIGNMENT_WEIGHT
            )
            
            final_score = int(final_score)
            improvement_potential = 100 - final_score
            
            # Get skill gaps for suggestions
            gaps = SkillAnalyticsService.analyze_user_skill_gaps(user_id)
            gap_dicts = [{'skill': g.skill, 'priority': g.priority} for g in gaps[:5]]
            
            suggestions = cls._generate_suggestions(
                resume_score, skill_coverage, match_rate, market_alignment, gap_dicts
            )
            
            return ProfileStrengthResult(
                profile_strength=final_score,
                improvement_potential=improvement_potential,
                breakdown={
                    'resume_completeness': resume_score,
                    'skill_coverage': skill_coverage,
                    'match_rate': match_rate,
                    'market_alignment': market_alignment
                },
                suggestions=suggestions
            )
            
        except Exception as e:
            logger.error(f"Failed to calculate profile strength: {e}")
            return ProfileStrengthResult(
                profile_strength=0,
                improvement_potential=100,
                breakdown={},
                suggestions=["Error calculating profile strength"]
            )

    @classmethod
    def get_strength_trend(cls, user_id: str) -> List[Dict]:
        """
        Get profile strength trend over time.
        
        Note: This is a placeholder for future implementation with history tracking.
        
        Args:
            user_id: User ID
            
        Returns:
            List of historical strength scores
        """
        # TODO: Implement history tracking in database
        # For now, return current score only
        current = cls.calculate_strength(user_id)
        return [
            {
                'date': 'current',
                'score': current.profile_strength,
                'breakdown': current.breakdown
            }
        ]
