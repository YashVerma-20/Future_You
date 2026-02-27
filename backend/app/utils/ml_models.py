"""Shared ML model singleton to prevent duplicate loading."""
import os
from sentence_transformers import SentenceTransformer
import structlog

logger = structlog.get_logger()

# Global singleton instance
_sentence_transformer_model = None


def get_sentence_transformer():
    """Get or create the sentence transformer model singleton."""
    global _sentence_transformer_model
    
    if _sentence_transformer_model is None:
        try:
            model_name = os.environ.get(
                "SENTENCE_TRANSFORMER_MODEL", 
                "all-MiniLM-L6-v2"
            )
            _sentence_transformer_model = SentenceTransformer(model_name)
            logger.info(f"Loaded sentence transformer model: {model_name}")
        except Exception as e:
            logger.error(f"Failed to load sentence transformer model: {e}")
            raise
    
    return _sentence_transformer_model
