"""PDF text extraction utility."""
import io
from typing import Optional
import PyPDF2
import structlog

logger = structlog.get_logger()


def extract_text_from_pdf(file_content: bytes) -> Optional[str]:
    """
    Extract text from PDF file content.
    
    Args:
        file_content: PDF file content as bytes
        
    Returns:
        Extracted text or None if extraction fails
    """
    try:
        pdf_file = io.BytesIO(file_content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        text = ""
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        
        logger.info(f"Extracted {len(text)} characters from PDF")
        return text.strip() if text else None
        
    except Exception as e:
        logger.error(f"PDF extraction failed: {e}")
        return None


def extract_pdf_metadata(file_content: bytes) -> dict:
    """
    Extract metadata from PDF file.
    
    Args:
        file_content: PDF file content as bytes
        
    Returns:
        Dictionary containing PDF metadata
    """
    try:
        pdf_file = io.BytesIO(file_content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        metadata = {
            'num_pages': len(pdf_reader.pages),
            'metadata': {}
        }
        
        if pdf_reader.metadata:
            meta = pdf_reader.metadata
            metadata['metadata'] = {
                'title': meta.get('/Title', ''),
                'author': meta.get('/Author', ''),
                'creator': meta.get('/Creator', ''),
                'producer': meta.get('/Producer', ''),
                'subject': meta.get('/Subject', ''),
            }
        
        return metadata
        
    except Exception as e:
        logger.error(f"PDF metadata extraction failed: {e}")
        return {'num_pages': 0, 'metadata': {}}
