"""
Example usage of the Job Matcher System.

This script demonstrates how to use the system programmatically.
"""

from pathlib import Path
from main import JobMatcherSystem


def example_basic_usage():
    """Basic usage example."""
    print("=" * 60)
    print("EXAMPLE 1: Basic Usage")
    print("=" * 60)
    
    # Initialize the system
    system = JobMatcherSystem()
    
    # Process a resume
    resume_path = Path("data/sample_resume.pdf")
    if not resume_path.exists():
        print(f"Note: {resume_path} not found. Using mock data.")
        return
    
    resume = system.process_resume(resume_path)
    
    print(f"Resume processed successfully!")
    print(f"  Sections found: {len(resume.sections)}")
    print(f"  Skills extracted: {len(resume.skills)}")
    print(f"  Experience entries: {len(resume.experience)}")
    print(f"  Education entries: {len(resume.education)}")
    
    # Display extracted skills
    if resume.skills:
        print(f"\nExtracted Skills:")
        for skill in resume.skills[:10]:
            print(f"  - {skill.name} ({skill.category or 'unknown'})")


def example_scrape_and_match():
    """Example of scraping jobs and matching."""
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Scrape and Match")
    print("=" * 60)
    
    system = JobMatcherSystem()
    
    # Scrape jobs (in real usage, this would actually scrape)
    print("\nScraping jobs...")
    print("Note: This would scrape Indeed in production.")
    print("For demo, we'll use mock jobs.")
    
    # Create mock jobs for demonstration
    from scrapers.base_scraper import JobPosting
    
    mock_jobs = [
        JobPosting(
            id="job_1",
            title="Python Developer",
            company="Tech Corp",
            location="New York, NY",
            description="Looking for a Python developer with Django experience. Must know SQL and Git.",
            requirements=["3+ years Python", "Django", "SQL"],
            skills_required=["python", "django", "sql", "git"]
        ),
        JobPosting(
            id="job_2",
            title="Data Scientist",
            company="Data Inc",
            location="Remote",
            description="Seeking data scientist with machine learning and Python experience.",
            requirements=["Python", "Machine Learning", "SQL"],
            skills_required=["python", "machine learning", "sql", "pandas"],
            remote=True
        ),
        JobPosting(
            id="job_3",
            title="Full Stack Developer",
            company="Web Solutions",
            location="San Francisco, CA",
            description="Full stack role requiring React, Node.js, and database skills.",
            requirements=["React", "Node.js", "MongoDB"],
            skills_required=["react", "node.js", "mongodb", "javascript"]
        )
    ]
    
    # Create a mock resume
    from resume.resume_model import Resume, Skill
    
    mock_resume = Resume(
        raw_text="Python developer with 5 years experience. Skills: Python, Django, SQL, Git, AWS.",
        skills=[
            Skill(name="python", category="programming"),
            Skill(name="django", category="framework"),
            Skill(name="sql", category="database"),
            Skill(name="git", category="tools"),
            Skill(name="aws", category="cloud")
        ]
    )
    
    # Match using different algorithms
    for matcher_type in ["rule", "tfidf", "semantic", "hybrid"]:
        print(f"\n--- Using {matcher_type.upper()} matcher ---")
        
        results = system.match_resume_to_jobs(
            resume=mock_resume,
            jobs=mock_jobs,
            matcher_type=matcher_type
        )
        
        for i, result in enumerate(results[:3], 1):
            job = next(j for j in mock_jobs if j.id == result['job_id'])
            print(f"{i}. {job.title} at {job.company}")
            print(f"   Score: {result['overall_score']:.2f}")
            if result.get('explanation'):
                print(f"   {result['explanation'][:80]}...")


def example_component_usage():
    """Example using individual components."""
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Individual Components")
    print("=" * 60)
    
    # PDF Parser only
    print("\n--- PDF Parser ---")
    from resume.pdf_parser import PDFResumeParser
    
    parser = PDFResumeParser()
    print("PDFParser initialized")
    print("Methods: parse(), parse_bytes(), extract_contact_info()")
    
    # Section Extractor only
    print("\n--- Section Extractor ---")
    from resume.section_extractor import ResumeSectionExtractor
    
    extractor = ResumeSectionExtractor()
    print("SectionExtractor initialized")
    print("Patterns:", [p.name for p in extractor.SECTION_PATTERNS])
    
    # Rule-based Matcher only
    print("\n--- Rule-Based Matcher ---")
    from matchers.rule_based_matcher import RuleBasedMatcher
    
    rule_matcher = RuleBasedMatcher()
    print("RuleBasedMatcher initialized")
    print("Weights:", rule_matcher.weights)
    
    # TF-IDF Matcher only
    print("\n--- TF-IDF Matcher ---")
    from matchers.tfidf_matcher import TFIDFMatcher
    
    tfidf_matcher = TFIDFMatcher()
    print("TFIDFMatcher initialized")
    print(f"Max features: {tfidf_matcher.vectorizer.max_features}")
    
    # Semantic Matcher only
    print("\n--- Semantic Matcher ---")
    from matchers.semantic_matcher import SemanticMatcher
    
    semantic_matcher = SemanticMatcher()
    print("SemanticMatcher initialized")
    print(f"Model: {semantic_matcher.model_name}")


def example_custom_weights():
    """Example with custom hybrid weights."""
    print("\n" + "=" * 60)
    print("EXAMPLE 4: Custom Hybrid Weights")
    print("=" * 60)
    
    from matchers.hybrid_matcher import HybridMatcher, HybridWeights
    
    # Create matcher with custom weights
    custom_weights = HybridWeights(
        rule_based=0.5,   # Emphasize explicit rules
        tfidf=0.2,
        semantic=0.3
    )
    
    custom_matcher = HybridMatcher(weights=custom_weights)
    
    print("Custom hybrid matcher created:")
    print(f"  Rule-based weight: {custom_matcher.weights.rule_based}")
    print(f"  TF-IDF weight: {custom_matcher.weights.tfidf}")
    print(f"  Semantic weight: {custom_matcher.weights.semantic}")


def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("JOB MATCHER SYSTEM - EXAMPLES")
    print("=" * 60)
    
    # Run examples
    example_basic_usage()
    example_scrape_and_match()
    example_component_usage()
    example_custom_weights()
    
    print("\n" + "=" * 60)
    print("Examples complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
