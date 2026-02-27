"""Sentence-transformer semantic similarity engine."""
from typing import List, Optional
import numpy as np
from sentence_transformers import SentenceTransformer
import joblib
from pathlib import Path

from .base_matcher import BaseMatcher, MatchResult
from resume.resume_model import Resume
from scrapers.base_scraper import JobPosting
from config import config
from utils import get_logger


class SemanticMatcher(BaseMatcher):
    """
    Semantic matcher using sentence transformers.
    Good for understanding context and meaning beyond keywords.
    """
    
    def __init__(self, model_name: str = None):
        super().__init__("semantic")
        self.logger = get_logger("semantic_matcher")
        
        self.model_name = model_name or config.model.sentence_transformer_model
        self.model: Optional[SentenceTransformer] = None
        self._load_model()
    
    def _load_model(self):
        """Load the sentence transformer model."""
        try:
            self.logger.info(f"Loading sentence transformer model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            self.logger.info("Model loaded successfully")
        except Exception as e:
            self.logger.error(f"Failed to load model: {e}")
            raise
    
    def encode(self, texts: List[str]) -> np.ndarray:
        """
        Encode texts to embeddings.
        
        Args:
            texts: List of text strings
            
        Returns:
            Numpy array of embeddings
        """
        if self.model is None:
            raise RuntimeError("Model not loaded")
        
        return self.model.encode(
            texts,
            show_progress_bar=False,
            convert_to_numpy=True
        )
    
    def match(
        self,
        resume: Resume,
        job: JobPosting
    ) -> MatchResult:
        """
        Calculate match score using semantic similarity.
        """
        # Prepare texts
        resume_text = resume.weighted_text or resume.raw_text
        job_text = self._prepare_job_text(job)
        
        # Encode
        try:
            embeddings = self.encode([resume_text, job_text])
            
            # Calculate cosine similarity
            similarity = self._cosine_similarity(embeddings[0], embeddings[1])
            
            score = float(similarity)
            
        except Exception as e:
            self.logger.error(f"Semantic matching failed: {e}")
            score = 0.0
        
        return MatchResult(
            job_id=job.id,
            resume_id=str(id(resume)),
            overall_score=round(score, 3),
            semantic_score=round(score, 3),
            explanation=f"Semantic similarity score: {score:.2f}. Based on meaning and context.",
            matcher_version=self.version
        )
    
    def match_batch(
        self,
        resume: Resume,
        jobs: List[JobPosting]
    ) -> List[MatchResult]:
        """
        Match resume against multiple jobs efficiently.
        """
        if not jobs:
            return []
        
        # Prepare texts
        resume_text = resume.weighted_text or resume.raw_text
        job_texts = [self._prepare_job_text(job) for job in jobs]
        
        # Encode all at once
        try:
            all_texts = [resume_text] + job_texts
            embeddings = self.encode(all_texts)
            
            resume_embedding = embeddings[0]
            job_embeddings = embeddings[1:]
            
            # Calculate similarities
            similarities = [
                self._cosine_similarity(resume_embedding, job_emb)
                for job_emb in job_embeddings
            ]
            
        except Exception as e:
            self.logger.error(f"Batch semantic matching failed: {e}")
            similarities = [0.0] * len(jobs)
        
        # Create results
        results = []
        for job, score in zip(jobs, similarities):
            result = MatchResult(
                job_id=job.id,
                resume_id=str(id(resume)),
                overall_score=round(score, 3),
                semantic_score=round(score, 3),
                explanation=f"Semantic similarity score: {score:.2f}",
                matcher_version=self.version
            )
            results.append(result)
        
        # Sort by score descending
        results.sort(key=lambda x: x.overall_score, reverse=True)
        
        return results
    
    def _prepare_job_text(self, job: JobPosting) -> str:
        """Prepare job text for encoding."""
        parts = [
            job.title,
            job.description,
            " ".join(job.requirements),
            " ".join(job.skills_required or [])
        ]
        return " ".join(filter(None, parts))
    
    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return float(np.dot(a, b) / (norm_a * norm_b))
    
    def encode_resume_sections(self, resume: Resume) -> dict:
        """
        Encode each resume section separately.
        
        Returns:
            Dictionary mapping section names to embeddings
        """
        section_embeddings = {}
        
        for section in resume.sections:
            if section.content:
                try:
                    embedding = self.encode([section.content])[0]
                    section_embeddings[section.name] = embedding
                except Exception as e:
                    self.logger.warning(f"Failed to encode section {section.name}: {e}")
        
        return section_embeddings
    
    def section_based_match(
        self,
        resume: Resume,
        job: JobPosting
    ) -> MatchResult:
        """
        Match using section-level embeddings with weights.
        """
        # Encode job
        job_text = self._prepare_job_text(job)
        job_embedding = self.encode([job_text])[0]
        
        # Encode resume sections
        section_embeddings = self.encode_resume_sections(resume)
        
        if not section_embeddings:
            # Fall back to full text
            return self.match(resume, job)
        
        # Calculate weighted similarity
        weighted_sum = 0.0
        total_weight = 0.0
        
        section_weights = {
            'experience': 2.0,
            'skills': 1.5,
            'summary': 1.0,
            'education': 0.8,
            'projects': 0.7
        }
        
        for section_name, embedding in section_embeddings.items():
            weight = section_weights.get(section_name, 1.0)
            similarity = self._cosine_similarity(embedding, job_embedding)
            
            weighted_sum += similarity * weight
            total_weight += weight
        
        score = weighted_sum / total_weight if total_weight > 0 else 0.0
        
        return MatchResult(
            job_id=job.id,
            resume_id=str(id(resume)),
            overall_score=round(score, 3),
            semantic_score=round(score, 3),
            explanation=f"Section-weighted semantic similarity: {score:.2f}",
            matcher_version=self.version
        )
    
    def find_similar_jobs(
        self,
        query_embedding: np.ndarray,
        job_embeddings: List[tuple],
        top_k: int = 10
    ) -> List[tuple]:
        """
        Find most similar jobs given a query embedding.
        
        Args:
            query_embedding: Embedding vector
            job_embeddings: List of (job_id, embedding) tuples
            top_k: Number of top results to return
            
        Returns:
            List of (job_id, similarity_score) tuples
        """
        similarities = []
        
        for job_id, embedding in job_embeddings:
            similarity = self._cosine_similarity(query_embedding, embedding)
            similarities.append((job_id, similarity))
        
        # Sort by similarity descending
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        return similarities[:top_k]
    
    def save_embeddings(self, embeddings: dict, filepath: Path):
        """Save embeddings to disk."""
        joblib.dump(embeddings, filepath)
        self.logger.info(f"Saved embeddings to {filepath}")
    
    def load_embeddings(self, filepath: Path) -> dict:
        """Load embeddings from disk."""
        embeddings = joblib.load(filepath)
        self.logger.info(f"Loaded embeddings from {filepath}")
        return embeddings
