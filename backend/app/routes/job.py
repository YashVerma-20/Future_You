"""Job routes."""
from flask import Blueprint, jsonify, request
from marshmallow import Schema, fields, validate
from app.middleware import jwt_required, optional_auth
from app.services.job_service import JobService
import structlog

logger = structlog.get_logger()
job_bp = Blueprint('job', __name__)


# Schemas
class CreateJobSchema(Schema):
    """Schema for creating a job."""
    title = fields.String(required=True, validate=validate.Length(min=1, max=255))
    description = fields.String(required=True, validate=validate.Length(min=10))
    requirements = fields.String(allow_none=True)
    responsibilities = fields.String(allow_none=True)
    location = fields.String(allow_none=True)
    is_remote = fields.Boolean(missing=False)
    is_hybrid = fields.Boolean(missing=False)
    salary_min = fields.Integer(allow_none=True)
    salary_max = fields.Integer(allow_none=True)
    salary_currency = fields.String(missing='USD')
    employment_type = fields.String(allow_none=True)
    experience_level = fields.String(allow_none=True)
    company = fields.Dict(allow_none=True)


class UpdateJobSchema(Schema):
    """Schema for updating a job."""
    title = fields.String(validate=validate.Length(min=1, max=255))
    description = fields.String(validate=validate.Length(min=10))
    requirements = fields.String(allow_none=True)
    responsibilities = fields.String(allow_none=True)
    location = fields.String(allow_none=True)
    is_remote = fields.Boolean()
    is_hybrid = fields.Boolean()
    salary_min = fields.Integer(allow_none=True)
    salary_max = fields.Integer(allow_none=True)
    employment_type = fields.String(allow_none=True)
    experience_level = fields.String(allow_none=True)
    is_active = fields.Boolean()


create_job_schema = CreateJobSchema()
update_job_schema = UpdateJobSchema()


@job_bp.route('/search', methods=['GET'])
@optional_auth
def search_jobs():
    """
    Search jobs with filters.
    
    Query Parameters:
        - q: Search query
        - location: Location filter
        - employment_type: full-time, part-time, contract, internship
        - experience_level: entry, mid, senior, executive
        - is_remote: true/false
        - page: Page number (default: 1)
        - limit: Results per page (default: 20)
    
    Returns:
        {
            "jobs": [job_data],
            "pagination": {page, limit, total, pages}
        }
    """
    query = request.args.get('q', '')
    location = request.args.get('location')
    employment_type = request.args.get('employment_type')
    experience_level = request.args.get('experience_level')
    is_remote = request.args.get('is_remote')
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    
    # Convert is_remote to boolean
    if is_remote is not None:
        is_remote = is_remote.lower() == 'true'
    
    try:
        results = JobService.search_jobs(
            query=query,
            location=location,
            employment_type=employment_type,
            experience_level=experience_level,
            is_remote=is_remote,
            page=page,
            limit=limit
        )
        
        return jsonify({
            'success': True,
            'data': results
        }), 200
        
    except Exception as e:
        logger.error(f"Job search failed: {e}")
        return jsonify({
            'success': False,
            'error': 'Search failed'
        }), 500


@job_bp.route('/recent', methods=['GET'])
@optional_auth
def get_recent_jobs():
    """
    Get recent job postings.
    
    Query Parameters:
        - limit: Number of jobs to return (default: 10)
    
    Returns:
        {
            "jobs": [job_data]
        }
    """
    limit = request.args.get('limit', 10, type=int)
    
    try:
        jobs = JobService.get_recent_jobs(limit=limit)
        return jsonify({
            'success': True,
            'data': {
                'jobs': [job.to_dict() for job in jobs]
            }
        }), 200
    except Exception as e:
        logger.error(f"Failed to get recent jobs: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get jobs'
        }), 500


@job_bp.route('/<job_id>', methods=['GET'])
@optional_auth
def get_job(job_id):
    """
    Get job details.
    
    Returns:
        {
            "job": {job_data}
        }
    """
    try:
        job = JobService.get_job(job_id)
        if not job:
            return jsonify({
                'success': False,
                'error': 'Job not found'
            }), 404
        
        return jsonify({
            'success': True,
            'data': {
                'job': job.to_dict()
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to get job: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get job'
        }), 500


@job_bp.route('/', methods=['POST'])
@jwt_required
def create_job():
    """
    Create a new job posting.
    
    Request Body:
        {
            "title": "Job Title",
            "description": "Job description...",
            "requirements": "Requirements...",
            "responsibilities": "Responsibilities...",
            "location": "City, Country",
            "is_remote": false,
            "is_hybrid": true,
            "salary_min": 50000,
            "salary_max": 80000,
            "employment_type": "full-time",
            "experience_level": "mid",
            "company": {
                "name": "Company Name",
                "description": "...",
                "website": "..."
            }
        }
    
    Returns:
        {
            "job": {created_job_data}
        }
    """
    try:
        data = create_job_schema.load(request.get_json())
        job = JobService.create_job(data)
        
        return jsonify({
            'success': True,
            'data': {
                'job': job.to_dict()
            }
        }), 201
        
    except Exception as e:
        logger.error(f"Failed to create job: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


@job_bp.route('/<job_id>', methods=['PUT'])
@jwt_required
def update_job(job_id):
    """
    Update a job posting.
    
    Request Body:
        Same as create, but all fields optional
    
    Returns:
        {
            "job": {updated_job_data}
        }
    """
    try:
        data = update_job_schema.load(request.get_json())
        job = JobService.update_job(job_id, data)
        
        return jsonify({
            'success': True,
            'data': {
                'job': job.to_dict()
            }
        }), 200
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 404
    except Exception as e:
        logger.error(f"Failed to update job: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


@job_bp.route('/<job_id>', methods=['DELETE'])
@jwt_required
def delete_job(job_id):
    """
    Delete a job posting.
    
    Returns:
        {
            "message": "Job deleted successfully"
        }
    """
    try:
        JobService.delete_job(job_id)
        return jsonify({
            'success': True,
            'message': 'Job deleted successfully'
        }), 200
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 404
    except Exception as e:
        logger.error(f"Failed to delete job: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@job_bp.route('/companies', methods=['GET'])
@optional_auth
def get_companies():
    """
    Get all companies.
    
    Returns:
        {
            "companies": [company_data]
        }
    """
    try:
        companies = JobService.get_companies()
        return jsonify({
            'success': True,
            'data': {
                'companies': [c.to_dict() for c in companies]
            }
        }), 200
    except Exception as e:
        logger.error(f"Failed to get companies: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
