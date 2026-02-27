"""Routes package."""
from app.routes.auth import auth_bp
from app.routes.resume import resume_bp
from app.routes.job import job_bp
from app.routes.recommendation import recommendation_bp

__all__ = ['auth_bp', 'resume_bp', 'job_bp', 'recommendation_bp']
