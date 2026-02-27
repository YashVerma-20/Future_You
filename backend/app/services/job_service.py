"""Job service layer."""
from typing import Dict, List, Optional
import structlog

from app.extensions import db
from app.models.job import Job, Company
from app.agents.job_agent import get_job_agent

logger = structlog.get_logger()


class JobService:
    """Service for handling job business logic."""
    
    @staticmethod
    def create_job(job_data: Dict) -> Job:
        """
        Create a new job posting.
        
        Args:
            job_data: Job data dictionary
            
        Returns:
            Created Job object
        """
        agent = get_job_agent()
        return agent.create_job(job_data)
    
    @staticmethod
    def get_job(job_id: str) -> Optional[Job]:
        """
        Get a job by ID.
        
        Args:
            job_id: Job ID
            
        Returns:
            Job object or None
        """
        return Job.query.filter_by(id=job_id, is_active=True).first()
    
    @staticmethod
    def search_jobs(
        query: str,
        location: Optional[str] = None,
        employment_type: Optional[str] = None,
        experience_level: Optional[str] = None,
        is_remote: Optional[bool] = None,
        page: int = 1,
        limit: int = 20
    ) -> Dict:
        """
        Search jobs with filters.
        
        Args:
            query: Search query
            location: Location filter
            employment_type: Employment type filter
            experience_level: Experience level filter
            is_remote: Remote work filter
            page: Page number
            limit: Results per page
            
        Returns:
            Dictionary with jobs and pagination info
        """
        agent = get_job_agent()
        
        # Build filters
        filters = {}
        if employment_type:
            filters['employment_type'] = employment_type
        if experience_level:
            filters['experience_level'] = experience_level
        
        # Search by keywords
        results = agent.search_jobs_by_keywords(query, filters if filters else None)
        
        # Apply additional filters
        if location:
            results = [r for r in results if location.lower() in (r['job'].get('location') or '').lower()]
        
        if is_remote is not None:
            results = [r for r in results if r['job'].get('is_remote') == is_remote]
        
        # Pagination
        total = len(results)
        start = (page - 1) * limit
        end = start + limit
        paginated_results = results[start:end]
        
        return {
            'jobs': paginated_results,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total,
                'pages': (total + limit - 1) // limit
            }
        }
    
    @staticmethod
    def get_recent_jobs(limit: int = 10) -> List[Job]:
        """
        Get recent job postings.
        
        Args:
            limit: Number of jobs to return
            
        Returns:
            List of Job objects
        """
        return Job.query.filter_by(is_active=True).order_by(Job.created_at.desc()).limit(limit).all()
    
    @staticmethod
    def update_job(job_id: str, job_data: Dict) -> Job:
        """
        Update a job posting.
        
        Args:
            job_id: Job ID
            job_data: Updated job data
            
        Returns:
            Updated Job object
        """
        job = Job.query.get(job_id)
        if not job:
            raise ValueError("Job not found")
        
        # Update fields
        allowed_fields = [
            'title', 'description', 'requirements', 'responsibilities',
            'location', 'is_remote', 'is_hybrid', 'salary_min', 'salary_max',
            'employment_type', 'experience_level', 'is_active'
        ]
        
        for field in allowed_fields:
            if field in job_data:
                setattr(job, field, job_data[field])
        
        # Update skills if description changed
        if 'description' in job_data:
            agent = get_job_agent()
            processed = agent.process_job_description(job_data['description'])
            job.required_skills = processed['skill_names']
            
            # Update embedding
            embedding_text = f"{job.title} {processed['cleaned_description']} {' '.join(processed['skill_names'])}"
            embedding = agent.generate_embedding(embedding_text)
            agent.store_job_embedding(job.id, embedding)
            
            # Update Elasticsearch
            agent.index_job_in_elasticsearch(job)
        
        db.session.commit()
        logger.info(f"Updated job: {job_id}")
        
        return job
    
    @staticmethod
    def delete_job(job_id: str) -> None:
        """
        Soft delete a job posting.
        
        Args:
            job_id: Job ID
        """
        job = Job.query.get(job_id)
        if not job:
            raise ValueError("Job not found")
        
        job.is_active = False
        db.session.commit()
        
        logger.info(f"Deleted job: {job_id}")
    
    @staticmethod
    def get_companies() -> List[Company]:
        """
        Get all companies.
        
        Returns:
            List of Company objects
        """
        return Company.query.all()
    
    @staticmethod
    def get_company(company_id: str) -> Optional[Company]:
        """
        Get a company by ID.
        
        Args:
            company_id: Company ID
            
        Returns:
            Company object or None
        """
        return Company.query.get(company_id)
