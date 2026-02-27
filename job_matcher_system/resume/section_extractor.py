"""Resume section extraction using regex patterns."""
import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from .resume_model import Resume, ResumeSection, ExperienceEntry, EducationEntry, Skill
from utils import get_logger


@dataclass
class SectionPattern:
    """Pattern for matching a resume section."""
    name: str
    primary_patterns: List[str]
    secondary_patterns: List[str] = None
    weight: float = 1.0
    
    def __post_init__(self):
        if self.secondary_patterns is None:
            self.secondary_patterns = []


class ResumeSectionExtractor:
    """
    Extract sections from resume text using regex patterns.
    """
    
    # Section patterns with multiple variations
    SECTION_PATTERNS = [
        SectionPattern(
            name="contact",
            primary_patterns=[
                r'(?:^|\n)\s*(?:contact|personal info|personal details)\s*(?:\n|$)',
            ],
            weight=0.5
        ),
        SectionPattern(
            name="summary",
            primary_patterns=[
                r'(?:^|\n)\s*(?:summary|professional summary|profile|objective|about me|overview)\s*(?:\n|$)',
            ],
            weight=1.0
        ),
        SectionPattern(
            name="experience",
            primary_patterns=[
                r'(?:^|\n)\s*(?:experience|work experience|employment|professional experience|career history|work history)\s*(?:\n|$)',
            ],
            weight=2.0
        ),
        SectionPattern(
            name="education",
            primary_patterns=[
                r'(?:^|\n)\s*(?:education|academic|qualifications|degrees|academic background)\s*(?:\n|$)',
            ],
            weight=1.5
        ),
        SectionPattern(
            name="skills",
            primary_patterns=[
                r'(?:^|\n)\s*(?:skills|technical skills|core competencies|expertise|proficiencies|key skills)\s*(?:\n|$)',
            ],
            weight=1.5
        ),
        SectionPattern(
            name="projects",
            primary_patterns=[
                r'(?:^|\n)\s*(?:projects|personal projects|side projects|portfolio)\s*(?:\n|$)',
            ],
            weight=1.0
        ),
        SectionPattern(
            name="certifications",
            primary_patterns=[
                r'(?:^|\n)\s*(?:certifications|certificates|professional certifications|accreditations)\s*(?:\n|$)',
            ],
            weight=0.8
        ),
        SectionPattern(
            name="awards",
            primary_patterns=[
                r'(?:^|\n)\s*(?:awards|honors|achievements|recognitions)\s*(?:\n|$)',
            ],
            weight=0.5
        ),
        SectionPattern(
            name="publications",
            primary_patterns=[
                r'(?:^|\n)\s*(?:publications|papers|research|articles)\s*(?:\n|$)',
            ],
            weight=0.5
        ),
        SectionPattern(
            name="languages",
            primary_patterns=[
                r'(?:^|\n)\s*(?:languages|language proficiency|spoken languages)\s*(?:\n|$)',
            ],
            weight=0.5
        ),
    ]
    
    # Experience entry patterns
    EXPERIENCE_PATTERNS = [
        # Company | Title | Date pattern
        r'([A-Z][A-Za-z\s&]+)\s*[|,]\s*([A-Za-z\s]+)\s*[|,]\s*(\w+\s*\d{4})\s*-\s*(\w+\s*\d{4}|present|current)',
        # Title at Company pattern
        r'([A-Za-z\s]+)\s+at\s+([A-Z][A-Za-z\s&]+)\s*\(?\s*(\w+\s*\d{4})\s*-\s*(\w+\s*\d{4}|present|current)\s*\)?',
    ]
    
    # Education patterns
    EDUCATION_PATTERNS = [
        # Degree in Field
        r'(Bachelor|Master|Ph\.?D|MBA|B\.S\.?|M\.S\.?|B\.A\.?|M\.A\.?)\s*(?:of|in)?\s*([A-Za-z\s]+)',
        # University pattern
        r'([A-Z][A-Za-z\s]+University|College|Institute|School)',
    ]
    
    # Skill categories
    SKILL_CATEGORIES = {
        'programming': ['python', 'java', 'javascript', 'c++', 'c#', 'go', 'rust', 'ruby', 'php'],
        'web': ['html', 'css', 'react', 'angular', 'vue', 'node.js', 'django', 'flask'],
        'data': ['sql', 'pandas', 'numpy', 'tensorflow', 'pytorch', 'machine learning'],
        'cloud': ['aws', 'azure', 'gcp', 'docker', 'kubernetes'],
        'soft': ['communication', 'leadership', 'teamwork', 'problem solving']
    }
    
    def __init__(self):
        self.logger = get_logger("section_extractor")
    
    def extract_sections(self, resume: Resume) -> Resume:
        """
        Extract all sections from resume text.
        
        Args:
            resume: Resume object with raw_text
            
        Returns:
            Resume with populated sections
        """
        text = resume.raw_text
        sections = []
        
        # Find all section boundaries
        section_boundaries = self._find_section_boundaries(text)
        
        # Extract content for each section
        for i, (section_name, start_pos, end_pos) in enumerate(section_boundaries):
            content = text[start_pos:end_pos].strip()
            
            # Get weight for this section
            weight = self._get_section_weight(section_name)
            
            section = ResumeSection(
                name=section_name,
                content=content,
                weight=weight,
                order=i
            )
            sections.append(section)
        
        resume.sections = sections
        
        # Extract structured data from sections
        self._extract_structured_data(resume)
        
        self.logger.info(f"Extracted {len(sections)} sections")
        return resume
    
    def _find_section_boundaries(self, text: str) -> List[Tuple[str, int, int]]:
        """
        Find all section boundaries in the text.
        
        Returns:
            List of (section_name, start_pos, end_pos) tuples
        """
        boundaries = []
        
        for pattern in self.SECTION_PATTERNS:
            for regex_pattern in pattern.primary_patterns:
                matches = list(re.finditer(regex_pattern, text, re.IGNORECASE))
                
                for match in matches:
                    section_start = match.end()
                    boundaries.append((
                        pattern.name,
                        section_start,
                        None  # Will be determined later
                    ))
        
        # Sort by position
        boundaries.sort(key=lambda x: x[1])
        
        # Determine end positions (start of next section)
        result = []
        for i, (name, start, _) in enumerate(boundaries):
            if i < len(boundaries) - 1:
                end = boundaries[i + 1][1]
            else:
                end = len(text)
            
            # Look back to get the actual content
            # Find the start of the line after the header
            content_start = start
            for j in range(start, min(start + 200, len(text))):
                if text[j] == '\n':
                    content_start = j + 1
                    break
            
            result.append((name, content_start, end))
        
        return result
    
    def _get_section_weight(self, section_name: str) -> float:
        """Get the weight for a section type."""
        for pattern in self.SECTION_PATTERNS:
            if pattern.name == section_name:
                return pattern.weight
        return 1.0
    
    def _extract_structured_data(self, resume: Resume):
        """Extract structured data from sections."""
        # Extract experience
        experience_section = resume.get_section_content("experience")
        if experience_section:
            resume.experience = self._extract_experience(experience_section)
        
        # Extract education
        education_section = resume.get_section_content("education")
        if education_section:
            resume.education = self._extract_education(education_section)
        
        # Extract skills
        skills_section = resume.get_section_content("skills")
        if skills_section:
            resume.skills = self._extract_skills(skills_section)
        
        # Also extract skills from full text if skills section is sparse
        if len(resume.skills) < 5:
            additional_skills = self._extract_skills(resume.raw_text)
            existing_names = {s.name.lower() for s in resume.skills}
            for skill in additional_skills:
                if skill.name.lower() not in existing_names:
                    resume.skills.append(skill)
    
    def _extract_experience(self, text: str) -> List[ExperienceEntry]:
        """Extract work experience entries."""
        entries = []
        
        # Split by common delimiters
        lines = text.split('\n')
        current_entry = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Try to match experience patterns
            for pattern in self.EXPERIENCE_PATTERNS:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    # Save previous entry
                    if current_entry:
                        entries.append(current_entry)
                    
                    # Create new entry
                    groups = match.groups()
                    if len(groups) >= 4:
                        current_entry = ExperienceEntry(
                            title=groups[1].strip(),
                            company=groups[0].strip(),
                            start_date=groups[2].strip(),
                            end_date=groups[3].strip(),
                            is_current=groups[3].lower() in ['present', 'current']
                        )
                    break
            else:
                # Add to description of current entry
                if current_entry:
                    current_entry.description += line + " "
        
        # Don't forget the last entry
        if current_entry:
            entries.append(current_entry)
        
        return entries
    
    def _extract_education(self, text: str) -> List[EducationEntry]:
        """Extract education entries."""
        entries = []
        
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            for pattern in self.EDUCATION_PATTERNS:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    groups = match.groups()
                    
                    entry = EducationEntry(
                        degree=groups[0] if groups else line,
                        institution=groups[1] if len(groups) > 1 else "",
                    )
                    entries.append(entry)
                    break
        
        return entries
    
    def _extract_skills(self, text: str) -> List[Skill]:
        """Extract skills from text."""
        skills = []
        text_lower = text.lower()
        
        for category, skill_list in self.SKILL_CATEGORIES.items():
            for skill_name in skill_list:
                # Look for whole word matches
                pattern = r'\b' + re.escape(skill_name) + r'\b'
                if re.search(pattern, text_lower):
                    skills.append(Skill(
                        name=skill_name,
                        category=category
                    ))
        
        return skills
    
    def extract_years_of_experience(self, text: str) -> Optional[float]:
        """Extract total years of experience from text."""
        # Pattern: "X years" or "X+ years"
        pattern = r'(\d+(?:\.\d+)?)\+?\s*years?'
        matches = re.findall(pattern, text, re.IGNORECASE)
        
        if matches:
            # Return the largest number found (usually total experience)
            return max(float(m) for m in matches)
        
        return None
