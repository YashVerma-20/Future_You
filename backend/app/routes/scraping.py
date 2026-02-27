"""Job scraping routes."""
from flask import Blueprint, request, jsonify, current_app
from marshmallow import Schema, fields, validate
from datetime import datetime
import asyncio
import structlog

from app.middleware import jwt_required, admin_required, get_current_user
from app.agents.scraping_agent import get_scraping_agent
from app.models.resume import Resume

logger = structlog.get_logger()
scraping_bp = Blueprint('scraping', __name__)


# Schemas
class ScrapeJobsSchema(Schema):
    """Schema for scraping jobs."""
    keywords = fields.List(
        fields.String(validate=validate.Length(min=1, max=100)),
        required=True,
        validate=validate.Length(min=1, max=10)
    )
    location = fields.String(validate=validate.Length(max=255), allow_none=True)
    sources = fields.List(
        fields.String(validate=validate.OneOf(['linkedin', 'indeed', 'glassdoor', 'internshala', 'mock'])),
        missing=['indeed', 'internshala']
    )
    max_results_per_source = fields.Integer(
        validate=validate.Range(min=1, max=50),
        missing=25
    )


class TriggerScrapingSchema(Schema):
    """Schema for triggering automated scraping."""
    keywords = fields.List(
        fields.String(validate=validate.Length(min=1, max=100)),
        required=True
    )
    location = fields.String(validate=validate.Length(max=255), allow_none=True)


scrape_jobs_schema = ScrapeJobsSchema()
trigger_scraping_schema = TriggerScrapingSchema()


@scraping_bp.route('/scrape', methods=['POST'])
@jwt_required
@admin_required
def scrape_jobs():
    """
    Manually trigger job scraping from external sources.
    
    Request Body:
        {
            "keywords": ["python", "react", "data science"],
            "location": "San Francisco, CA",
            "sources": ["mock"],
            "max_results_per_source": 50
        }
    
    Returns:
        {
            "success": true,
            "data": {
                "total_scraped": 100,
                "stored": 85,
                "duplicates": 15,
                "by_source": {
                    "mock": 100
                }
            }
        }
    """
    json_data = request.get_json()
    
    if not json_data:
        return jsonify({
            'success': False,
            'error': 'No input data provided'
        }), 400
    
    # Validate input
    errors = scrape_jobs_schema.validate(json_data)
    if errors:
        return jsonify({
            'success': False,
            'error': 'Validation error',
            'details': errors
        }), 400
    
    keywords = json_data['keywords']
    location = json_data.get('location')
    sources = json_data.get('sources', ['mock'])
    max_results = json_data.get('max_results_per_source', 50)
    
    try:
        agent = get_scraping_agent()
        
        # Run synchronous scraping with Selenium
        result = agent.scrape_and_store(
            keywords=keywords,
            location=location,
            sources=sources,
            max_results_per_source=max_results
        )
        
        if result['success']:
            logger.info(
                f"Job scraping completed: {result['stored']} jobs stored",
                user_id=get_current_user().id if get_current_user() else None
            )
            
            return jsonify({
                'success': True,
                'data': result
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Scraping failed')
            }), 500
            
    except Exception as e:
        logger.error(f"Job scraping failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@scraping_bp.route('/status', methods=['GET'])
@jwt_required
def get_scraping_status():
    """
    Get the status of job scraping operations.
    
    Returns:
        {
            "success": true,
            "data": {
                "available_sources": ["mock", "linkedin", "indeed", "glassdoor"],
                "selenium_configured": true,
                "note": "Selenium-based scraping for LinkedIn, Indeed, and Glassdoor"
            }
        }
    """
    # Check if Selenium is available
    try:
        from selenium import webdriver
        selenium_available = True
    except ImportError:
        selenium_available = False
    
    return jsonify({
        'success': True,
        'data': {
            'available_sources': ['mock', 'linkedin', 'indeed', 'glassdoor', 'internshala'],
            'selenium_configured': selenium_available,
            'note': 'Selenium-based scraping for LinkedIn, Indeed, Glassdoor, and Internshala. Chrome browser required.'
        }
    }), 200


@scraping_bp.route('/demo', methods=['POST'])
@jwt_required
def scrape_demo_jobs():
    """
    Quick endpoint to scrape demo/mock jobs for testing.
    
    Request Body:
        {
            "keywords": ["python", "react"],
            "count": 10
        }
    
    Returns:
        {
            "success": true,
            "data": {
                "total_scraped": 10,
                "stored": 10,
                "duplicates": 0
            }
        }
    """
    json_data = request.get_json() or {}
    
    keywords = json_data.get('keywords', ['python', 'react', 'data science'])
    count = json_data.get('count', 10)
    
    try:
        agent = get_scraping_agent()
        
        result = agent.scrape_and_store(
            keywords=keywords,
            sources=['mock'],
            max_results_per_source=count
        )
        
        return jsonify({
            'success': True,
            'data': result
        }), 200
        
    except Exception as e:
        logger.error(f"Demo scraping failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Store scraping status for async operations
_scraping_status = {}

@scraping_bp.route('/scrape-for-me', methods=['POST'])
@jwt_required
def scrape_jobs_for_user():
    """
    Trigger job scraping based on user's resume skills and location.
    This endpoint returns immediately and processes scraping in background.
    
    Request Body (optional):
        {
            "max_results_per_source": 25,  # Optional, default 25
            "additional_keywords": ["AI", "machine learning"]  # Optional extra keywords
        }
    
    Returns:
        {
            "success": true,
            "data": {
                "message": "Scraping started",
                "scraping_id": "uuid",
                "estimated_time": "30-60 seconds"
            }
        }
    """
    import uuid
    
    user = get_current_user()
    scraping_id = str(uuid.uuid4())
    json_data = request.get_json() or {}
    
    try:
        # Get user's latest processed resume
        resume = (
            Resume.query
            .filter_by(user_id=user.id, processing_status='completed')
            .order_by(Resume.created_at.desc())
            .first()
        )
        
        if not resume:
            return jsonify({
                'success': False,
                'error': 'No processed resume found. Please upload and process a resume first.'
            }), 400
        
        # Extract keywords from resume skills
        keywords = []
        if resume.extracted_skills:
            for skill in resume.extracted_skills[:5]:
                skill_name = skill.get('normalized_name') or skill.get('name')
                if skill_name:
                    keywords.append(skill_name)
        
        # Add additional keywords if provided
        additional_keywords = json_data.get('additional_keywords', [])
        keywords.extend(additional_keywords)
        
        # Fallback keywords if no skills extracted
        if not keywords:
            keywords = ['software engineer', 'developer', 'programming']
        
        # Get user's location preference
        location = user.location
        
        # Determine sources based on location
        india_locations = [
            'india', 'bangalore', 'bengaluru', 'mumbai', 'delhi', 'pune', 
            'hyderabad', 'chennai', 'kolkata', 'gurgaon', 'gurugram', 'noida',
            'ahmedabad', 'jaipur', 'lucknow', 'kanpur', 'nagpur', 'indore',
            'thane', 'bhopal', 'visakhapatnam', 'vadodara', 'firozabad',
            'ludhiana', 'rajkot', 'agra', 'siliguri', 'durgapur', 'chandigarh',
            'coimbatore', 'mysore', 'trivandrum', 'kochi', 'goa'
        ]
        
        sources = ['indeed']
        is_india_location = False
        if location:
            location_lower = location.lower()
            is_india_location = any(india_loc in location_lower for india_loc in india_locations)
        
        if is_india_location:
            sources.append('naukri')
            if len(keywords) <= 2:
                sources.append('internshala')
        
        combined_query = ' '.join(keywords[:2]) if len(keywords) > 1 else keywords[0] if keywords else 'software engineer'
        
        # Store initial status
        _scraping_status[scraping_id] = {
            'status': 'in_progress',
            'user_id': user.id,
            'started_at': datetime.now().isoformat(),
            'result': None
        }
        
        # Start scraping in background thread with app context
        import threading
        app = current_app._get_current_object()
        
        def do_scraping():
            with app.app_context():
                try:
                    agent = get_scraping_agent()
                    result = agent.scrape_and_store(
                        keywords=[combined_query],
                        location=location,
                        sources=sources,
                        max_results_per_source=8,
                        max_pages=1,
                        top_n=8
                    )
                    
                    if result['success']:
                        result['combined_query_used'] = combined_query
                        result['skills_extracted'] = keywords
                        result['location_used'] = location
                    
                    _scraping_status[scraping_id] = {
                        'status': 'completed' if result['success'] else 'failed',
                        'user_id': user.id,
                        'completed_at': datetime.now().isoformat(),
                        'result': result
                    }
                    
                    logger.info(f"Background scraping completed for user {user.id}", scraping_id=scraping_id)
                except Exception as e:
                    logger.error(f"Background scraping failed: {e}", scraping_id=scraping_id)
                    _scraping_status[scraping_id] = {
                        'status': 'failed',
                        'user_id': user.id,
                        'completed_at': datetime.now().isoformat(),
                        'error': str(e)
                    }
        
        thread = threading.Thread(target=do_scraping)
        thread.daemon = True
        thread.start()
        
        logger.info(f"Started background scraping for user {user.id}", scraping_id=scraping_id)
        
        return jsonify({
            'success': True,
            'data': {
                'message': 'Scraping started',
                'scraping_id': scraping_id,
                'estimated_time': '30-60 seconds',
                'sources': sources,
                'query': combined_query
            }
        }), 200
            
    except Exception as e:
        logger.error(f"Failed to start scraping: {e}", user_id=user.id)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@scraping_bp.route('/scrape-status/<scraping_id>', methods=['GET'])
@jwt_required
def check_scraping_status(scraping_id):
    """
    Get the status of a scraping operation.
    
    Returns:
        {
            "success": true,
            "data": {
                "status": "in_progress|completed|failed",
                "result": { ... }  # Only present if completed
            }
        }
    """
    user = get_current_user()
    
    if scraping_id not in _scraping_status:
        return jsonify({
            'success': False,
            'error': 'Scraping ID not found'
        }), 404
    
    status_info = _scraping_status[scraping_id]
    
    # Ensure user can only access their own scraping status
    if status_info['user_id'] != user.id:
        return jsonify({
            'success': False,
            'error': 'Unauthorized'
        }), 403
    
    return jsonify({
        'success': True,
        'data': status_info
    }), 200
