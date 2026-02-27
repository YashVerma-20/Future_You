"""JWT token handling utilities."""
import jwt
from datetime import datetime, timedelta
from flask import current_app
import structlog

logger = structlog.get_logger()


def generate_token(user_id, firebase_uid, email, expires_in_hours=24):
    """
    Generate JWT token for authenticated user.
    
    Args:
        user_id: Internal user ID
        firebase_uid: Firebase user UID
        email: User email
        expires_in_hours: Token expiration time in hours
        
    Returns:
        str: JWT token
    """
    payload = {
        'user_id': user_id,
        'firebase_uid': firebase_uid,
        'email': email,
        'exp': datetime.utcnow() + timedelta(hours=expires_in_hours),
        'iat': datetime.utcnow(),
        'type': 'access'
    }
    
    token = jwt.encode(
        payload,
        current_app.config['JWT_SECRET_KEY'],
        algorithm='HS256'
    )
    
    return token


def generate_refresh_token(user_id, expires_in_days=7):
    """
    Generate refresh token.
    
    Args:
        user_id: Internal user ID
        expires_in_days: Token expiration time in days
        
    Returns:
        str: Refresh token
    """
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(days=expires_in_days),
        'iat': datetime.utcnow(),
        'type': 'refresh'
    }
    
    token = jwt.encode(
        payload,
        current_app.config['JWT_SECRET_KEY'],
        algorithm='HS256'
    )
    
    return token


def decode_token(token):
    """
    Decode and validate JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        dict: Decoded token payload
        
    Raises:
        jwt.ExpiredSignatureError: If token has expired
        jwt.InvalidTokenError: If token is invalid
    """
    try:
        payload = jwt.decode(
            token,
            current_app.config['JWT_SECRET_KEY'],
            algorithms=['HS256']
        )
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("JWT token has expired")
        raise
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid JWT token: {e}")
        raise


def verify_token(token, token_type='access'):
    """
    Verify JWT token and check type.
    
    Args:
        token: JWT token string
        token_type: Expected token type ('access' or 'refresh')
        
    Returns:
        dict: Decoded token payload
        
    Raises:
        ValueError: If token type doesn't match
        jwt.InvalidTokenError: If token is invalid
    """
    payload = decode_token(token)
    
    if payload.get('type') != token_type:
        raise ValueError(f"Invalid token type. Expected {token_type}")
    
    return payload


def refresh_access_token(refresh_token):
    """
    Generate new access token using refresh token.
    
    Args:
        refresh_token: Refresh token string
        
    Returns:
        str: New access token
    """
    from app.models.user import User
    
    payload = verify_token(refresh_token, token_type='refresh')
    user_id = payload.get('user_id')
    
    # Get user from database
    user = User.query.get(user_id)
    if not user or not user.is_active:
        raise ValueError("User not found or inactive")
    
    # Generate new access token
    return generate_token(
        user_id=user.id,
        firebase_uid=user.firebase_uid,
        email=user.email
    )


def get_token_from_header(auth_header):
    """
    Extract token from Authorization header.
    
    Args:
        auth_header: Authorization header value
        
    Returns:
        str: Token string or None
    """
    if not auth_header:
        return None
    
    parts = auth_header.split()
    
    if len(parts) != 2:
        return None
    
    if parts[0].lower() != 'bearer':
        return None
    
    return parts[1]
