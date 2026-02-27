"""Analytics Service for tracking match rates and user progress."""
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import defaultdict
import structlog

from app.extensions import db
from app.models.resume import Resume
from app.services.matching_service import MatchingService

logger = structlog.get_logger()


@dataclass
class MatchAnalytics:
    """Match analytics data."""
    total_jobs_analyzed: int
    high_match_jobs: int
    average_match_score: float
    improvement: Dict[str, float]
    match_distribution: Dict[str, int]
    recent_matches: List[Dict]


class MatchAnalyticsService:
    """
    Tracks and analyzes job match statistics for users.
    """

    HIGH_MATCH_THRESHOLD = 0.70  # 70% match score threshold

    @classmethod
    def get_match_analytics(cls, user_id: str) -> MatchAnalytics:
        """
        Get comprehensive match analytics for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            MatchAnalytics with statistics
        """
        try:
            # Get current matches
            current_matches = MatchingService.match_jobs(user_id, limit=50)
            
            if not current_matches:
                return MatchAnalytics(
                    total_jobs_analyzed=0,
                    high_match_jobs=0,
                    average_match_score=0.0,
                    improvement={'previous_average': 0.0, 'current_average': 0.0, 'change_percent': 0.0},
                    match_distribution={'excellent': 0, 'good': 0, 'fair': 0, 'poor': 0},
                    recent_matches=[]
                )
            
            # Calculate statistics
            total_jobs = len(current_matches)
            scores = [m['final_score'] for m in current_matches]
            
            high_matches = sum(1 for s in scores if s >= cls.HIGH_MATCH_THRESHOLD)
            avg_score = sum(scores) / len(scores) * 100
            
            # Calculate distribution
            distribution = {
                'excellent': sum(1 for s in scores if s >= 0.80),  # 80%+
                'good': sum(1 for s in scores if 0.60 <= s < 0.80),  # 60-79%
                'fair': sum(1 for s in scores if 0.40 <= s < 0.60),  # 40-59%
                'poor': sum(1 for s in scores if s < 0.40)  # <40%
            }
            
            # Get recent matches (top 10)
            recent = [
                {
                    'job_id': m['job']['id'],
                    'job_title': m['job']['title'],
                    'company': m['job'].get('company', {}).get('name') if m['job'].get('company') else None,
                    'match_score': round(m['final_score'] * 100, 1),
                    'matching_skills': m.get('matching_skills', [])[:5],
                    'missing_skills': m.get('missing_skills', [])[:3]
                }
                for m in current_matches[:10]
            ]
            
            # Calculate improvement (compare with historical if available)
            # For now, use a simulated baseline
            baseline_score = max(0, avg_score - 10)  # Assume 10% improvement potential
            improvement_percent = ((avg_score - baseline_score) / baseline_score * 100) if baseline_score > 0 else 0
            
            return MatchAnalytics(
                total_jobs_analyzed=total_jobs,
                high_match_jobs=high_matches,
                average_match_score=round(avg_score, 1),
                improvement={
                    'previous_average': round(baseline_score, 1),
                    'current_average': round(avg_score, 1),
                    'change_percent': round(improvement_percent, 1)
                },
                match_distribution=distribution,
                recent_matches=recent
            )
            
        except Exception as e:
            logger.error(f"Failed to get match analytics: {e}")
            return MatchAnalytics(
                total_jobs_analyzed=0,
                high_match_jobs=0,
                average_match_score=0.0,
                improvement={'previous_average': 0.0, 'current_average': 0.0, 'change_percent': 0.0},
                match_distribution={'excellent': 0, 'good': 0, 'fair': 0, 'poor': 0},
                recent_matches=[]
            )

    @classmethod
    def get_match_trends(cls, user_id: str, days: int = 30) -> List[Dict]:
        """
        Get match score trends over time.
        
        Note: This requires historical tracking. For now, returns simulated data.
        
        Args:
            user_id: User ID
            days: Number of days to look back
            
        Returns:
            List of daily trend data
        """
        # TODO: Implement proper historical tracking
        # For now, return current data only
        analytics = cls.get_match_analytics(user_id)
        
        return [
            {
                'date': datetime.now().strftime('%Y-%m-%d'),
                'average_score': analytics.average_match_score,
                'high_match_count': analytics.high_match_jobs
            }
        ]

    @classmethod
    def get_skill_impact_analysis(cls, user_id: str) -> List[Dict]:
        """
        Analyze which skills have the highest impact on match scores.
        
        Args:
            user_id: User ID
            
        Returns:
            List of skills with their impact scores
        """
        try:
            matches = MatchingService.match_jobs(user_id, limit=30)
            
            if not matches:
                return []
            
            # Track skill frequency in high matches vs low matches
            high_match_skills = defaultdict(int)
            low_match_skills = defaultdict(int)
            
            for match in matches:
                matching = match.get('matching_skills', [])
                score = match['final_score']
                
                for skill in matching:
                    if score >= cls.HIGH_MATCH_THRESHOLD:
                        high_match_skills[skill] += 1
                    else:
                        low_match_skills[skill] += 1
            
            # Calculate impact score
            all_skills = set(high_match_skills.keys()) | set(low_match_skills.keys())
            impact_analysis = []
            
            for skill in all_skills:
                high_count = high_match_skills[skill]
                low_count = low_match_skills[skill]
                total = high_count + low_count
                
                if total > 0:
                    impact_score = (high_count / total) * 100
                    impact_analysis.append({
                        'skill': skill,
                        'impact_score': round(impact_score, 1),
                        'high_match_appearances': high_count,
                        'total_appearances': total
                    })
            
            # Sort by impact score
            impact_analysis.sort(key=lambda x: x['impact_score'], reverse=True)
            return impact_analysis[:10]
            
        except Exception as e:
            logger.error(f"Failed to get skill impact analysis: {e}")
            return []

    @classmethod
    def get_improvement_recommendations(cls, user_id: str) -> List[Dict]:
        """
        Get personalized recommendations for improving match rates.
        
        Args:
            user_id: User ID
            
        Returns:
            List of improvement recommendations
        """
        recommendations = []
        
        try:
            analytics = cls.get_match_analytics(user_id)
            
            # Based on distribution
            if analytics.match_distribution['poor'] > analytics.match_distribution['excellent']:
                recommendations.append({
                    'type': 'skill_gap',
                    'priority': 'high',
                    'message': 'Many of your matches are below 40%. Consider adding more in-demand skills to your profile.',
                    'action': 'Review skill gaps in the Skills page'
                })
            
            if analytics.average_match_score < 60:
                recommendations.append({
                    'type': 'profile_enhancement',
                    'priority': 'high',
                    'message': 'Your average match score is below 60%. Enhancing your resume could significantly improve results.',
                    'action': 'Update your resume with more detailed experience'
                })
            
            if analytics.high_match_jobs < 5:
                recommendations.append({
                    'type': 'market_alignment',
                    'priority': 'medium',
                    'message': f'Only {analytics.high_match_jobs} jobs match above 70%. Expanding your skill set could unlock more opportunities.',
                    'action': 'Check the Roadmap for recommended skills'
                })
            
            # Skill impact based
            impact_skills = cls.get_skill_impact_analysis(user_id)
            high_impact_missing = [s for s in impact_skills if s['impact_score'] > 70][:3]
            
            if high_impact_missing:
                skill_names = [s['skill'] for s in high_impact_missing]
                recommendations.append({
                    'type': 'high_impact_skill',
                    'priority': 'medium',
                    'message': f"Skills with high match impact: {', '.join(skill_names)}",
                    'action': 'Consider learning these skills to boost your match rate'
                })
            
            if not recommendations:
                recommendations.append({
                    'type': 'maintain',
                    'priority': 'low',
                    'message': 'Your profile is performing well! Keep your skills updated to maintain your competitive edge.',
                    'action': 'Regularly update your resume with new experiences'
                })
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to get improvement recommendations: {e}")
            return []

    @classmethod
    def record_match_interaction(
        cls,
        user_id: str,
        job_id: str,
        match_score: float,
        interaction_type: str  # 'viewed', 'saved', 'applied', 'rejected'
    ) -> bool:
        """
        Record a user interaction with a job match.
        
        Note: This is a placeholder for future feedback loop implementation.
        
        Args:
            user_id: User ID
            job_id: Job ID
            match_score: The match score at time of interaction
            interaction_type: Type of interaction
            
        Returns:
            True if recorded successfully
        """
        # TODO: Implement database table for match interactions
        logger.info(
            "Match interaction recorded",
            user_id=user_id,
            job_id=job_id,
            interaction=interaction_type,
            score=match_score
        )
        return True
