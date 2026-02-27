"""Job models."""
from app.extensions import db
from app.models.base import BaseModel


class Company(BaseModel):
    """Company model."""
    
    __tablename__ = 'companies'
    
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    industry = db.Column(db.String(100), nullable=True)
    size = db.Column(db.String(50), nullable=True)  # startup, small, medium, large, enterprise
    website = db.Column(db.String(500), nullable=True)
    logo_url = db.Column(db.String(500), nullable=True)
    location = db.Column(db.String(255), nullable=True)
    
    # Relationships
    jobs = db.relationship('Job', backref='company', lazy='dynamic')
    
    def __repr__(self):
        return f'<Company {self.name}>'
    
    def to_dict(self):
        """Convert company to dictionary."""
        base_dict = super().to_dict()
        base_dict.update({
            'name': self.name,
            'description': self.description,
            'industry': self.industry,
            'size': self.size,
            'website': self.website,
            'logo_url': self.logo_url,
            'location': self.location,
        })
        return base_dict


class Job(BaseModel):
    """Job posting model."""
    
    __tablename__ = 'jobs'
    
    title = db.Column(db.String(255), nullable=False, index=True)
    company_id = db.Column(db.String(36), db.ForeignKey('companies.id'), nullable=True)
    description = db.Column(db.Text, nullable=False)
    requirements = db.Column(db.Text, nullable=True)
    responsibilities = db.Column(db.Text, nullable=True)
    
    # Location
    location = db.Column(db.String(255), nullable=True)
    is_remote = db.Column(db.Boolean, default=False)
    is_hybrid = db.Column(db.Boolean, default=False)
    
    # Compensation
    salary_min = db.Column(db.Integer, nullable=True)
    salary_max = db.Column(db.Integer, nullable=True)
    salary_currency = db.Column(db.String(10), default='USD')
    salary_period = db.Column(db.String(20), default='yearly')  # hourly, monthly, yearly
    
    # Job details
    employment_type = db.Column(db.String(50), nullable=True)  # full-time, part-time, contract, internship
    experience_level = db.Column(db.String(50), nullable=True)  # entry, mid, senior, executive
    
    # Source
    source_url = db.Column(db.String(500), nullable=True)
    source_platform = db.Column(db.String(100), nullable=True)  # linkedin, indeed, etc.
    external_id = db.Column(db.String(255), nullable=True)
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    posted_at = db.Column(db.DateTime, nullable=True)
    expires_at = db.Column(db.DateTime, nullable=True)
    
    # Extracted data
    required_skills = db.Column(db.JSON, default=list)
    
    def __repr__(self):
        return f'<Job {self.title}>'
    
    def to_dict(self):
        """Convert job to dictionary."""
        base_dict = super().to_dict()
        base_dict.update({
            'title': self.title,
            'company': self.company.to_dict() if self.company else None,
            'description': self.description,
            'requirements': self.requirements,
            'responsibilities': self.responsibilities,
            'location': self.location,
            'is_remote': self.is_remote,
            'is_hybrid': self.is_hybrid,
            'salary_range': {
                'min': self.salary_min,
                'max': self.salary_max,
                'currency': self.salary_currency,
                'period': self.salary_period,
            } if self.salary_min or self.salary_max else None,
            'employment_type': self.employment_type,
            'experience_level': self.experience_level,
            'source_url': self.source_url,
            'source_platform': self.source_platform,
            'is_active': self.is_active,
            'posted_at': self.posted_at.isoformat() if self.posted_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'required_skills': self.required_skills,
        })
        return base_dict
