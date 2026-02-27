"""Authentication routes."""
from flask import Blueprint, request, jsonify
from marshmallow import Schema, fields, validate
from app.services.auth_service import AuthService
from app.utils.jwt_handler import refresh_access_token, verify_token
from app.middleware import jwt_required, get_current_user
from app.extensions import limiter
import structlog

logger = structlog.get_logger()
auth_bp = Blueprint('auth', __name__)


# Schemas
class FirebaseAuthSchema(Schema):
    """Schema for Firebase authentication."""
    id_token = fields.String(required=True, validate=validate.Length(min=10))


class RefreshTokenSchema(Schema):
    """Schema for token refresh."""
    refresh_token = fields.String(required=True, validate=validate.Length(min=10))


class UpdateProfileSchema(Schema):
    """Schema for profile update."""
    display_name = fields.String(validate=validate.Length(max=255), allow_none=True)
    phone = fields.String(validate=validate.Length(max=20), allow_none=True)
    photo_url = fields.String(validate=validate.Length(max=500), allow_none=True)
    location = fields.String(validate=validate.Length(max=255), allow_none=True)
    preferred_work_type = fields.String(
        validate=validate.OneOf(['remote', 'onsite', 'hybrid']),
        allow_none=True
    )


firebase_auth_schema = FirebaseAuthSchema()
refresh_token_schema = RefreshTokenSchema()
update_profile_schema = UpdateProfileSchema()


@auth_bp.route('/firebase', methods=['POST'])
@limiter.exempt
def firebase_auth():
    """
    Authenticate user with Firebase ID token.
    
    Request Body:
        {
            "id_token": "firebase_id_token_string"
        }
    
    Returns:
        {
            "access_token": "jwt_access_token",
            "refresh_token": "jwt_refresh_token",
            "user": {user_data}
        }
    """
    try:
        data = firebase_auth_schema.load(request.get_json())
        result = AuthService.authenticate_with_firebase(data['id_token'])
        
        logger.info(f"User authenticated: {result['user']['email']}")
        return jsonify({
            'success': True,
            'data': result
        }), 200
        
    except Exception as e:
        logger.warning(f"Firebase authentication failed: {e}")
        return jsonify({
            'success': False,
            'error': 'Authentication failed',
            'message': str(e)
        }), 401


@auth_bp.route('/refresh', methods=['POST'])
@limiter.limit("20 per minute")
def refresh_token():
    """
    Refresh access token using refresh token.
    
    Request Body:
        {
            "refresh_token": "jwt_refresh_token"
        }
    
    Returns:
        {
            "access_token": "new_jwt_access_token"
        }
    """
    try:
        data = refresh_token_schema.load(request.get_json())
        access_token = refresh_access_token(data['refresh_token'])
        
        return jsonify({
            'success': True,
            'data': {
                'access_token': access_token
            }
        }), 200
        
    except Exception as e:
        logger.warning(f"Token refresh failed: {e}")
        return jsonify({
            'success': False,
            'error': 'Token refresh failed',
            'message': str(e)
        }), 401


@auth_bp.route('/me', methods=['GET'])
@jwt_required
def get_current_user_info():
    """
    Get current authenticated user information.
    
    Returns:
        {
            "user": {user_data}
        }
    """
    user = get_current_user()
    return jsonify({
        'success': True,
        'data': {
            'user': user.to_dict()
        }
    }), 200


@auth_bp.route('/me', methods=['PUT'])
@jwt_required
def update_profile():
    """
    Update current user profile.
    
    Request Body:
        {
            "display_name": "John Doe",
            "phone": "+1234567890",
            "photo_url": "https://example.com/photo.jpg"
        }
    
    Returns:
        {
            "user": {updated_user_data}
        }
    """
    try:
        data = update_profile_schema.load(request.get_json())
        user = get_current_user()
        
        updated_user = AuthService.update_user_profile(
            user.id,
            **{k: v for k, v in data.items() if v is not None}
        )
        
        return jsonify({
            'success': True,
            'data': {
                'user': updated_user.to_dict()
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Profile update failed: {e}")
        return jsonify({
            'success': False,
            'error': 'Profile update failed',
            'message': str(e)
        }), 400


@auth_bp.route('/me', methods=['DELETE'])
@jwt_required
def delete_account():
    """
    Delete current user account.
    
    Returns:
        {
            "message": "Account deleted successfully"
        }
    """
    try:
        user = get_current_user()
        AuthService.delete_user_account(user.id)
        
        return jsonify({
            'success': True,
            'message': 'Account deleted successfully'
        }), 200
        
    except Exception as e:
        logger.error(f"Account deletion failed: {e}")
        return jsonify({
            'success': False,
            'error': 'Account deletion failed',
            'message': str(e)
        }), 400


@auth_bp.route('/verify-token', methods=['POST'])
def verify_token_endpoint():
    """
    Verify if a token is valid.
    
    Request Body:
        {
            "token": "jwt_token"
        }
    
    Returns:
        {
            "valid": true,
            "payload": {token_payload}
        }
    """
    try:
        token = request.get_json().get('token')
        if not token:
            return jsonify({
                'success': False,
                'valid': False,
                'message': 'Token is required'
            }), 400
        
        payload = verify_token(token)
        
        return jsonify({
            'success': True,
            'valid': True,
            'payload': payload
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': True,
            'valid': False,
            'message': str(e)
        }), 200
