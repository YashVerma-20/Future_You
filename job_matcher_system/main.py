"""
Job Matcher System - Main Orchestrator

A production-ready job matching system with:
- Multi-source job scraping (Selenium-based)
- PDF resume parsing
- Resume section extraction (regex-based)
- Weighted resume representation
- Rule-based scoring
- TF-IDF similarity
- Sentence-transformer semantic similarity
- Hybrid scoring system
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config import config
from utils import get_logger, is_valid_pdf

from resume.pdf_parser import PDFResumeParser
from resume.section_extractor import ResumeSectionExtractor
from resume.weighted_representation import WeightedResumeRepresentation
from resume.resume_model import Resume

from scrapers.scraper_manager import ScraperManager
from scrapers.base_scraper import JobPosting

from matchers.rule_based_matcher import RuleBasedMatcher
from matchers.tfidf_matcher import TFIDFMatcher
from matchers.semantic_matcher import SemanticMatcher
from matchers.hybrid_matcher import HybridMatcher


logger = get_logger("main")


class JobMatcherSystem:
    """
    Main orchestrator for the job matching system.
    """
    
    def __init__(self):
        self.logger = get_logger("job_matcher_system")
        
        # Resume processing components
        self.pdf_parser = PDFResumeParser()
        self.section_extractor = ResumeSectionExtractor()
        self.weighted_rep = WeightedResumeRepresentation()
        
        # Matching components
        self.rule_matcher = RuleBasedMatcher()
        self.tfidf_matcher = TFIDFMatcher()
        self.semantic_matcher = SemanticMatcher()
        self.hybrid_matcher = HybridMatcher(
            rule_matcher=self.rule_matcher,
            tfidf_matcher=self.tfidf_matcher,
            semantic_matcher=self.semantic_matcher
        )
        
        self.logger.info("Job Matcher System initialized")
    
    def process_resume(self, pdf_path: Path) -> Resume:
        """
        Process a PDF resume through the full pipeline.
        
        Args:
            pdf_path: Path to PDF resume file
            
        Returns:
            Processed Resume object
        """
        self.logger.info(f"Processing resume: {pdf_path}")
        
        # Step 1: Parse PDF
        resume = self.pdf_parser.parse(pdf_path)
        
        # Step 2: Extract sections
        resume = self.section_extractor.extract_sections(resume)
        
        # Step 3: Create weighted representation
        weighted_text = self.weighted_rep.create_weighted_text(resume)
        
        self.logger.info(
            f"Resume processed: {len(resume.sections)} sections, "
            f"{len(resume.skills)} skills, {len(weighted_text)} chars"
        )
        
        return resume
    
    def scrape_jobs(
        self,
        query: str,
        location: Optional[str] = None,
        max_results: int = 20,
        sources: List[str] = None
    ) -> List[JobPosting]:
        """
        Scrape jobs from multiple sources.
        
        Args:
            query: Job search query
            location: Optional location
            max_results: Maximum results per source
            sources: Specific sources to use
            
        Returns:
            List of JobPosting objects
        """
        self.logger.info(f"Scraping jobs: '{query}' in '{location}'")
        
        with ScraperManager() as manager:
            jobs = manager.search_all(
                query=query,
                location=location,
                max_results_per_source=max_results,
                sources=sources
            )
            
            # Save jobs to disk
            manager.save_jobs(jobs)
        
        self.logger.info(f"Scraped {len(jobs)} jobs")
        return jobs
    
    def load_jobs(self, filename: str) -> List[JobPosting]:
        """Load previously scraped jobs."""
        with ScraperManager() as manager:
            return manager.load_jobs(filename)
    
    def match_resume_to_jobs(
        self,
        resume: Resume,
        jobs: List[JobPosting],
        matcher_type: str = "hybrid"
    ) -> List[dict]:
        """
        Match resume to jobs using specified matcher.
        
        Args:
            resume: Processed resume
            jobs: List of job postings
            matcher_type: 'rule', 'tfidf', 'semantic', or 'hybrid'
            
        Returns:
            List of match results as dictionaries
        """
        self.logger.info(f"Matching using {matcher_type} matcher")
        
        # Select matcher
        if matcher_type == "rule":
            matcher = self.rule_matcher
        elif matcher_type == "tfidf":
            matcher = self.tfidf_matcher
            # Fit TF-IDF on job descriptions
            job_texts = [job.description for job in jobs]
            if resume.weighted_text:
                job_texts.append(resume.weighted_text)
            matcher.fit(job_texts)
        elif matcher_type == "semantic":
            matcher = self.semantic_matcher
        else:  # hybrid
            matcher = self.hybrid_matcher
            # Fit TF-IDF component
            job_texts = [job.description for job in jobs]
            if resume.weighted_text:
                job_texts.append(resume.weighted_text)
            self.tfidf_matcher.fit(job_texts)
        
        # Perform matching
        results = matcher.match_batch(resume, jobs)
        
        # Convert to dictionaries
        return [r.to_dict() for r in results]
    
    def run_full_pipeline(
        self,
        resume_path: Path,
        job_query: str,
        location: Optional[str] = None,
        max_jobs: int = 20,
        matcher_type: str = "hybrid"
    ) -> dict:
        """
        Run the complete job matching pipeline.
        
        Args:
            resume_path: Path to PDF resume
            job_query: Job search query
            location: Optional location
            max_jobs: Maximum jobs to scrape
            matcher_type: Matcher to use
            
        Returns:
            Pipeline results dictionary
        """
        self.logger.info("Starting full pipeline")
        
        # Step 1: Process resume
        resume = self.process_resume(resume_path)
        
        # Step 2: Scrape jobs
        jobs = self.scrape_jobs(
            query=job_query,
            location=location,
            max_results=max_jobs
        )
        
        if not jobs:
            self.logger.warning("No jobs found")
            return {
                'success': False,
                'error': 'No jobs found',
                'resume_processed': True,
                'jobs_found': 0
            }
        
        # Step 3: Match resume to jobs
        matches = self.match_resume_to_jobs(
            resume=resume,
            jobs=jobs,
            matcher_type=matcher_type
        )
        
        # Step 4: Prepare results
        results = {
            'success': True,
            'resume_file': str(resume_path),
            'job_query': job_query,
            'location': location,
            'matcher_type': matcher_type,
            'jobs_found': len(jobs),
            'matches': matches,
            'top_matches': matches[:5],
            'resume_summary': {
                'sections': [s.name for s in resume.sections],
                'skills': [s.name for s in resume.skills],
                'experience_years': resume.get_total_experience_years()
            }
        }
        
        self.logger.info(f"Pipeline complete. Top match score: {matches[0]['overall_score'] if matches else 0}")
        
        return results
    
    def save_results(self, results: dict, output_path: Path):
        """Save results to JSON file."""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        self.logger.info(f"Results saved to {output_path}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Job Matcher System - Match resumes to job postings"
    )
    
    parser.add_argument(
        "--resume", "-r",
        type=str,
        required=True,
        help="Path to PDF resume file"
    )
    
    parser.add_argument(
        "--query", "-q",
        type=str,
        required=True,
        help="Job search query (e.g., 'python developer')"
    )
    
    parser.add_argument(
        "--location", "-l",
        type=str,
        default=None,
        help="Job location (e.g., 'New York, NY')"
    )
    
    parser.add_argument(
        "--max-jobs", "-n",
        type=int,
        default=20,
        help="Maximum number of jobs to scrape (default: 20)"
    )
    
    parser.add_argument(
        "--matcher", "-m",
        type=str,
        choices=['rule', 'tfidf', 'semantic', 'hybrid'],
        default='hybrid',
        help="Matching algorithm to use (default: hybrid)"
    )
    
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Output file path for results (default: auto-generated)"
    )
    
    parser.add_argument(
        "--jobs-file", "-j",
        type=str,
        default=None,
        help="Load jobs from file instead of scraping"
    )
    
    args = parser.parse_args()
    
    # Validate resume path
    resume_path = Path(args.resume)
    if not resume_path.exists():
        print(f"Error: Resume file not found: {resume_path}")
        sys.exit(1)
    
    if not is_valid_pdf(str(resume_path)):
        print(f"Error: File is not a valid PDF: {resume_path}")
        sys.exit(1)
    
    # Initialize system
    system = JobMatcherSystem()
    
    # Process resume
    print(f"Processing resume: {resume_path}")
    resume = system.process_resume(resume_path)
    print(f"  ✓ Extracted {len(resume.sections)} sections")
    print(f"  ✓ Found {len(resume.skills)} skills")
    print(f"  ✓ {resume.get_total_experience_years():.1f} years experience")
    
    # Get jobs
    if args.jobs_file:
        print(f"\nLoading jobs from: {args.jobs_file}")
        jobs = system.load_jobs(args.jobs_file)
    else:
        print(f"\nScraping jobs for: '{args.query}'")
        if args.location:
            print(f"  Location: {args.location}")
        
        try:
            jobs = system.scrape_jobs(
                query=args.query,
                location=args.location,
                max_results=args.max_jobs
            )
        except Exception as e:
            print(f"Error scraping jobs: {e}")
            print("Tip: Use --jobs-file to load previously scraped jobs")
            sys.exit(1)
    
    print(f"  ✓ Found {len(jobs)} jobs")
    
    if not jobs:
        print("\nNo jobs found. Exiting.")
        sys.exit(0)
    
    # Match resume to jobs
    print(f"\nMatching using {args.matcher} algorithm...")
    matches = system.match_resume_to_jobs(
        resume=resume,
        jobs=jobs,
        matcher_type=args.matcher
    )
    
    # Display results
    print(f"\n{'='*60}")
    print("TOP 5 MATCHES")
    print(f"{'='*60}")
    
    for i, match in enumerate(matches[:5], 1):
        job = next((j for j in jobs if j.id == match['job_id']), None)
        if job:
            print(f"\n{i}. {job.title}")
            print(f"   Company: {job.company}")
            print(f"   Location: {job.location}")
            print(f"   Match Score: {match['overall_score']:.1%}")
            
            if match.get('rule_based_score'):
                print(f"   - Rule-based: {match['rule_based_score']:.2f}")
            if match.get('tfidf_score'):
                print(f"   - TF-IDF: {match['tfidf_score']:.2f}")
            if match.get('semantic_score'):
                print(f"   - Semantic: {match['semantic_score']:.2f}")
            
            if match.get('matching_skills'):
                skills_str = ', '.join(match['matching_skills'][:5])
                print(f"   Matching Skills: {skills_str}")
            
            if match.get('explanation'):
                print(f"   {match['explanation'][:100]}...")
    
    # Save results
    if args.output:
        output_path = Path(args.output)
    else:
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = config.paths.data_dir / f"match_results_{timestamp}.json"
    
    results = {
        'resume_file': str(resume_path),
        'job_query': args.query,
        'location': args.location,
        'matcher_type': args.matcher,
        'jobs_found': len(jobs),
        'matches': matches
    }
    
    system.save_results(results, output_path)
    print(f"\n{'='*60}")
    print(f"Results saved to: {output_path}")


if __name__ == "__main__":
    main()
