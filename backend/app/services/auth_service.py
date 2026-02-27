"""Authentication service layer."""
from datetime import datetime
from app.models.user import User
from app.extensions import db
from app.utils.firebase import verify_id_token, get_user_by_uid
from app.utils.jwt_handler import generate_token, generate_refresh_token
import structlog

logger = structlog.get_logger()


class AuthService:
    """Service for handling authentication business logic."""
    
    @staticmethod
    def authenticate_with_firebase(id_token):
        """
        Authenticate user with Firebase ID token.
        
        Args:
            id_token: Firebase ID token from client
            
        Returns:
            dict: Authentication result with tokens and user data
            
        Raises:
            ValueError: If authentication fails
        """
        try:
            # Verify Firebase token
            decoded_token = verify_id_token(id_token)
            firebase_uid = decoded_token.get('uid')
            email = decoded_token.get('email')
            
            if not firebase_uid or not email:
                raise ValueError("Invalid Firebase token: missing uid or email")
            
            # Get or create user in our database
            user = User.query.filter_by(firebase_uid=firebase_uid).first()
            
            if not user:
                # Create new user
                user = User(
                    firebase_uid=firebase_uid,
                    email=email,
                    display_name=decoded_token.get('name'),
                    photo_url=decoded_token.get('picture'),
                    is_email_verified=decoded_token.get('email_verified', False)
                )
                db.session.add(user)
                logger.info(f"Created new user: {email}")
            
            # Update last login
            user.last_login_at = datetime.utcnow()
            user.is_email_verified = decoded_token.get('email_verified', False)
            db.session.commit()
            
            # Generate tokens
            access_token = generate_token(
                user_id=user.id,
                firebase_uid=user.firebase_uid,
                email=user.email
            )
            refresh_token = generate_refresh_token(user_id=user.id)
            
            return {
                'access_token': access_token,
                'refresh_token': refresh_token,
                'user': user.to_dict()
            }
            
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            raise ValueError(f"Authentication failed: {str(e)}")
    
    @staticmethod
    def register_user(firebase_uid, email, display_name=None, phone=None, photo_url=None):
        """
        Register a new user after Firebase authentication.
        
        Args:
            firebase_uid: Firebase user UID
            email: User email
            display_name: User display name
            phone: User phone number
            photo_url: User profile photo URL
            
        Returns:
            User: Created user
            
        Raises:
            ValueError: If user already exists
        """
        # Check if user already exists
        existing = User.query.filter(
            db.or_(
                User.firebase_uid == firebase_uid,
                User.email == email
            )
        ).first()
        
        if existing:
            raise ValueError("User already exists")
        
        # Create new user
        user = User(
            firebase_uid=firebase_uid,
            email=email,
            display_name=display_name,
            phone=phone,
            photo_url=photo_url
        )
        
        db.session.add(user)
        db.session.commit()
        
        logger.info(f"Registered new user: {email}")
        return user
    
    @staticmethod
    def get_user_by_firebase_uid(firebase_uid):
        """
        Get user by Firebase UID.
        
        Args:
            firebase_uid: Firebase user UID
            
        Returns:
            User or None
        """
        return User.query.filter_by(firebase_uid=firebase_uid).first()
    
    @staticmethod
    def update_user_profile(user_id, **kwargs):
        """
        Update user profile.
        
        Args:
            user_id: User ID
            **kwargs: Fields to update
            
        Returns:
            User: Updated user
        """
        user = User.query.get(user_id)
        if not user:
            raise ValueError("User not found")
        
        allowed_fields = ['display_name', 'phone', 'photo_url', 'location', 'preferred_work_type']
        
        for field, value in kwargs.items():
            if field in allowed_fields and value is not None:
                setattr(user, field, value)
        
        db.session.commit()
        logger.info(f"Updated user profile: {user_id}")
        
        return user
    
    @staticmethod
    def deactivate_user(user_id):
        """
        Deactivate user account.
        
        Args:
            user_id: User ID
        """
        user = User.query.get(user_id)
        if not user:
            raise ValueError("User not found")
        
        user.is_active = False
        db.session.commit()
        
        logger.info(f"Deactivated user: {user_id}")
    
    @staticmethod
    def delete_user_account(user_id):
        """
        Delete user account completely.
        
        Args:
            user_id: User ID
        """
        from app.utils.firebase import delete_user as delete_firebase_user
        
        user = User.query.get(user_id)
        if not user:
            raise ValueError("User not found")
        
        # Delete from Firebase
        try:
            delete_firebase_user(user.firebase_uid)
        except Exception as e:
            logger.warning(f"Failed to delete Firebase user: {e}")
        
        # Delete from database
        user.delete()
        
        logger.info(f"Deleted user account: {user_id}")
