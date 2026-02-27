"""Hybrid scoring system combining multiple matching engines."""
from typing import List, Optional, Dict
from dataclasses import dataclass

from .base_matcher import BaseMatcher, MatchResult
from .rule_based_matcher import RuleBasedMatcher
from .tfidf_matcher import TFIDFMatcher
from .semantic_matcher import SemanticMatcher
from resume.resume_model import Resume
from scrapers.base_scraper import JobPosting
from config import config
from utils import get_logger


@dataclass
class HybridWeights:
    """Weights for hybrid scoring components."""
    rule_based: float = 0.25
    tfidf: float = 0.25
    semantic: float = 0.50
    
    def validate(self):
        """Ensure weights sum to 1.0."""
        total = self.rule_based + self.tfidf + self.semantic
        if abs(total - 1.0) > 0.001:
            raise ValueError(f"Weights must sum to 1.0, got {total}")


class HybridMatcher(BaseMatcher):
    """
    Hybrid matcher combining rule-based, TF-IDF, and semantic matching.
    Provides the best of all approaches:
    - Rule-based: Interpretable, explicit criteria
    - TF-IDF: Keyword overlap, fast
    - Semantic: Context understanding, meaning-based
    """
    
    def __init__(
        self,
        rule_matcher: RuleBasedMatcher = None,
        tfidf_matcher: TFIDFMatcher = None,
        semantic_matcher: SemanticMatcher = None,
        weights: HybridWeights = None
    ):
        super().__init__("hybrid")
        self.logger = get_logger("hybrid_matcher")
        
        # Initialize matchers
        self.rule_matcher = rule_matcher or RuleBasedMatcher()
        self.tfidf_matcher = tfidf_matcher or TFIDFMatcher()
        self.semantic_matcher = semantic_matcher or SemanticMatcher()
        
        # Weights
        self.weights = weights or HybridWeights(
            rule_based=config.scoring.rule_based_weight,
            tfidf=config.scoring.tfidf_weight,
            semantic=config.scoring.semantic_weight
        )
        self.weights.validate()
    
    def match(
        self,
        resume: Resume,
        job: JobPosting
    ) -> MatchResult:
        """
        Calculate hybrid match score combining all engines.
        """
        self.logger.debug(f"Hybrid matching: {job.title}")
        
        # Get scores from all matchers
        rule_result = self.rule_matcher.match(resume, job)
        tfidf_result = self.tfidf_matcher.match(resume, job)
        semantic_result = self.semantic_matcher.match(resume, job)
        
        # Calculate weighted overall score
        overall_score = (
            rule_result.overall_score * self.weights.rule_based +
            tfidf_result.overall_score * self.weights.tfidf +
            semantic_result.overall_score * self.weights.semantic
        )
        
        # Combine explanations
        explanation = self._generate_hybrid_explanation(
            rule_result,
            tfidf_result,
            semantic_result,
            overall_score
        )
        
        # Combine matching skills
        all_matching_skills = list(set(
            rule_result.matching_skills +
            tfidf_result.matching_skills +
            semantic_result.matching_skills
        ))
        
        # Combine missing skills
        all_missing_skills = list(set(
            rule_result.missing_skills +
            tfidf_result.missing_skills +
            semantic_result.missing_skills
        ))
        
        return MatchResult(
            job_id=job.id,
            resume_id=str(id(resume)),
            overall_score=round(overall_score, 3),
            rule_based_score=round(rule_result.overall_score, 3),
            tfidf_score=round(tfidf_result.overall_score, 3),
            semantic_score=round(semantic_result.overall_score, 3),
            skill_match_score=rule_result.skill_match_score,
            experience_match_score=rule_result.experience_match_score,
            education_match_score=rule_result.education_match_score,
            matching_skills=all_matching_skills[:15],
            missing_skills=all_missing_skills[:10],
            skill_gaps=all_missing_skills[:10],
            explanation=explanation,
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
        self.logger.info(f"Hybrid batch matching against {len(jobs)} jobs")
        
        # Get all results from each matcher
        rule_results = self.rule_matcher.match_batch(resume, jobs)
        tfidf_results = self.tfidf_matcher.match_batch(resume, jobs)
        semantic_results = self.semantic_matcher.match_batch(resume, jobs)
        
        # Create lookup by job_id
        rule_by_id = {r.job_id: r for r in rule_results}
        tfidf_by_id = {r.job_id: r for r in tfidf_results}
        semantic_by_id = {r.job_id: r for r in semantic_results}
        
        # Combine results
        combined_results = []
        
        for job in jobs:
            rule_result = rule_by_id.get(job.id)
            tfidf_result = tfidf_by_id.get(job.id)
            semantic_result = semantic_by_id.get(job.id)
            
            if not all([rule_result, tfidf_result, semantic_result]):
                self.logger.warning(f"Missing results for job {job.id}")
                continue
            
            # Calculate weighted score
            overall_score = (
                rule_result.overall_score * self.weights.rule_based +
                tfidf_result.overall_score * self.weights.tfidf +
                semantic_result.overall_score * self.weights.semantic
            )
            
            # Combine skills
            all_matching = list(set(
                rule_result.matching_skills +
                tfidf_result.matching_skills +
                semantic_result.matching_skills
            ))
            
            all_missing = list(set(
                rule_result.missing_skills +
                tfidf_result.missing_skills +
                semantic_result.missing_skills
            ))
            
            explanation = self._generate_hybrid_explanation(
                rule_result, tfidf_result, semantic_result, overall_score
            )
            
            result = MatchResult(
                job_id=job.id,
                resume_id=str(id(resume)),
                overall_score=round(overall_score, 3),
                rule_based_score=round(rule_result.overall_score, 3),
                tfidf_score=round(tfidf_result.overall_score, 3),
                semantic_score=round(semantic_result.overall_score, 3),
                skill_match_score=rule_result.skill_match_score,
                experience_match_score=rule_result.experience_match_score,
                education_match_score=rule_result.education_match_score,
                matching_skills=all_matching[:15],
                missing_skills=all_missing[:10],
                skill_gaps=all_missing[:10],
                explanation=explanation,
                matcher_version=self.version
            )
            
            combined_results.append(result)
        
        # Sort by overall score
        combined_results.sort(key=lambda x: x.overall_score, reverse=True)
        
        self.logger.info(f"Hybrid matching complete. Top score: {combined_results[0].overall_score if combined_results else 0}")
        
        return combined_results
    
    def _generate_hybrid_explanation(
        self,
        rule_result: MatchResult,
        tfidf_result: MatchResult,
        semantic_result: MatchResult,
        overall_score: float
    ) -> str:
        """Generate comprehensive explanation."""
        parts = []
        
        # Overall assessment
        if overall_score >= 0.8:
            parts.append("Excellent match!")
        elif overall_score >= 0.6:
            parts.append("Good match.")
        elif overall_score >= 0.4:
            parts.append("Moderate match.")
        else:
            parts.append("Weak match.")
        
        # Component breakdown
        parts.append(
            f"Rule-based: {rule_result.overall_score:.2f}, "
            f"TF-IDF: {tfidf_result.overall_score:.2f}, "
            f"Semantic: {semantic_result.overall_score:.2f}."
        )
        
        # Skills info
        if rule_result.matching_skills:
            parts.append(
                f"Matching skills ({len(rule_result.matching_skills)}): "
                f"{', '.join(rule_result.matching_skills[:5])}."
            )
        
        if rule_result.missing_skills:
            parts.append(
                f"Missing skills: {', '.join(rule_result.missing_skills[:3])}."
            )
        
        # Experience info
        if rule_result.experience_match_score:
            if rule_result.experience_match_score >= 0.8:
                parts.append("Experience level is a strong match.")
            elif rule_result.experience_match_score >= 0.5:
                parts.append("Experience level is acceptable.")
            else:
                parts.append("Experience level may not meet requirements.")
        
        return " ".join(parts)
    
    def get_component_scores(self, result: MatchResult) -> Dict[str, float]:
        """Extract individual component scores from result."""
        return {
            'rule_based': result.rule_based_score or 0.0,
            'tfidf': result.tfidf_score or 0.0,
            'semantic': result.semantic_score or 0.0,
            'overall': result.overall_score
        }
    
    def analyze_match_quality(self, result: MatchResult) -> Dict[str, str]:
        """
        Analyze the quality of a match.
        
        Returns:
            Dictionary with analysis details
        """
        scores = self.get_component_scores(result)
        
        analysis = {
            'overall_rating': 'poor',
            'strength': 'none',
            'weakness': 'none',
            'recommendation': 'skip'
        }
        
        # Overall rating
        if result.overall_score >= 0.8:
            analysis['overall_rating'] = 'excellent'
            analysis['recommendation'] = 'apply'
        elif result.overall_score >= 0.6:
            analysis['overall_rating'] = 'good'
            analysis['recommendation'] = 'apply'
        elif result.overall_score >= 0.4:
            analysis['overall_rating'] = 'moderate'
            analysis['recommendation'] = 'consider'
        else:
            analysis['overall_rating'] = 'poor'
            analysis['recommendation'] = 'skip'
        
        # Find strongest component
        max_component = max(scores.items(), key=lambda x: x[1] if x[0] != 'overall' else 0)
        analysis['strength'] = max_component[0]
        
        # Find weakest component
        min_component = min(
            [(k, v) for k, v in scores.items() if k != 'overall'],
            key=lambda x: x[1]
        )
        analysis['weakness'] = min_component[0]
        
        return analysis
    
    def fit_tfidf(self, documents: List[str]):
        """Fit the TF-IDF matcher on a corpus."""
        self.tfidf_matcher.fit(documents)
        self.logger.info("Fitted TF-IDF matcher on corpus")
    
    def set_weights(self, weights: HybridWeights):
        """Update hybrid weights."""
        weights.validate()
        self.weights = weights
        self.logger.info(f"Updated hybrid weights: {weights}")
