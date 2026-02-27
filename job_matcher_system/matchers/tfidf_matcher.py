"""TF-IDF similarity engine for job-resume matching."""
from typing import List, Optional
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import joblib
from pathlib import Path

from .base_matcher import BaseMatcher, MatchResult
from resume.resume_model import Resume
from scrapers.base_scraper import JobPosting
from config import config
from utils import get_logger


class TFIDFMatcher(BaseMatcher):
    """
    TF-IDF based matcher using term frequency-inverse document frequency.
    Good for keyword-based matching and fast computation.
    """
    
    def __init__(self, vectorizer: TfidfVectorizer = None):
        super().__init__("tfidf")
        self.logger = get_logger("tfidf_matcher")
        
        self.vectorizer = vectorizer or self._create_vectorizer()
        self._fitted = False
    
    def _create_vectorizer(self) -> TfidfVectorizer:
        """Create TF-IDF vectorizer with configuration."""
        return TfidfVectorizer(
            max_features=config.model.tfidf_max_features,
            ngram_range=config.model.tfidf_ngram_range,
            min_df=config.model.tfidf_min_df,
            max_df=config.model.tfidf_max_df,
            stop_words='english',
            lowercase=True,
            strip_accents='unicode'
        )
    
    def fit(self, documents: List[str]):
        """
        Fit the vectorizer on a corpus of documents.
        
        Args:
            documents: List of text documents
        """
        self.logger.info(f"Fitting TF-IDF vectorizer on {len(documents)} documents")
        self.vectorizer.fit(documents)
        self._fitted = True
        self.logger.info("TF-IDF vectorizer fitted successfully")
    
    def match(
        self,
        resume: Resume,
        job: JobPosting
    ) -> MatchResult:
        """
        Calculate match score using TF-IDF cosine similarity.
        """
        if not self._fitted:
            self.logger.warning("Vectorizer not fitted. Fitting on current documents.")
            # Fit on both documents
            self.fit([resume.weighted_text or resume.raw_text, job.description])
        
        # Prepare texts
        resume_text = resume.weighted_text or resume.raw_text
        job_text = self._prepare_job_text(job)
        
        # Transform to TF-IDF vectors
        try:
            tfidf_matrix = self.vectorizer.transform([resume_text, job_text])
            
            # Calculate cosine similarity
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            
            # Normalize to 0-1
            score = float(similarity)
            
        except Exception as e:
            self.logger.error(f"TF-IDF calculation failed: {e}")
            score = 0.0
        
        # Get matching terms for explanation
        matching_terms = self._get_matching_terms(resume_text, job_text)
        
        return MatchResult(
            job_id=job.id,
            resume_id=str(id(resume)),
            overall_score=round(score, 3),
            tfidf_score=round(score, 3),
            matching_skills=matching_terms[:10],
            explanation=f"TF-IDF similarity score: {score:.2f}. Key matching terms: {', '.join(matching_terms[:5])}.",
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
        
        # Fit if not already fitted
        if not self._fitted:
            all_texts = [resume_text] + job_texts
            self.fit(all_texts)
        
        # Transform all at once
        try:
            resume_vector = self.vectorizer.transform([resume_text])
            job_vectors = self.vectorizer.transform(job_texts)
            
            # Calculate similarities
            similarities = cosine_similarity(resume_vector, job_vectors)[0]
            
        except Exception as e:
            self.logger.error(f"Batch TF-IDF calculation failed: {e}")
            similarities = np.zeros(len(jobs))
        
        # Create results
        results = []
        for job, score in zip(jobs, similarities):
            result = MatchResult(
                job_id=job.id,
                resume_id=str(id(resume)),
                overall_score=round(float(score), 3),
                tfidf_score=round(float(score), 3),
                explanation=f"TF-IDF similarity score: {score:.2f}",
                matcher_version=self.version
            )
            results.append(result)
        
        # Sort by score descending
        results.sort(key=lambda x: x.overall_score, reverse=True)
        
        return results
    
    def _prepare_job_text(self, job: JobPosting) -> str:
        """Prepare job text for matching."""
        parts = [
            job.title,
            job.description,
            " ".join(job.requirements),
            " ".join(job.skills_required or [])
        ]
        return " ".join(filter(None, parts))
    
    def _get_matching_terms(self, resume_text: str, job_text: str) -> List[str]:
        """Get top matching terms between resume and job."""
        try:
            # Transform individual documents
            resume_tfidf = self.vectorizer.transform([resume_text])
            job_tfidf = self.vectorizer.transform([job_text])
            
            # Get feature names
            feature_names = self.vectorizer.get_feature_names_out()
            
            # Get non-zero terms from both
            resume_terms = set(resume_tfidf.nonzero()[1])
            job_terms = set(job_tfidf.nonzero()[1])
            
            # Find common terms
            common_terms = resume_terms & job_terms
            
            # Get term scores
            term_scores = []
            for idx in common_terms:
                score = resume_tfidf[0, idx] * job_tfidf[0, idx]
                term_scores.append((feature_names[idx], score))
            
            # Sort by score
            term_scores.sort(key=lambda x: x[1], reverse=True)
            
            return [term for term, _ in term_scores[:20]]
            
        except Exception as e:
            self.logger.warning(f"Failed to get matching terms: {e}")
            return []
    
    def get_feature_names(self) -> List[str]:
        """Get TF-IDF feature names."""
        return list(self.vectorizer.get_feature_names_out())
    
    def get_top_terms(self, text: str, n: int = 10) -> List[tuple]:
        """
        Get top TF-IDF terms for a text.
        
        Returns:
            List of (term, score) tuples
        """
        if not self._fitted:
            self.logger.warning("Vectorizer not fitted")
            return []
        
        try:
            tfidf_vector = self.vectorizer.transform([text])
            feature_names = self.vectorizer.get_feature_names_out()
            
            # Get non-zero entries
            indices = tfidf_vector.nonzero()[1]
            scores = tfidf_vector.data
            
            # Create term-score pairs
            term_scores = [
                (feature_names[idx], score)
                for idx, score in zip(indices, scores)
            ]
            
            # Sort by score
            term_scores.sort(key=lambda x: x[1], reverse=True)
            
            return term_scores[:n]
            
        except Exception as e:
            self.logger.error(f"Failed to get top terms: {e}")
            return []
    
    def save(self, filepath: Path):
        """Save fitted vectorizer to disk."""
        joblib.dump({
            'vectorizer': self.vectorizer,
            'fitted': self._fitted,
            'version': self.version
        }, filepath)
        self.logger.info(f"Saved TF-IDF vectorizer to {filepath}")
    
    def load(self, filepath: Path):
        """Load fitted vectorizer from disk."""
        data = joblib.load(filepath)
        self.vectorizer = data['vectorizer']
        self._fitted = data['fitted']
        self.version = data.get('version', '1.0')
        self.logger.info(f"Loaded TF-IDF vectorizer from {filepath}")
