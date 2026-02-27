"""Resume routes."""
from flask import Blueprint, request, jsonify
from marshmallow import Schema, fields, validate
from app.middleware import jwt_required, get_current_user
from app.services.resume_service import ResumeService
from app.agents.resume_agent import get_resume_agent
import structlog

logger = structlog.get_logger()
resume_bp = Blueprint('resume', __name__)


# Schemas
class UpdateSkillsSchema(Schema):
    """Schema for updating skills."""
    skills = fields.List(fields.Dict(), required=True)


update_skills_schema = UpdateSkillsSchema()


@resume_bp.route('/upload', methods=['POST'])
@jwt_required
def upload_resume():
    """
    Upload and process resume.
    
    Request:
        multipart/form-data with 'file' field
    
    Returns:
        {
            "resume": {resume_data},
            "processing_result": {skills_extracted: N}
        }
    """
    user = get_current_user()
    
    if 'file' not in request.files:
        return jsonify({
            'success': False,
            'error': 'No file provided'
        }), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({
            'success': False,
            'error': 'No file selected'
        }), 400
    
    try:
        # Upload and save resume
        resume = ResumeService.upload_resume(user.id, file, file.filename)
        
        # Process resume (extract skills, generate embeddings)
        try:
            processing_result = ResumeService.process_resume(resume.id)
        except Exception as e:
            logger.error(f"Resume processing failed: {e}")
            processing_result = {'success': False, 'error': str(e)}
        
        return jsonify({
            'success': True,
            'data': {
                'resume': resume.to_dict(),
                'processing_result': processing_result
            }
        }), 201
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except Exception as e:
        logger.error(f"Resume upload failed: {e}")
        return jsonify({
            'success': False,
            'error': 'Upload failed'
        }), 500


@resume_bp.route('/', methods=['GET'])
@jwt_required
def get_resumes():
    """
    Get all user resumes.
    
    Returns:
        {
            "resumes": [resume_data]
        }
    """
    user = get_current_user()
    resumes = ResumeService.get_user_resumes(user.id)
    
    return jsonify({
        'success': True,
        'data': {
            'resumes': [r.to_dict() for r in resumes]
        }
    }), 200


@resume_bp.route('/<resume_id>', methods=['GET'])
@jwt_required
def get_resume(resume_id):
    """
    Get specific resume details.
    
    Returns:
        {
            "resume": {resume_data}
        }
    """
    user = get_current_user()
    
    try:
        resume = ResumeService.get_resume(resume_id, user.id)
        return jsonify({
            'success': True,
            'data': {
                'resume': resume.to_dict()
            }
        }), 200
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 404


@resume_bp.route('/<resume_id>', methods=['DELETE'])
@jwt_required
def delete_resume(resume_id):
    """
    Delete a resume.
    
    Returns:
        {
            "message": "Resume deleted"
        }
    """
    user = get_current_user()
    
    try:
        ResumeService.delete_resume(resume_id, user.id)
        return jsonify({
            'success': True,
            'message': 'Resume deleted successfully'
        }), 200
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 404


@resume_bp.route('/skills', methods=['GET'])
@jwt_required
def get_skills():
    """
    Get user skills.
    
    Returns:
        {
            "skills": [skill_data]
        }
    """
    user = get_current_user()
    return jsonify({
        'success': True,
        'data': {
            'skills': user.get_skills()
        }
    }), 200


@resume_bp.route('/skills', methods=['PUT'])
@jwt_required
def update_skills():
    """
    Update user skills manually.
    
    Request Body:
        {
            "skills": [
                {"skill_id": "uuid", "proficiency": 3}
            ]
        }
    
    Returns:
        {
            "skills": [updated_skill_data]
        }
    """
    user = get_current_user()
    
    try:
        data = update_skills_schema.load(request.get_json())
        updated_skills = ResumeService.update_user_skills(user.id, data['skills'])
        
        return jsonify({
            'success': True,
            'data': {
                'skills': [s.to_dict() for s in updated_skills]
            }
        }), 200
    except Exception as e:
        logger.error(f"Skills update failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


@resume_bp.route('/extract-text', methods=['POST'])
@jwt_required
def extract_text():
    """
    Extract text from resume without saving (for preview).
    
    Request:
        multipart/form-data with 'file' field
    
    Returns:
        {
            "text": "extracted text",
            "skills": [extracted_skills]
        }
    """
    if 'file' not in request.files:
        return jsonify({
            'success': False,
            'error': 'No file provided'
        }), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({
            'success': False,
            'error': 'No file selected'
        }), 400
    
    try:
        file_content = file.read()
        file_ext = file.filename.rsplit('.', 1)[1].lower()
        
        # Parse resume
        agent = get_resume_agent()
        parsed = agent.parse_resume(file_content, file_ext)
        
        # Extract skills
        skills = agent.extract_skills(parsed['text'])
        normalized_skills = agent.normalize_skills(skills)
        
        return jsonify({
            'success': True,
            'data': {
                'text': parsed['text'][:5000],  # Limit preview text
                'skills': normalized_skills[:20]  # Limit preview skills
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Text extraction failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
