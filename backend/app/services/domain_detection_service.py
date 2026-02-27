"""Career Domain Detection Service for identifying user's professional domain."""
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import numpy as np
import structlog

from app.agents.job_agent import get_job_agent
from app.models.job import Job

logger = structlog.get_logger()


@dataclass
class DomainResult:
    """Result of domain detection."""
    primary_domain: str
    primary_confidence: float
    secondary_domain: Optional[str]
    secondary_confidence: float
    all_scores: Dict[str, float]


class DomainDetectionService:
    """
    Detects career domains based on resume/job text using embedding similarity.
    
    Domains:
    - Machine Learning / AI
    - Backend Engineering
    - Frontend Engineering
    - Data Engineering
    - DevOps / SRE
    - Mobile Development
    - Full Stack
    """

    # Domain definitions with characteristic keywords
    DOMAIN_KEYWORDS = {
        'machine_learning': [
            'machine learning', 'deep learning', 'neural network', 'tensorflow',
            'pytorch', 'scikit-learn', 'nlp', 'computer vision', 'ai',
            'artificial intelligence', 'data science', 'model training',
            'reinforcement learning', 'llm', 'generative ai'
        ],
        'backend_engineering': [
            'backend', 'server-side', 'api', 'rest', 'graphql', 'microservices',
            'database', 'sql', 'nosql', 'postgresql', 'mongodb', 'redis',
            'django', 'flask', 'fastapi', 'spring', 'node.js', 'express'
        ],
        'frontend_engineering': [
            'frontend', 'frontend', 'react', 'vue', 'angular', 'javascript',
            'typescript', 'css', 'html', 'webpack', 'vite', 'ui', 'ux',
            'responsive design', 'spa', 'dom', 'browser'
        ],
        'data_engineering': [
            'data engineering', 'etl', 'data pipeline', 'apache spark',
            'hadoop', 'kafka', 'airflow', 'dbt', 'data warehouse',
            'big data', 'data modeling', 'snowflake', 'databricks'
        ],
        'devops': [
            'devops', 'sre', 'ci/cd', 'jenkins', 'github actions', 'gitlab',
            'docker', 'kubernetes', 'terraform', 'ansible', 'aws', 'gcp',
            'azure', 'infrastructure', 'monitoring', 'prometheus', 'grafana'
        ],
        'mobile_development': [
            'mobile', 'ios', 'android', 'swift', 'kotlin', 'flutter',
            'react native', 'xamarin', 'app development', 'mobile app'
        ],
        'full_stack': [
            'full stack', 'fullstack', 'end-to-end', 'mern', 'mean',
            'web development', 'web application'
        ]
    }

    # Human-readable domain names
    DOMAIN_NAMES = {
        'machine_learning': 'Machine Learning / AI',
        'backend_engineering': 'Backend Engineering',
        'frontend_engineering': 'Frontend Engineering',
        'data_engineering': 'Data Engineering',
        'devops': 'DevOps / SRE',
        'mobile_development': 'Mobile Development',
        'full_stack': 'Full Stack Development'
    }

    _domain_centroids: Optional[Dict[str, np.ndarray]] = None

    @classmethod
    def _generate_domain_centroids(cls) -> Dict[str, np.ndarray]:
        """
        Generate embedding centroids for each domain.
        
        Returns:
            Dictionary mapping domain keys to centroid embeddings
        """
        if cls._domain_centroids is not None:
            return cls._domain_centroids

        try:
            job_agent = get_job_agent()
            centroids = {}

            for domain_key, keywords in cls.DOMAIN_KEYWORDS.items():
                # Create a representative text for the domain
                domain_text = f"{cls.DOMAIN_NAMES[domain_key]}. " + " ".join(keywords)

                # Generate embedding
                embedding = job_agent.generate_embedding(domain_text)
                centroids[domain_key] = np.array(embedding)

            cls._domain_centroids = centroids

            logger.info(
                "Domain centroids generated",
                domains=list(centroids.keys())
            )

            return centroids

        except Exception as e:
            logger.error(f"Failed to generate domain centroids: {e}")
            return {}

    @classmethod
    def _cosine_similarity(cls, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return float(np.dot(a, b) / (norm_a * norm_b))

    @classmethod
    def detect_domain(cls, text: str) -> Optional[DomainResult]:
        """
        Detect career domain from text (resume or job description).
        
        Args:
            text: Text to analyze (resume content or job description)
            
        Returns:
            DomainResult with primary and secondary domains
        """
        if not text or not text.strip():
            return None

        try:
            # Get domain centroids
            centroids = cls._generate_domain_centroids()
            if not centroids:
                return None

            # Generate embedding for input text
            job_agent = get_job_agent()
            text_embedding = np.array(job_agent.generate_embedding(text))

            # Calculate similarity with each domain
            similarities = {}
            for domain_key, centroid in centroids.items():
                similarity = cls._cosine_similarity(text_embedding, centroid)
                similarities[domain_key] = similarity

            # Sort by similarity
            sorted_domains = sorted(
                similarities.items(),
                key=lambda x: x[1],
                reverse=True
            )

            primary_domain = sorted_domains[0][0]
            primary_confidence = sorted_domains[0][1]

            secondary_domain = None
            secondary_confidence = 0.0

            if len(sorted_domains) > 1:
                secondary_domain = sorted_domains[1][0]
                secondary_confidence = sorted_domains[1][1]

            return DomainResult(
                primary_domain=cls.DOMAIN_NAMES[primary_domain],
                primary_confidence=round(primary_confidence, 3),
                secondary_domain=cls.DOMAIN_NAMES.get(secondary_domain),
                secondary_confidence=round(secondary_confidence, 3),
                all_scores={
                    cls.DOMAIN_NAMES[k]: round(v, 3)
                    for k, v in similarities.items()
                }
            )

        except Exception as e:
            logger.error(f"Failed to detect domain: {e}")
            return None

    @classmethod
    def detect_domain_from_resume(cls, resume_text: str) -> Optional[DomainResult]:
        """
        Detect domain from resume text.
        
        Args:
            resume_text: Resume content
            
        Returns:
            DomainResult
        """
        return cls.detect_domain(resume_text)

    @classmethod
    def detect_domain_from_job(cls, job: Job) -> Optional[DomainResult]:
        """
        Detect domain from job posting.
        
        Args:
            job: Job model instance
            
        Returns:
            DomainResult
        """
        # Combine job title, description, and requirements
        text_parts = [
            job.title or '',
            job.description or '',
            job.requirements or '',
            ' '.join(job.required_skills or [])
        ]
        text = ' '.join(text_parts)

        return cls.detect_domain(text)

    @classmethod
    def get_domain_distribution(cls, limit: int = 100) -> Dict[str, int]:
        """
        Get distribution of domains across active jobs.
        
        Args:
            limit: Maximum number of jobs to analyze
            
        Returns:
            Dictionary with domain counts
        """
        try:
            jobs = Job.query.filter_by(is_active=True).limit(limit).all()

            domain_counts = {}
            for job in jobs:
                result = cls.detect_domain_from_job(job)
                if result:
                    domain = result.primary_domain
                    domain_counts[domain] = domain_counts.get(domain, 0) + 1

            return domain_counts

        except Exception as e:
            logger.error(f"Failed to get domain distribution: {e}")
            return {}

    @classmethod
    def get_recommended_domains(cls, user_domain: str) -> List[Dict]:
        """
        Get recommended related domains for career transition.
        
        Args:
            user_domain: User's current domain
            
        Returns:
            List of related domains with transition difficulty
        """
        # Domain transition graph (simplified)
        transitions = {
            'Machine Learning / AI': [
                {'domain': 'Data Engineering', 'difficulty': 'easy', 'overlap': 0.7},
                {'domain': 'Backend Engineering', 'difficulty': 'medium', 'overlap': 0.5},
                {'domain': 'Full Stack Development', 'difficulty': 'hard', 'overlap': 0.3}
            ],
            'Backend Engineering': [
                {'domain': 'DevOps / SRE', 'difficulty': 'easy', 'overlap': 0.6},
                {'domain': 'Full Stack Development', 'difficulty': 'easy', 'overlap': 0.7},
                {'domain': 'Data Engineering', 'difficulty': 'medium', 'overlap': 0.4}
            ],
            'Frontend Engineering': [
                {'domain': 'Full Stack Development', 'difficulty': 'easy', 'overlap': 0.8},
                {'domain': 'Mobile Development', 'difficulty': 'medium', 'overlap': 0.5}
            ],
            'Data Engineering': [
                {'domain': 'Machine Learning / AI', 'difficulty': 'medium', 'overlap': 0.6},
                {'domain': 'Backend Engineering', 'difficulty': 'easy', 'overlap': 0.5},
                {'domain': 'DevOps / SRE', 'difficulty': 'medium', 'overlap': 0.4}
            ],
            'DevOps / SRE': [
                {'domain': 'Backend Engineering', 'difficulty': 'easy', 'overlap': 0.5},
                {'domain': 'Data Engineering', 'difficulty': 'medium', 'overlap': 0.4}
            ],
            'Mobile Development': [
                {'domain': 'Full Stack Development', 'difficulty': 'medium', 'overlap': 0.5},
                {'domain': 'Frontend Engineering', 'difficulty': 'easy', 'overlap': 0.6}
            ],
            'Full Stack Development': [
                {'domain': 'Backend Engineering', 'difficulty': 'easy', 'overlap': 0.7},
                {'domain': 'Frontend Engineering', 'difficulty': 'easy', 'overlap': 0.7},
                {'domain': 'DevOps / SRE', 'difficulty': 'medium', 'overlap': 0.4}
            ]
        }

        return transitions.get(user_domain, [])
