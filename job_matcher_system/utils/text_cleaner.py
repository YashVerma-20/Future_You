"""Text cleaning and normalization utilities."""
import re
import string
from typing import List


class TextCleaner:
    """Clean and normalize text data."""
    
    @staticmethod
    def clean(text: str) -> str:
        """Apply all cleaning steps."""
        if not text:
            return ""
        
        text = TextCleaner.remove_urls(text)
        text = TextCleaner.remove_emails(text)
        text = TextCleaner.remove_phone_numbers(text)
        text = TextCleaner.remove_special_chars(text)
        text = TextCleaner.normalize_whitespace(text)
        text = text.lower().strip()
        
        return text
    
    @staticmethod
    def remove_urls(text: str) -> str:
        """Remove URLs from text."""
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        return re.sub(url_pattern, '', text)
    
    @staticmethod
    def remove_emails(text: str) -> str:
        """Remove email addresses."""
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        return re.sub(email_pattern, '', text)
    
    @staticmethod
    def remove_phone_numbers(text: str) -> str:
        """Remove phone numbers."""
        phone_pattern = r'\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b'
        return re.sub(phone_pattern, '', text)
    
    @staticmethod
    def remove_special_chars(text: str) -> str:
        """Remove special characters but keep basic punctuation."""
        allowed = string.ascii_letters + string.digits + string.whitespace + '.,;:!?-'
        return ''.join(c for c in text if c in allowed)
    
    @staticmethod
    def normalize_whitespace(text: str) -> str:
        """Normalize whitespace."""
        return ' '.join(text.split())
    
    @staticmethod
    def tokenize(text: str) -> List[str]:
        """Simple tokenization."""
        return text.lower().split()
