"""Resume data models."""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime
from pathlib import Path
import json


@dataclass
class ResumeSection:
    """Represents a section of a resume."""
    name: str
    content: str
    weight: float = 1.0
    order: int = 0
    
    def to_dict(self) -> Dict:
        return {
            'name': self.name,
            'content': self.content,
            'weight': self.weight,
            'order': self.order
        }


@dataclass
class ExperienceEntry:
    """Work experience entry."""
    title: str
    company: str
    location: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    description: str = ""
    is_current: bool = False
    
    def to_dict(self) -> Dict:
        return {
            'title': self.title,
            'company': self.company,
            'location': self.location,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'description': self.description,
            'is_current': self.is_current
        }


@dataclass
class EducationEntry:
    """Education entry."""
    degree: str
    institution: str
    field_of_study: Optional[str] = None
    graduation_date: Optional[str] = None
    gpa: Optional[float] = None
    
    def to_dict(self) -> Dict:
        return {
            'degree': self.degree,
            'institution': self.institution,
            'field_of_study': self.field_of_study,
            'graduation_date': self.graduation_date,
            'gpa': self.gpa
        }


@dataclass
class Skill:
    """Skill with proficiency."""
    name: str
    category: Optional[str] = None
    proficiency: Optional[int] = None  # 1-5 scale
    years_experience: Optional[float] = None
    
    def to_dict(self) -> Dict:
        return {
            'name': self.name,
            'category': self.category,
            'proficiency': self.proficiency,
            'years_experience': self.years_experience
        }


@dataclass
class Resume:
    """
    Complete resume representation.
    """
    # Basic info
    raw_text: str
    file_path: Optional[Path] = None
    
    # Extracted sections
    sections: List[ResumeSection] = field(default_factory=list)
    
    # Structured data
    contact_info: Dict[str, Any] = field(default_factory=dict)
    experience: List[ExperienceEntry] = field(default_factory=list)
    education: List[EducationEntry] = field(default_factory=list)
    skills: List[Skill] = field(default_factory=list)
    
    # Metadata
    processed_at: Optional[datetime] = None
    parser_version: str = "1.0"
    
    # Weighted representation (computed)
    weighted_text: Optional[str] = None
    section_embeddings: Optional[Dict[str, List[float]]] = None
    
    def __post_init__(self):
        if self.processed_at is None:
            self.processed_at = datetime.now()
    
    def get_section(self, name: str) -> Optional[ResumeSection]:
        """Get section by name."""
        for section in self.sections:
            if section.name.lower() == name.lower():
                return section
        return None
    
    def get_section_content(self, name: str) -> str:
        """Get section content by name."""
        section = self.get_section(name)
        return section.content if section else ""
    
    def get_skills_by_category(self, category: str) -> List[Skill]:
        """Get skills filtered by category."""
        return [s for s in self.skills if s.category == category]
    
    def get_total_experience_years(self) -> float:
        """Calculate total years of experience."""
        total = 0.0
        for exp in self.experience:
            if exp.years_experience:
                total += exp.years_experience
        return total
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'raw_text': self.raw_text,
            'file_path': str(self.file_path) if self.file_path else None,
            'sections': [s.to_dict() for s in self.sections],
            'contact_info': self.contact_info,
            'experience': [e.to_dict() for e in self.experience],
            'education': [e.to_dict() for e in self.education],
            'skills': [s.to_dict() for s in self.skills],
            'processed_at': self.processed_at.isoformat() if self.processed_at else None,
            'parser_version': self.parser_version,
            'weighted_text': self.weighted_text
        }
    
    def save(self, filepath: Path):
        """Save resume to JSON file."""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
    
    @classmethod
    def load(cls, filepath: Path) -> 'Resume':
        """Load resume from JSON file."""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Reconstruct sections
        sections = [
            ResumeSection(**s) for s in data.get('sections', [])
        ]
        
        # Reconstruct experience
        experience = [
            ExperienceEntry(**e) for e in data.get('experience', [])
        ]
        
        # Reconstruct education
        education = [
            EducationEntry(**e) for e in data.get('education', [])
        ]
        
        # Reconstruct skills
        skills = [
            Skill(**s) for s in data.get('skills', [])
        ]
        
        return cls(
            raw_text=data['raw_text'],
            file_path=Path(data['file_path']) if data.get('file_path') else None,
            sections=sections,
            contact_info=data.get('contact_info', {}),
            experience=experience,
            education=education,
            skills=skills,
            parser_version=data.get('parser_version', '1.0'),
            weighted_text=data.get('weighted_text')
        )
