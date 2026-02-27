"""Recommendation service layer."""
from typing import Dict, List
import structlog

from app.agents.recommendation_agent import get_recommendation_agent
from app.utils.neo4j_client import neo4j_client

logger = structlog.get_logger()


class RecommendationService:
    """Service for handling recommendation business logic."""
    
    @staticmethod
    def get_job_recommendations(user_id: str, limit: int = 10) -> List[Dict]:
        """
        Get personalized job recommendations for a user.
        
        Args:
            user_id: User ID
            limit: Number of recommendations
            
        Returns:
            List of job recommendations
        """
        agent = get_recommendation_agent()
        return agent.get_recommendations(user_id, limit=limit)
    
    @staticmethod
    def analyze_skill_gaps(user_id: str, job_id: str) -> Dict:
        """
        Analyze skill gaps for a specific job.
        
        Args:
            user_id: User ID
            job_id: Job ID
            
        Returns:
            Skill gap analysis
        """
        agent = get_recommendation_agent()
        return agent.analyze_skill_gaps(user_id, job_id)
    
    @staticmethod
    def get_learning_path(user_id: str, target_skill_id: str) -> List[Dict]:
        """
        Get learning path for a target skill.
        
        Args:
            user_id: User ID
            target_skill_id: Target skill ID
            
        Returns:
            List of skills in learning path
        """
        agent = get_recommendation_agent()
        return agent.generate_learning_path(user_id, target_skill_id)
    
    @staticmethod
    def get_related_skills(skill_id: str, limit: int = 5) -> List[Dict]:
        """
        Get skills related to a given skill.
        
        Args:
            skill_id: Skill ID
            limit: Number of related skills
            
        Returns:
            List of related skills
        """
        return neo4j_client.find_related_skills(skill_id, limit=limit)
    
    @staticmethod
    def get_skill_statistics(skill_id: str) -> Dict:
        """
        Get statistics about a skill.
        
        Args:
            skill_id: Skill ID
            
        Returns:
            Skill statistics
        """
        return neo4j_client.get_skill_statistics(skill_id)
