"""Resume service layer."""
import os
import uuid
from typing import Dict, List
from werkzeug.utils import secure_filename
from flask import current_app
import structlog

from app.extensions import db
from app.models.resume import Resume
from app.models.user import UserSkill
from app.agents.resume_agent import get_resume_agent

logger = structlog.get_logger()


class ResumeService:
    """Service for handling resume business logic."""
    
    ALLOWED_EXTENSIONS = {'pdf', 'docx', 'doc'}
    MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB
    
    @staticmethod
    def allowed_file(filename: str) -> bool:
        """Check if file extension is allowed."""
        return '.' in filename and \
            filename.rsplit('.', 1)[1].lower() in ResumeService.ALLOWED_EXTENSIONS
    
    @classmethod
    def upload_resume(cls, user_id: str, file, file_name: str) -> Resume:
        """
        Upload and save resume file.
        
        Args:
            user_id: User ID
            file: File object
            file_name: Original file name
            
        Returns:
            Created Resume object
        """
        if not cls.allowed_file(file_name):
            raise ValueError(f"File type not allowed. Allowed types: {cls.ALLOWED_EXTENSIONS}")
        
        # Read file content
        file_content = file.read()
        file_size = len(file_content)
        
        if file_size > cls.MAX_FILE_SIZE:
            raise ValueError(f"File too large. Maximum size: {cls.MAX_FILE_SIZE / 1024 / 1024}MB")
        
        # Generate unique filename
        file_ext = file_name.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4()}.{file_ext}"
        
        # Save file
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        
        file_path = os.path.join(upload_folder, unique_filename)
        with open(file_path, 'wb') as f:
            f.write(file_content)
        
        # Create resume record
        resume = Resume(
            user_id=user_id,
            file_url=file_path,
            file_name=secure_filename(file_name),
            file_type=file_ext,
            file_size=file_size,
            processing_status='pending'
        )
        
        db.session.add(resume)
        db.session.commit()
        
        logger.info(f"Resume uploaded: {resume.id}")
        return resume
    
    @staticmethod
    def process_resume(resume_id: str) -> Dict:
        """
        Process resume using Resume Agent.
        
        Args:
            resume_id: Resume ID
            
        Returns:
            Processing results
        """
        agent = get_resume_agent()
        return agent.process_resume(resume_id)
    
    @staticmethod
    def get_user_resumes(user_id: str) -> List[Resume]:
        """
        Get all resumes for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of Resume objects
        """
        return Resume.query.filter_by(user_id=user_id).order_by(Resume.created_at.desc()).all()
    
    @staticmethod
    def get_resume(resume_id: str, user_id: str) -> Resume:
        """
        Get a specific resume.
        
        Args:
            resume_id: Resume ID
            user_id: User ID (for authorization)
            
        Returns:
            Resume object
        """
        resume = Resume.query.filter_by(id=resume_id, user_id=user_id).first()
        if not resume:
            raise ValueError("Resume not found")
        return resume
    
    @staticmethod
    def delete_resume(resume_id: str, user_id: str) -> None:
        """
        Delete a resume.
        
        Args:
            resume_id: Resume ID
            user_id: User ID (for authorization)
        """
        resume = Resume.query.filter_by(id=resume_id, user_id=user_id).first()
        if not resume:
            raise ValueError("Resume not found")
        
        # Delete file
        try:
            if os.path.exists(resume.file_url):
                os.remove(resume.file_url)
        except Exception as e:
            logger.warning(f"Failed to delete resume file: {e}")
        
        # Delete from database
        resume.delete()
        
        logger.info(f"Resume deleted: {resume_id}")
    
    @staticmethod
    def update_user_skills(user_id: str, skills: List[Dict]) -> List[UserSkill]:
        """
        Update user skills manually.
        
        Args:
            user_id: User ID
            skills: List of skills with skill_id and proficiency
            
        Returns:
            List of updated UserSkill objects
        """
        from app.models.skill import Skill
        
        updated_skills = []
        
        for skill_data in skills:
            skill_id = skill_data.get('skill_id')
            proficiency = skill_data.get('proficiency', 1)
            
            # Check if skill exists
            skill = Skill.query.get(skill_id)
            if not skill:
                logger.warning(f"Skill not found: {skill_id}")
                continue
            
            # Check if user already has this skill
            user_skill = UserSkill.query.filter_by(
                user_id=user_id,
                skill_id=skill_id
            ).first()
            
            if user_skill:
                # Update existing
                user_skill.proficiency = proficiency
            else:
                # Create new
                user_skill = UserSkill(
                    user_id=user_id,
                    skill_id=skill_id,
                    proficiency=proficiency,
                    is_verified=False,
                    source='manual'
                )
                db.session.add(user_skill)
            
            updated_skills.append(user_skill)
        
        db.session.commit()
        logger.info(f"Updated {len(updated_skills)} skills for user: {user_id}")
        
        return updated_skills
