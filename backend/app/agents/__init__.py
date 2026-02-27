"""Agents package."""
from app.agents.resume_agent import ResumeAgent, get_resume_agent
from app.agents.job_agent import JobAgent, get_job_agent
from app.agents.recommendation_agent import RecommendationAgent, get_recommendation_agent
from app.agents.scraping_agent import JobScrapingAgent, get_scraping_agent

__all__ = [
    'ResumeAgent', 'get_resume_agent',
    'JobAgent', 'get_job_agent',
    'RecommendationAgent', 'get_recommendation_agent',
    'JobScrapingAgent', 'get_scraping_agent',
]
