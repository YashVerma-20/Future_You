# Job Matcher System

A production-ready, modular Python project for matching resumes to job postings using multiple AI/ML approaches.

## Features

### Scraping Engine
- **Multi-source Selenium-based scraping** with anti-detection measures
- Support for Indeed (extensible to LinkedIn, Glassdoor)
- Rate limiting and human-like behavior
- Structured job posting data extraction

### Resume Processing
- **PDF parsing** using PyPDF2 and pdfplumber
- **Regex-based section extraction** (Experience, Education, Skills, etc.)
- **Weighted representation** emphasizing important sections
- Structured data models for Resume, Experience, Education, Skills

### Matching Engines

1. **Rule-Based Scoring**
   - Explicit matching rules for skills, experience, education
   - Interpretable scores with explanations
   - Configurable weights

2. **TF-IDF Similarity**
   - Term frequency-inverse document frequency
   - Fast keyword-based matching
   - N-gram support

3. **Semantic Similarity**
   - Sentence-transformer embeddings
   - Context-aware matching beyond keywords
   - Section-level embeddings support

4. **Hybrid Scoring**
   - Combines all three approaches
   - Configurable weights (default: 25% rule, 25% TF-IDF, 50% semantic)
   - Best overall accuracy

## Project Structure

```
job_matcher_system/
├── config.py                 # Configuration management
├── requirements.txt          # Dependencies
├── main.py                   # CLI entry point
│
├── scrapers/                 # Job scraping modules
│   ├── base_scraper.py       # Abstract base class
│   ├── selenium_scraper.py   # Selenium base with anti-detection
│   ├── indeed_scraper.py     # Indeed.com scraper
│   └── scraper_manager.py    # Multi-source coordination
│
├── resume/                   # Resume processing modules
│   ├── resume_model.py       # Data models (Resume, Section, etc.)
│   ├── pdf_parser.py         # PDF text extraction
│   ├── section_extractor.py  # Regex-based section extraction
│   └── weighted_representation.py  # Weighted text creation
│
├── matchers/                 # Matching engines
│   ├── base_matcher.py       # Abstract base class
│   ├── rule_based_matcher.py # Rule-based scoring
│   ├── tfidf_matcher.py      # TF-IDF similarity
│   ├── semantic_matcher.py   # Sentence-transformer similarity
│   └── hybrid_matcher.py     # Combined approach
│
├── utils/                    # Utility modules
│   ├── logger.py             # Structured logging
│   ├── text_cleaner.py       # Text normalization
│   └── validators.py         # Input validation
│
├── data/                     # Data directory
├── jobs/                     # Scraped jobs storage
├── logs/                     # Log files
└── models/                   # Saved model files
```

## Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Download NLTK data (if using NLP features)
python -c "import nltk; nltk.download('punkt')"
```

## Usage

### Command Line

```bash
# Basic usage with hybrid matcher (recommended)
python main.py --resume path/to/resume.pdf --query "python developer"

# With location
python main.py -r resume.pdf -q "software engineer" -l "New York, NY"

# Use specific matcher
python main.py -r resume.pdf -q "data scientist" -m semantic

# Load previously scraped jobs
python main.py -r resume.pdf -q "web developer" -j jobs_20240115_143022.json

# Save results to specific file
python main.py -r resume.pdf -q "ml engineer" -o my_results.json
```

### Python API

```python
from main import JobMatcherSystem
from pathlib import Path

# Initialize system
system = JobMatcherSystem()

# Process resume
resume = system.process_resume(Path("resume.pdf"))

# Scrape jobs
jobs = system.scrape_jobs(
    query="python developer",
    location="San Francisco, CA",
    max_results=30
)

# Match using hybrid approach
matches = system.match_resume_to_jobs(
    resume=resume,
    jobs=jobs,
    matcher_type="hybrid"
)

# Print top matches
for match in matches[:5]:
    print(f"Job: {match['job_id']}")
    print(f"Score: {match['overall_score']:.2f}")
    print(f"Explanation: {match['explanation']}")
```

### Individual Components

```python
# Resume processing
from resume.pdf_parser import PDFResumeParser
from resume.section_extractor import ResumeSectionExtractor

parser = PDFResumeParser()
resume = parser.parse("resume.pdf")

extractor = ResumeSectionExtractor()
resume = extractor.extract_sections(resume)

# Matching
from matchers.hybrid_matcher import HybridMatcher

matcher = HybridMatcher()
result = matcher.match(resume, job_posting)
print(f"Match score: {result.overall_score}")
```

## Configuration

Create a `.env` file:

```env
# Scraping
SELENIUM_HEADLESS=true
SELENIUM_TIMEOUT=30
REQUEST_DELAY=2

# Models
SENTENCE_TRANSFORMER_MODEL=all-MiniLM-L6-v2
TFIDF_MAX_FEATURES=5000

# Scoring Weights
RULE_BASED_WEIGHT=0.25
TFIDF_WEIGHT=0.25
SEMANTIC_WEIGHT=0.50
```

Or modify `config.py` directly.

## Algorithm Details

### Rule-Based Scoring
- **Skills (40%)**: Exact and partial skill matching
- **Experience (30%)**: Years of experience comparison
- **Education (15%)**: Degree level matching
- **Location (10%)**: Geographic matching
- **Job Type (5%)**: Employment type matching

### TF-IDF Similarity
- Vectorizes resume and job descriptions
- Calculates cosine similarity
- Configurable n-grams (default: 1-2)
- Top 5000 features by default

### Semantic Similarity
- Uses `all-MiniLM-L6-v2` sentence transformer
- 384-dimensional embeddings
- Cosine similarity calculation
- Context-aware matching

### Hybrid Scoring
```
Final Score = 
    0.25 × Rule-Based +
    0.25 × TF-IDF +
    0.50 × Semantic
```

## Extending the System

### Adding a New Scraper

```python
from scrapers.selenium_scraper import SeleniumJobScraper, JobPosting

class LinkedInScraper(SeleniumJobScraper):
    def search_jobs(self, query, location=None, max_results=10):
        # Implementation
        pass
```

### Adding a New Matcher

```python
from matchers.base_matcher import BaseMatcher, MatchResult

class CustomMatcher(BaseMatcher):
    def match(self, resume, job):
        # Calculate score
        score = ...
        return MatchResult(
            job_id=job.id,
            resume_id=str(id(resume)),
            overall_score=score
        )
```

## License

MIT License
