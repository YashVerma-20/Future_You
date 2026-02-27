"""Resume model."""
from app.extensions import db
from app.models.base import BaseModel


class Resume(BaseModel):
    """Resume model for storing user resume information."""
    
    __tablename__ = 'resumes'
    
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False, index=True)
    file_url = db.Column(db.String(500), nullable=False)
    file_name = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(50), nullable=False)  # pdf, docx, doc
    file_size = db.Column(db.Integer, nullable=False)  # in bytes
    
    # Parsed data
    parsed_data = db.Column(db.JSON, default=dict)
    raw_text = db.Column(db.Text, nullable=True)
    
    # Processing status
    processing_status = db.Column(db.String(50), default='pending')  # pending, processing, completed, failed
    processing_error = db.Column(db.Text, nullable=True)
    
    # Extracted information
    extracted_skills = db.Column(db.JSON, default=list)
    extracted_experience = db.Column(db.JSON, default=list)
    extracted_education = db.Column(db.JSON, default=list)
    
    def __repr__(self):
        return f'<Resume {self.file_name}>'
    
    def to_dict(self):
        """Convert resume to dictionary."""
        base_dict = super().to_dict()
        base_dict.update({
            'user_id': self.user_id,
            'file_url': self.file_url,
            'file_name': self.file_name,
            'file_type': self.file_type,
            'file_size': self.file_size,
            'processing_status': self.processing_status,
            'extracted_skills': self.extracted_skills,
            'extracted_experience': self.extracted_experience,
            'extracted_education': self.extracted_education,
        })
        return base_dict
