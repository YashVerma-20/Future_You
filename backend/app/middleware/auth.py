"""Authentication middleware."""
from functools import wraps
from flask import request, jsonify, g
from app.utils.jwt_handler import decode_token, get_token_from_header
from app.models.user import User
import structlog

logger = structlog.get_logger()


def jwt_required(f):
    """
    Decorator to protect routes with JWT authentication.
    
    Usage:
        @app.route('/protected')
        @jwt_required
        def protected_route():
            return jsonify({'message': 'Protected'})
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        token = get_token_from_header(auth_header)
        
        if not token:
            return jsonify({
                'error': 'Unauthorized',
                'message': 'Missing authorization token'
            }), 401
        
        try:
            payload = decode_token(token)
            
            # Check token type
            if payload.get('type') != 'access':
                return jsonify({
                    'error': 'Unauthorized',
                    'message': 'Invalid token type'
                }), 401
            
            # Get user from database
            user_id = payload.get('user_id')
            user = User.query.get(user_id)
            
            if not user:
                return jsonify({
                    'error': 'Unauthorized',
                    'message': 'User not found'
                }), 401
            
            if not user.is_active:
                return jsonify({
                    'error': 'Unauthorized',
                    'message': 'User account is deactivated'
                }), 401
            
            # Store user in Flask g object for access in route
            g.user = user
            g.user_id = user_id
            g.firebase_uid = payload.get('firebase_uid')
            
            return f(*args, **kwargs)
            
        except Exception as e:
            logger.warning(f"Token validation failed: {e}")
            return jsonify({
                'error': 'Unauthorized',
                'message': 'Invalid or expired token'
            }), 401
    
    return decorated_function


def optional_auth(f):
    """
    Decorator for optional authentication.
    If token is provided and valid, sets g.user.
    If not, continues without authentication.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        token = get_token_from_header(auth_header)
        
        g.user = None
        g.user_id = None
        g.firebase_uid = None
        
        if token:
            try:
                payload = decode_token(token)
                user_id = payload.get('user_id')
                user = User.query.get(user_id)
                
                if user and user.is_active:
                    g.user = user
                    g.user_id = user_id
                    g.firebase_uid = payload.get('firebase_uid')
            except Exception:
                pass  # Silently ignore invalid tokens for optional auth
        
        return f(*args, **kwargs)
    
    return decorated_function


def get_current_user():
    """
    Get current authenticated user.
    
    Returns:
        User: Current user or None
    """
    return getattr(g, 'user', None)


def get_current_user_id():
    """
    Get current user ID.
    
    Returns:
        str: User ID or None
    """
    return getattr(g, 'user_id', None)


def admin_required(f):
    """
    Decorator to restrict routes to admin users only.
    Must be used after @jwt_required.
    
    Usage:
        @app.route('/admin-only')
        @jwt_required
        @admin_required
        def admin_route():
            return jsonify({'message': 'Admin only'})
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        
        if not user:
            return jsonify({
                'error': 'Unauthorized',
                'message': 'Authentication required'
            }), 401
        
        # Check if user has admin role
        # Adjust this based on your User model's role field
        is_admin = getattr(user, 'is_admin', False) or getattr(user, 'role', None) == 'admin'
        
        if not is_admin:
            logger.warning(f"Admin access denied for user: {user.id}")
            return jsonify({
                'error': 'Forbidden',
                'message': 'Admin access required'
            }), 403
        
        return f(*args, **kwargs)
    
    return decorated_function
