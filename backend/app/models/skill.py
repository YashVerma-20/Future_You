"""Skill taxonomy model."""
from app.extensions import db
from app.models.base import BaseModel


class Skill(BaseModel):
    """Skill taxonomy model for normalized skills."""
    
    __tablename__ = 'skills'
    
    name = db.Column(db.String(100), nullable=False, index=True)
    normalized_name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    category = db.Column(db.String(50), nullable=True)  # technical, soft, domain, etc.
    description = db.Column(db.Text, nullable=True)
    aliases = db.Column(db.JSON, default=list)  # Alternative names for the skill
    parent_id = db.Column(db.String(36), db.ForeignKey('skills.id'), nullable=True)
    
    # Relationships
    parent = db.relationship('Skill', remote_side='Skill.id', backref='children')
    
    def __repr__(self):
        return f'<Skill {self.name}>'
    
    def to_dict(self):
        """Convert skill to dictionary."""
        base_dict = super().to_dict()
        base_dict.update({
            'name': self.name,
            'normalized_name': self.normalized_name,
            'category': self.category,
            'description': self.description,
            'aliases': self.aliases,
            'parent_id': self.parent_id
        })
        return base_dict
    
    @classmethod
    def find_by_name(cls, name):
        """Find skill by name (case-insensitive)."""
        normalized = name.lower().strip()
        return cls.query.filter(
            db.or_(
                cls.normalized_name == normalized,
                cls.name.ilike(f'%{name}%')
            )
        ).first()
    
    @classmethod
    def get_or_create(cls, name, category=None):
        """Get existing skill or create new one."""
        skill = cls.find_by_name(name)
        if skill:
            return skill
        
        normalized = name.lower().strip()
        skill = cls(
            name=name.strip(),
            normalized_name=normalized,
            category=category
        )
        skill.save()
        return skill
