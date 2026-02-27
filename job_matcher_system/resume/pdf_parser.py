"""PDF resume parser using multiple extraction methods."""
import re
from pathlib import Path
from typing import Optional, Dict, Any
import io

import PyPDF2
import pdfplumber

from .resume_model import Resume
from utils import get_logger, TextCleaner


class PDFResumeParser:
    """
    Parse PDF resumes using multiple extraction strategies.
    """
    
    def __init__(self):
        self.logger = get_logger("pdf_parser")
        self.text_cleaner = TextCleaner()
    
    def parse(self, file_path: Path) -> Resume:
        """
        Parse a PDF resume file.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            Resume object with extracted text
        """
        self.logger.info(f"Parsing PDF: {file_path}")
        
        # Try multiple extraction methods
        raw_text = self._extract_with_pdfplumber(file_path)
        
        if not raw_text or len(raw_text) < 100:
            self.logger.warning("pdfplumber extraction failed, trying PyPDF2")
            raw_text = self._extract_with_pypdf2(file_path)
        
        if not raw_text or len(raw_text) < 100:
            raise ValueError(f"Failed to extract text from {file_path}")
        
        # Clean the text
        cleaned_text = self.text_cleaner.clean(raw_text)
        
        # Extract metadata
        metadata = self._extract_metadata(file_path)
        
        resume = Resume(
            raw_text=cleaned_text,
            file_path=file_path
        )
        
        self.logger.info(f"Successfully parsed PDF: {len(cleaned_text)} characters")
        
        return resume
    
    def parse_bytes(self, pdf_bytes: bytes, filename: str = "resume.pdf") -> Resume:
        """
        Parse PDF from bytes.
        
        Args:
            pdf_bytes: PDF file content as bytes
            filename: Original filename
            
        Returns:
            Resume object
        """
        self.logger.info(f"Parsing PDF from bytes: {filename}")
        
        # Try pdfplumber first
        raw_text = self._extract_bytes_with_pdfplumber(pdf_bytes)
        
        if not raw_text or len(raw_text) < 100:
            raw_text = self._extract_bytes_with_pypdf2(pdf_bytes)
        
        if not raw_text or len(raw_text) < 100:
            raise ValueError("Failed to extract text from PDF bytes")
        
        cleaned_text = self.text_cleaner.clean(raw_text)
        
        return Resume(
            raw_text=cleaned_text,
            file_path=Path(filename)
        )
    
    def _extract_with_pdfplumber(self, file_path: Path) -> str:
        """Extract text using pdfplumber."""
        text = ""
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as e:
            self.logger.error(f"pdfplumber extraction failed: {e}")
        
        return text
    
    def _extract_with_pypdf2(self, file_path: Path) -> str:
        """Extract text using PyPDF2."""
        text = ""
        try:
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as e:
            self.logger.error(f"PyPDF2 extraction failed: {e}")
        
        return text
    
    def _extract_bytes_with_pdfplumber(self, pdf_bytes: bytes) -> str:
        """Extract text from bytes using pdfplumber."""
        text = ""
        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as e:
            self.logger.error(f"pdfplumber bytes extraction failed: {e}")
        
        return text
    
    def _extract_bytes_with_pypdf2(self, pdf_bytes: bytes) -> str:
        """Extract text from bytes using PyPDF2."""
        text = ""
        try:
            reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        except Exception as e:
            self.logger.error(f"PyPDF2 bytes extraction failed: {e}")
        
        return text
    
    def _extract_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract PDF metadata."""
        metadata = {}
        try:
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                if reader.metadata:
                    metadata = {
                        'author': reader.metadata.get('/Author'),
                        'creator': reader.metadata.get('/Creator'),
                        'producer': reader.metadata.get('/Producer'),
                        'subject': reader.metadata.get('/Subject'),
                        'title': reader.metadata.get('/Title'),
                        'num_pages': len(reader.pages)
                    }
        except Exception as e:
            self.logger.warning(f"Failed to extract metadata: {e}")
        
        return metadata
    
    def extract_contact_info(self, text: str) -> Dict[str, Any]:
        """Extract contact information from resume text."""
        contact_info = {}
        
        # Email pattern
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        if emails:
            contact_info['email'] = emails[0]
        
        # Phone pattern
        phone_pattern = r'\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b'
        phones = re.findall(phone_pattern, text)
        if phones:
            contact_info['phone'] = phones[0]
        
        # LinkedIn
        linkedin_pattern = r'linkedin\.com/in/[a-zA-Z0-9_-]+'
        linkedin = re.findall(linkedin_pattern, text, re.IGNORECASE)
        if linkedin:
            contact_info['linkedin'] = linkedin[0]
        
        # GitHub
        github_pattern = r'github\.com/[a-zA-Z0-9_-]+'
        github = re.findall(github_pattern, text, re.IGNORECASE)
        if github:
            contact_info['github'] = github[0]
        
        return contact_info
