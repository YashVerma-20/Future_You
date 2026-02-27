"""Firebase Admin SDK integration."""
import firebase_admin
from firebase_admin import credentials, auth
from firebase_admin.auth import UserNotFoundError, InvalidIdTokenError
from flask import current_app
import structlog

logger = structlog.get_logger()

# Global Firebase app instance
_firebase_app = None


def init_firebase():
    """Initialize Firebase Admin SDK."""
    global _firebase_app
    
    if _firebase_app is not None:
        return _firebase_app
    
    try:
        # Try to get existing app
        _firebase_app = firebase_admin.get_app()
    except ValueError:
        # Initialize new app
        config = current_app.config
        
        cred_dict = {
            "type": "service_account",
            "project_id": config.get('FIREBASE_PROJECT_ID'),
            "private_key": config.get('FIREBASE_PRIVATE_KEY'),
            "client_email": config.get('FIREBASE_CLIENT_EMAIL'),
            "token_uri": "https://oauth2.googleapis.com/token",
        }
        
        if not all([cred_dict['project_id'], cred_dict['private_key'], cred_dict['client_email']]):
            logger.warning("Firebase credentials not fully configured")
            return None
        
        cred = credentials.Certificate(cred_dict)
        _firebase_app = firebase_admin.initialize_app(cred)
        logger.info("Firebase Admin SDK initialized")
    
    return _firebase_app


def verify_id_token(id_token):
    """
    Verify Firebase ID token.
    
    Args:
        id_token: Firebase ID token from client
        
    Returns:
        dict: Decoded token claims
        
    Raises:
        InvalidIdTokenError: If token is invalid
    """
    init_firebase()
    try:
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token
    except InvalidIdTokenError as e:
        logger.warning(f"Invalid Firebase ID token: {e}")
        raise
    except Exception as e:
        logger.error(f"Error verifying Firebase token: {e}")
        raise


def get_user_by_email(email):
    """
    Get Firebase user by email.
    
    Args:
        email: User email address
        
    Returns:
        UserRecord or None
    """
    init_firebase()
    try:
        return auth.get_user_by_email(email)
    except UserNotFoundError:
        return None
    except Exception as e:
        logger.error(f"Error getting user by email: {e}")
        return None


def get_user_by_uid(uid):
    """
    Get Firebase user by UID.
    
    Args:
        uid: Firebase user UID
        
    Returns:
        UserRecord or None
    """
    init_firebase()
    try:
        return auth.get_user(uid)
    except UserNotFoundError:
        return None
    except Exception as e:
        logger.error(f"Error getting user by UID: {e}")
        return None


def create_user(email, password=None, phone=None, display_name=None):
    """
    Create a new Firebase user.
    
    Args:
        email: User email
        password: User password (optional)
        phone: User phone number (optional)
        display_name: User display name (optional)
        
    Returns:
        UserRecord
    """
    init_firebase()
    try:
        user_props = {
            'email': email,
            'email_verified': False,
            'disabled': False
        }
        
        if password:
            user_props['password'] = password
        if phone:
            user_props['phone_number'] = phone
        if display_name:
            user_props['display_name'] = display_name
        
        user = auth.create_user(**user_props)
        logger.info(f"Created Firebase user: {email}")
        return user
    except Exception as e:
        logger.error(f"Error creating Firebase user: {e}")
        raise


def generate_email_verification_link(email):
    """
    Generate email verification link.
    
    Args:
        email: User email
        
    Returns:
        str: Verification link
    """
    init_firebase()
    try:
        link = auth.generate_email_verification_link(email)
        return link
    except Exception as e:
        logger.error(f"Error generating verification link: {e}")
        raise


def generate_password_reset_link(email):
    """
    Generate password reset link.
    
    Args:
        email: User email
        
    Returns:
        str: Reset link
    """
    init_firebase()
    try:
        link = auth.generate_password_reset_link(email)
        return link
    except Exception as e:
        logger.error(f"Error generating password reset link: {e}")
        raise


def delete_user(uid):
    """
    Delete Firebase user.
    
    Args:
        uid: Firebase user UID
    """
    init_firebase()
    try:
        auth.delete_user(uid)
        logger.info(f"Deleted Firebase user: {uid}")
    except Exception as e:
        logger.error(f"Error deleting Firebase user: {e}")
        raise


def send_push_notification(token, title, body, data=None):
    """
    Send push notification via Firebase Cloud Messaging.
    
    Args:
        token: FCM device token
        title: Notification title
        body: Notification body
        data: Additional data payload (optional)
    """
    from firebase_admin import messaging
    
    init_firebase()
    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body
            ),
            data=data or {},
            token=token
        )
        
        response = messaging.send(message)
        logger.info(f"Sent FCM notification: {response}")
        return response
    except Exception as e:
        logger.error(f"Error sending FCM notification: {e}")
        raise
