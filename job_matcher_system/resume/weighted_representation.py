"""Weighted resume representation for matching."""
from typing import Dict, List
from collections import defaultdict

from .resume_model import Resume, ResumeSection
from config import config
from utils import get_logger


class WeightedResumeRepresentation:
    """
    Creates weighted text representation of resume for similarity matching.
    Different sections have different importance weights.
    """
    
    def __init__(self):
        self.logger = get_logger("weighted_representation")
        self.section_weights = config.resume.section_weights
    
    def create_weighted_text(self, resume: Resume) -> str:
        """
        Create a weighted text representation by repeating sections
        according to their importance weights.
        
        Args:
            resume: Resume object with extracted sections
            
        Returns:
            Weighted text string
        """
        weighted_parts = []
        
        # Process each section
        for section in resume.sections:
            weight = self._get_section_weight(section.name)
            
            # Repeat content based on weight (rounded)
            repetitions = max(1, int(weight))
            
            for _ in range(repetitions):
                weighted_parts.append(section.content)
        
        # Also add structured data with appropriate weights
        structured_text = self._create_structured_text(resume)
        if structured_text:
            weighted_parts.append(structured_text)
        
        # Join all parts
        weighted_text = "\n\n".join(weighted_parts)
        
        resume.weighted_text = weighted_text
        
        self.logger.info(
            f"Created weighted representation: "
            f"{len(weighted_text)} chars from {len(resume.sections)} sections"
        )
        
        return weighted_text
    
    def _get_section_weight(self, section_name: str) -> float:
        """Get weight for a section."""
        normalized_name = section_name.lower().replace(" ", "_")
        return self.section_weights.get(normalized_name, 1.0)
    
    def _create_structured_text(self, resume: Resume) -> str:
        """Create text from structured data."""
        parts = []
        
        # Add skills with high repetition
        if resume.skills:
            skill_names = [s.name for s in resume.skills]
            # Repeat skills 3 times to emphasize importance
            skills_text = "Skills: " + ", ".join(skill_names * 3)
            parts.append(skills_text)
        
        # Add experience
        if resume.experience:
            exp_parts = []
            for exp in resume.experience:
                exp_text = f"{exp.title} at {exp.company}"
                if exp.description:
                    exp_text += f": {exp.description[:200]}"
                exp_parts.append(exp_text)
            parts.append("Experience: " + " ".join(exp_parts))
        
        # Add education
        if resume.education:
            edu_parts = []
            for edu in resume.education:
                edu_text = f"{edu.degree} from {edu.institution}"
                edu_parts.append(edu_text)
            parts.append("Education: " + " ".join(edu_parts))
        
        return "\n".join(parts)
    
    def create_section_vectors(
        self,
        resume: Resume,
        embedding_model
    ) -> Dict[str, List[float]]:
        """
        Create embeddings for each section separately.
        
        Args:
            resume: Resume object
            embedding_model: Model with encode() method
            
        Returns:
            Dictionary mapping section names to embeddings
        """
        section_embeddings = {}
        
        for section in resume.sections:
            if section.content:
                try:
                    embedding = embedding_model.encode(section.content)
                    section_embeddings[section.name] = embedding.tolist()
                except Exception as e:
                    self.logger.warning(
                        f"Failed to encode section {section.name}: {e}"
                    )
        
        resume.section_embeddings = section_embeddings
        
        return section_embeddings
    
    def get_weighted_embedding(
        self,
        section_embeddings: Dict[str, List[float]]
    ) -> List[float]:
        """
        Combine section embeddings using weights.
        
        Args:
            section_embeddings: Dict of section name -> embedding
            
        Returns:
            Weighted average embedding
        """
        import numpy as np
        
        if not section_embeddings:
            return []
        
        weighted_sum = None
        total_weight = 0.0
        
        for section_name, embedding in section_embeddings.items():
            weight = self._get_section_weight(section_name)
            
            if weighted_sum is None:
                weighted_sum = np.array(embedding) * weight
            else:
                weighted_sum += np.array(embedding) * weight
            
            total_weight += weight
        
        if total_weight > 0:
            weighted_avg = weighted_sum / total_weight
            return weighted_avg.tolist()
        
        return []
    
    def extract_keywords(self, resume: Resume, top_n: int = 20) -> List[str]:
        """
        Extract important keywords from weighted representation.
        
        Args:
            resume: Resume object
            top_n: Number of top keywords to return
            
        Returns:
            List of keywords
        """
        from collections import Counter
        import re
        
        text = resume.weighted_text or resume.raw_text
        
        # Simple keyword extraction (can be enhanced with NLP)
        # Remove common stop words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to',
            'for', 'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were',
            'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did'
        }
        
        # Extract words
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        
        # Filter stop words and count
        filtered_words = [w for w in words if w not in stop_words]
        word_counts = Counter(filtered_words)
        
        # Return top keywords
        return [word for word, count in word_counts.most_common(top_n)]
