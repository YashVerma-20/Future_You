"""User model."""
from app.extensions import db
from app.models.base import BaseModel


class User(BaseModel):
    """User model for storing user information."""
    
    __tablename__ = 'users'
    
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20), unique=True, nullable=True)
    firebase_uid = db.Column(db.String(128), unique=True, nullable=False, index=True)
    display_name = db.Column(db.String(255), nullable=True)
    photo_url = db.Column(db.String(500), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_email_verified = db.Column(db.Boolean, default=False, nullable=False)
    last_login_at = db.Column(db.DateTime, nullable=True)
    
    # Location for job matching
    location = db.Column(db.String(255), nullable=True)
    preferred_work_type = db.Column(db.String(50), nullable=True)  # remote, onsite, hybrid
    
    # Relationships
    resumes = db.relationship('Resume', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    user_skills = db.relationship('UserSkill', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<User {self.email}>'
    
    def to_dict(self):
        """Convert user to dictionary."""
        base_dict = super().to_dict()
        base_dict.update({
            'email': self.email,
            'phone': self.phone,
            'display_name': self.display_name,
            'photo_url': self.photo_url,
            'is_active': self.is_active,
            'is_email_verified': self.is_email_verified,
            'last_login_at': self.last_login_at.isoformat() if self.last_login_at else None,
            'location': self.location,
            'preferred_work_type': self.preferred_work_type
        })
        return base_dict
    
    def get_skills(self):
        """Get user skills with details."""
        return [us.to_dict() for us in self.user_skills]


class UserSkill(BaseModel):
    """User skill association model."""
    
    __tablename__ = 'user_skills'
    
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    skill_id = db.Column(db.String(36), db.ForeignKey('skills.id'), nullable=False)
    proficiency = db.Column(db.Integer, default=1)  # 1-5 scale
    is_verified = db.Column(db.Boolean, default=False)
    source = db.Column(db.String(50), default='manual')  # manual, resume, assessment
    
    # Relationship
    skill = db.relationship('Skill', backref='user_skills')
    
    def to_dict(self):
        """Convert user skill to dictionary."""
        base_dict = super().to_dict()
        base_dict.update({
            'user_id': self.user_id,
            'skill_id': self.skill_id,
            'skill_name': self.skill.name if self.skill else None,
            'proficiency': self.proficiency,
            'is_verified': self.is_verified,
            'source': self.source
        })
        return base_dict
