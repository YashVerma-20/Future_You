"""Recommendation routes."""
from flask import Blueprint, request, jsonify
from app.middleware import jwt_required, get_current_user
from app.services.recommendation_service import RecommendationService
from app.services.skill_analytics_service import SkillAnalyticsService
from app.services.domain_detection_service import DomainDetectionService
from app.services.seniority_service import SeniorityService
from app.services.profile_strength_service import ProfileStrengthService
from app.services.analytics_service import MatchAnalyticsService
from app.services.roadmap_service import RoadmapService
from app.models.resume import Resume
import structlog

logger = structlog.get_logger()
recommendation_bp = Blueprint('recommendation', __name__)


@recommendation_bp.route('/jobs', methods=['GET'])
@jwt_required
def get_job_recommendations():
    """
    Get personalized job recommendations for the current user.
    
    Query Parameters:
        - limit: Number of recommendations (default: 10)
    
    Returns:
        {
            "recommendations": [
                {
                    "job": {job_data},
                    "match_score": 85.5,
                    "explanation": "Why this job matches...",
                    "skill_gaps": {gap_analysis}
                }
            ]
        }
    """
    user = get_current_user()
    limit = request.args.get('limit', 10, type=int)
    
    try:
        recommendations = RecommendationService.get_job_recommendations(
            user_id=user.id,
            limit=limit
        )
        
        return jsonify({
            'success': True,
            'data': {
                'recommendations': recommendations,
                'user_id': user.id
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to get job recommendations: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@recommendation_bp.route('/skill-gaps', methods=['GET'])
@jwt_required
def get_skill_gaps():
    """
    Analyze skill gaps for a specific job.
    
    Query Parameters:
        - job_id: Job ID to analyze (required)
    
    Returns:
        {
            "job_id": "uuid",
            "job_title": "Job Title",
            "match_percentage": 75.0,
            "required_skills_count": 10,
            "matching_skills_count": 7,
            "missing_skills_count": 3,
            "matching_skills": [...],
            "missing_skills": [...]
        }
    """
    user = get_current_user()
    job_id = request.args.get('job_id')
    
    if not job_id:
        return jsonify({
            'success': False,
            'error': 'job_id is required'
        }), 400
    
    try:
        analysis = RecommendationService.analyze_skill_gaps(user.id, job_id)
        
        return jsonify({
            'success': True,
            'data': analysis
        }), 200
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 404
    except Exception as e:
        logger.error(f"Failed to analyze skill gaps: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@recommendation_bp.route('/learning-path', methods=['GET'])
@jwt_required
def get_learning_path():
    """
    Get personalized learning path for a target skill.
    
    Query Parameters:
        - skill_id: Target skill ID (required)
    
    Returns:
        {
            "learning_path": [
                {"id": "uuid", "name": "Skill Name", "category": "..."}
            ]
        }
    """
    user = get_current_user()
    skill_id = request.args.get('skill_id')
    
    if not skill_id:
        return jsonify({
            'success': False,
            'error': 'skill_id is required'
        }), 400
    
    try:
        learning_path = RecommendationService.get_learning_path(user.id, skill_id)
        
        return jsonify({
            'success': True,
            'data': {
                'learning_path': learning_path,
                'target_skill_id': skill_id
            }
        }), 200
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 404
    except Exception as e:
        logger.error(f"Failed to get learning path: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@recommendation_bp.route('/related-skills/<skill_id>', methods=['GET'])
@jwt_required
def get_related_skills(skill_id):
    """
    Get skills related to a specific skill.
    
    Query Parameters:
        - limit: Number of related skills (default: 5)
    
    Returns:
        {
            "related_skills": [
                {"skill_id": "uuid", "name": "...", "frequency": 10}
            ]
        }
    """
    limit = request.args.get('limit', 5, type=int)
    
    try:
        related_skills = RecommendationService.get_related_skills(skill_id, limit)
        
        return jsonify({
            'success': True,
            'data': {
                'skill_id': skill_id,
                'related_skills': related_skills
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to get related skills: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@recommendation_bp.route('/skill-stats/<skill_id>', methods=['GET'])
@jwt_required
def get_skill_statistics(skill_id):
    """
    Get statistics about a skill.
    
    Returns:
        {
            "skill_id": "uuid",
            "name": "Skill Name",
            "category": "...",
            "job_count": 50,
            "user_count": 120
        }
    """
    try:
        stats = RecommendationService.get_skill_statistics(skill_id)
        
        return jsonify({
            'success': True,
            'data': stats
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to get skill statistics: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


from app.services.matching_service import MatchingService


@recommendation_bp.route('/match-jobs', methods=['POST'])
@jwt_required
def match_jobs():
    """
    Semantic job matching using latest resume.

    Query Params:
        - limit (optional, default=10)
    """
    user = get_current_user()
    limit = request.args.get('limit', 10, type=int)

    try:
        results = MatchingService.match_jobs(
            user_id=user.id,
            limit=limit
        )

        return jsonify({
            "success": True,
            "data": {
                "matches": results,
                "total": len(results)
            }
        }), 200

    except ValueError as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400

    except Exception as e:
        logger.error(f"Job matching failed: {e}")
        return jsonify({
            "success": False,
            "error": "Matching failed"
        }), 500


@recommendation_bp.route('/domain', methods=['GET'])
@jwt_required
def get_domain():
    """
    Detect career domain from user's resume.
    
    Returns:
        {
            "primary_domain": "Machine Learning / AI",
            "confidence": 0.82,
            "secondary_domain": "Data Engineering",
            "secondary_confidence": 0.45,
            "all_scores": {...}
        }
    """
    user = get_current_user()
    
    try:
        # Get latest resume
        resume = (
            Resume.query
            .filter_by(user_id=user.id, processing_status='completed')
            .order_by(Resume.created_at.desc())
            .first()
        )
        
        if not resume or not resume.raw_text:
            return jsonify({
                'success': False,
                'error': 'No processed resume found. Please upload a resume first.'
            }), 404
        
        # Detect domain
        result = DomainDetectionService.detect_domain(resume.raw_text)
        
        if not result:
            return jsonify({
                'success': False,
                'error': 'Could not detect domain from resume'
            }), 500
        
        return jsonify({
            'success': True,
            'data': {
                'primary_domain': result.primary_domain,
                'primary_confidence': result.primary_confidence,
                'secondary_domain': result.secondary_domain,
                'secondary_confidence': result.secondary_confidence,
                'all_scores': result.all_scores
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to detect domain: {e}")
        return jsonify({
            'success': False,
            'error': 'Domain detection failed'
        }), 500


@recommendation_bp.route('/seniority', methods=['GET'])
@jwt_required
def get_seniority():
    """
    Detect seniority level from user's resume.
    
    Returns:
        {
            "seniority_level": "Mid-Level",
            "estimated_years": 3.2,
            "confidence": 0.85,
            "years_breakdown": {...}
        }
    """
    user = get_current_user()
    
    try:
        # Get latest resume
        resume = (
            Resume.query
            .filter_by(user_id=user.id, processing_status='completed')
            .order_by(Resume.created_at.desc())
            .first()
        )
        
        if not resume:
            return jsonify({
                'success': False,
                'error': 'No processed resume found. Please upload a resume first.'
            }), 404
        
        # Detect seniority
        result = SeniorityService.detect_seniority(resume)
        
        return jsonify({
            'success': True,
            'data': {
                'seniority_level': result.seniority_level,
                'estimated_years': result.estimated_years,
                'confidence': result.confidence,
                'years_breakdown': result.years_breakdown,
                'next_level': SeniorityService.get_next_career_level(result.seniority_level),
                'level_requirements': SeniorityService.get_level_requirements(result.seniority_level)
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to detect seniority: {e}")
        return jsonify({
            'success': False,
            'error': 'Seniority detection failed'
        }), 500


@recommendation_bp.route('/skill-gaps/market', methods=['GET'])
@jwt_required
def get_market_skill_gaps():
    """
    Get comprehensive skill gap analysis against market demand.
    
    Returns:
        {
            "market_demand": {...},
            "user_skills": [...],
            "skill_coverage": {...},
            "gaps": [...],
            "top_opportunities": [...]
        }
    """
    user = get_current_user()
    
    try:
        analysis = SkillAnalyticsService.get_skill_gap_analysis(user.id)
        
        return jsonify({
            'success': True,
            'data': analysis
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to get skill gap analysis: {e}")
        return jsonify({
            'success': False,
            'error': 'Skill gap analysis failed'
        }), 500


@recommendation_bp.route('/market-demand', methods=['GET'])
@jwt_required
def get_market_demand():
    """
    Get top demanded skills in the market.
    
    Query Parameters:
        - limit: Number of top skills (default: 20)
    
    Returns:
        {
            "top_skills": [
                {"skill": "python", "demand_percentage": 75.5, "job_count": 150}
            ]
        }
    """
    limit = request.args.get('limit', 20, type=int)
    
    try:
        top_skills = SkillAnalyticsService.get_top_demanded_skills(top_n=limit)
        
        return jsonify({
            'success': True,
            'data': {
                'top_skills': top_skills,
                'total_analyzed': len(top_skills)
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to get market demand: {e}")
        return jsonify({
            'success': False,
            'error': 'Market demand analysis failed'
        }), 500


@recommendation_bp.route('/profile-strength', methods=['GET'])
@jwt_required
def get_profile_strength():
    """
    Get dynamic profile strength score.
    
    Returns:
        {
            "profile_strength": 74,
            "improvement_potential": 26,
            "breakdown": {...},
            "suggestions": [...]
        }
    """
    user = get_current_user()
    
    try:
        result = ProfileStrengthService.calculate_strength(user.id)
        
        return jsonify({
            'success': True,
            'data': {
                'profile_strength': result.profile_strength,
                'improvement_potential': result.improvement_potential,
                'breakdown': result.breakdown,
                'suggestions': result.suggestions
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to get profile strength: {e}")
        return jsonify({
            'success': False,
            'error': 'Profile strength calculation failed'
        }), 500


@recommendation_bp.route('/analytics', methods=['GET'])
@jwt_required
def get_match_analytics():
    """
    Get match rate analytics for the user.
    
    Returns:
        {
            "total_jobs_analyzed": 150,
            "high_match_jobs": 23,
            "average_match_score": 68.5,
            "improvement": {...},
            "match_distribution": {...},
            "recent_matches": [...]
        }
    """
    user = get_current_user()
    
    try:
        analytics = MatchAnalyticsService.get_match_analytics(user.id)
        recommendations = MatchAnalyticsService.get_improvement_recommendations(user.id)
        
        return jsonify({
            'success': True,
            'data': {
                'total_jobs_analyzed': analytics.total_jobs_analyzed,
                'high_match_jobs': analytics.high_match_jobs,
                'average_match_score': analytics.average_match_score,
                'improvement': analytics.improvement,
                'match_distribution': analytics.match_distribution,
                'recent_matches': analytics.recent_matches,
                'recommendations': recommendations
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to get match analytics: {e}")
        return jsonify({
            'success': False,
            'error': 'Analytics retrieval failed'
        }), 500


@recommendation_bp.route('/roadmap', methods=['GET'])
@jwt_required
def get_career_roadmap():
    """
    Get personalized career roadmap.
    
    Returns:
        {
            "current_position": "Mid-Level in Machine Learning",
            "target_position": "Senior ML Engineer",
            "milestones": [...],
            "summary": "..."
        }
    """
    user = get_current_user()
    
    try:
        roadmap = RoadmapService.generate_roadmap(user.id)
        
        if not roadmap:
            return jsonify({
                'success': False,
                'error': 'Could not generate roadmap. Please upload a resume first.'
            }), 404
        
        return jsonify({
            'success': True,
            'data': {
                'current_position': roadmap.current_position,
                'target_position': roadmap.target_position,
                'current_domain': roadmap.current_domain,
                'estimated_timeline_months': roadmap.estimated_timeline_months,
                'summary': roadmap.summary,
                'milestones': [
                    {
                        'order': m.order,
                        'title': m.title,
                        'description': m.description,
                        'reason': m.reason,
                        'skills_to_acquire': m.skills_to_acquire,
                        'estimated_weeks': m.estimated_weeks,
                        'resources': m.resources,
                        'completion_criteria': m.completion_criteria
                    }
                    for m in roadmap.milestones
                ]
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to get career roadmap: {e}")
        return jsonify({
            'success': False,
            'error': 'Roadmap generation failed'
        }), 500


@recommendation_bp.route('/roadmap/summary', methods=['GET'])
@jwt_required
def get_roadmap_summary():
    """
    Get simplified roadmap summary for dashboard.
    
    Returns:
        {
            "available": true,
            "current_position": "...",
            "target_position": "...",
            "next_milestone": {...}
        }
    """
    user = get_current_user()
    
    try:
        summary = RoadmapService.get_roadmap_summary(user.id)
        
        return jsonify({
            'success': True,
            'data': summary
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to get roadmap summary: {e}")
        return jsonify({
            'success': False,
            'error': 'Roadmap summary failed'
        }), 500