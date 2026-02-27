"""Validation utilities."""
import re
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse


def validate_url(url: str) -> bool:
    """Validate URL format."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False


def validate_file_path(path: str, must_exist: bool = False) -> Optional[Path]:
    """Validate file path."""
    try:
        p = Path(path)
        if must_exist and not p.exists():
            return None
        return p
    except:
        return None


def is_valid_pdf(path: str) -> bool:
    """Check if file is a valid PDF."""
    p = Path(path)
    if not p.exists() or not p.is_file():
        return False
    return p.suffix.lower() == '.pdf'
