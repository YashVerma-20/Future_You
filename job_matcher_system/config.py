"""Configuration management for Job Matcher System."""
import os
from dataclasses import dataclass, field
from typing import Dict
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


@dataclass
class ScrapingConfig:
    """Configuration for web scraping."""
    headless: bool = True
    timeout: int = 30
    request_delay: float = 2.0
    max_retries: int = 3
    requests_per_minute: int = 10


@dataclass
class ModelConfig:
    """Configuration for ML models."""
    sentence_transformer_model: str = "all-MiniLM-L6-v2"
    tfidf_max_features: int = 5000
    tfidf_ngram_range: tuple = (1, 2)


@dataclass
class ScoringConfig:
    """Configuration for scoring algorithms."""
    rule_based_weight: float = 0.25
    tfidf_weight: float = 0.25
    semantic_weight: float = 0.50
    min_match_score: float = 0.3
    high_match_threshold: float = 0.75


@dataclass
class ResumeConfig:
    """Configuration for resume processing."""
    section_weights: Dict[str, float] = field(default_factory=lambda: {
        'summary': 0.15,
        'experience': 0.40,
        'skills': 0.25,
        'education': 0.15,
        'projects': 0.05
    })


class Config:
    """Main configuration class."""
    
    def __init__(self):
        self.scraping = ScrapingConfig()
        self.model = ModelConfig()
        self.scoring = ScoringConfig()
        self.resume = ResumeConfig()
        self.base_dir = Path(__file__).parent


config = Config()
