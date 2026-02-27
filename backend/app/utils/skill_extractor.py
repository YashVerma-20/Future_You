"""Skill extraction using NER and local models."""
import re
from typing import List, Dict, Set
import structlog

logger = structlog.get_logger()


# Common technical skills taxonomy
TECHNICAL_SKILLS = {
    'programming_languages': {
        'python', 'javascript', 'typescript', 'java', 'c++', 'c#', 'go', 'rust',
        'ruby', 'php', 'swift', 'kotlin', 'scala', 'r', 'matlab', 'perl',
        'shell', 'bash', 'powershell', 'sql', 'html', 'css', 'sass', 'less'
    },
    'frameworks_libraries': {
        'react', 'vue', 'angular', 'svelte', 'next.js', 'nuxt', 'django',
        'flask', 'fastapi', 'spring', 'laravel', 'express', 'nestjs',
        'tensorflow', 'pytorch', 'scikit-learn', 'pandas', 'numpy',
        'bootstrap', 'tailwind', 'material-ui', 'antd'
    },
    'databases': {
        'postgresql', 'mysql', 'mongodb', 'redis', 'elasticsearch', 'cassandra',
        'dynamodb', 'sqlite', 'oracle', 'sql server', 'firebase', 'couchdb'
    },
    'cloud_platforms': {
        'aws', 'azure', 'gcp', 'google cloud', 'heroku', 'digitalocean',
        'vercel', 'netlify', 'cloudflare', 'docker', 'kubernetes', 'terraform'
    },
    'tools': {
        'git', 'github', 'gitlab', 'bitbucket', 'jenkins', 'circleci',
        'travis', 'github actions', 'jira', 'confluence', 'slack', 'trello'
    },
    'machine_learning': {
        'machine learning', 'deep learning', 'nlp', 'computer vision',
        'data science', 'data analysis', 'statistics', 'a/b testing',
        'neural networks', 'transformers', 'llm', 'generative ai'
    }
}

SOFT_SKILLS = {
    'leadership', 'communication', 'teamwork', 'problem solving', 'critical thinking',
    'time management', 'project management', 'agile', 'scrum', 'collaboration',
    'adaptability', 'creativity', 'attention to detail', 'analytical thinking'
}


class SkillExtractor:
    """Extract skills from text using pattern matching and NER."""
    
    def __init__(self):
        self.all_skills = self._build_skill_set()
        self.skill_patterns = self._compile_patterns()
    
    def _build_skill_set(self) -> Set[str]:
        """Build a comprehensive set of all known skills."""
        skills = set()
        for category, skill_set in TECHNICAL_SKILLS.items():
            skills.update(skill_set)
        skills.update(SOFT_SKILLS)
        return skills
    
    def _compile_patterns(self) -> Dict[str, re.Pattern]:
        """Compile regex patterns for skill detection."""
        patterns = {}
        for skill in self.all_skills:
            # Create pattern that matches whole word with optional variations
            pattern = r'\b' + re.escape(skill) + r'\b'
            patterns[skill] = re.compile(pattern, re.IGNORECASE)
        return patterns
    
    def extract_skills(self, text: str) -> List[Dict]:
        """
        Extract skills from text.
        
        Args:
            text: Input text to analyze
            
        Returns:
            List of extracted skills with metadata
        """
        if not text:
            return []
        
        text_lower = text.lower()
        found_skills = []
        
        for skill, pattern in self.skill_patterns.items():
            matches = pattern.findall(text)
            if matches:
                # Determine category
                category = self._get_skill_category(skill)
                
                found_skills.append({
                    'name': skill,
                    'normalized_name': skill.lower(),
                    'category': category,
                    'mentions': len(matches),
                    'confidence': min(1.0, 0.5 + len(matches) * 0.1)
                })
        
        # Sort by mentions (frequency) descending
        found_skills.sort(key=lambda x: x['mentions'], reverse=True)
        
        logger.info(f"Extracted {len(found_skills)} skills from text")
        return found_skills
    
    def _get_skill_category(self, skill: str) -> str:
        """Determine the category of a skill."""
        skill_lower = skill.lower()
        
        for category, skills in TECHNICAL_SKILLS.items():
            if skill_lower in skills:
                return category
        
        if skill_lower in SOFT_SKILLS:
            return 'soft_skills'
        
        return 'other'
    
    def extract_sections(self, text: str) -> Dict[str, str]:
        """
        Extract common resume sections.
        
        Args:
            text: Resume text
            
        Returns:
            Dictionary of section names to content
        """
        sections = {
            'experience': '',
            'education': '',
            'skills': '',
            'summary': '',
            'projects': ''
        }
        
        # Common section headers
        section_patterns = {
            'experience': r'(?:experience|work experience|employment|professional experience)',
            'education': r'(?:education|academic|qualifications|degrees)',
            'skills': r'(?:skills|technical skills|competencies|expertise)',
            'summary': r'(?:summary|objective|profile|about)',
            'projects': r'(?:projects|personal projects|side projects)'
        }
        
        lines = text.split('\n')
        current_section = None
        section_content = []
        
        for line in lines:
            line_lower = line.lower().strip()
            
            # Check if line is a section header
            for section_name, pattern in section_patterns.items():
                if re.search(pattern, line_lower) and len(line_lower) < 50:
                    # Save previous section
                    if current_section and section_content:
                        sections[current_section] = '\n'.join(section_content).strip()
                    
                    current_section = section_name
                    section_content = []
                    break
            else:
                if current_section:
                    section_content.append(line)
        
        # Save last section
        if current_section and section_content:
            sections[current_section] = '\n'.join(section_content).strip()
        
        return sections
    
    def normalize_skill(self, skill_name: str) -> str:
        """
        Normalize a skill name.
        
        Args:
            skill_name: Raw skill name
            
        Returns:
            Normalized skill name
        """
        # Convert to lowercase
        normalized = skill_name.lower().strip()
        
        # Remove common suffixes
        normalized = re.sub(r'\s*(programming|language|framework|library)$', '', normalized)
        
        # Standardize common variations
        variations = {
            'js': 'javascript',
            'ts': 'typescript',
            'py': 'python',
            'node': 'nodejs',
            'reactjs': 'react',
            'vuejs': 'vue',
        }
        
        return variations.get(normalized, normalized)


# Global instance
skill_extractor = SkillExtractor()


def extract_skills_from_text(text: str) -> List[Dict]:
    """Convenience function to extract skills from text."""
    return skill_extractor.extract_skills(text)


def extract_resume_sections(text: str) -> Dict[str, str]:
    """Convenience function to extract resume sections."""
    return skill_extractor.extract_sections(text)
