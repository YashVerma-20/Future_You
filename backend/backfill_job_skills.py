"""Script to backfill skills for existing jobs in the database."""
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.extensions import db
from app.models.job import Job
from app.agents.job_agent import JobAgent


def backfill_job_skills():
    """Backfill skills for all existing jobs that don't have them."""
    app = create_app()
    
    with app.app_context():
        print("Initializing JobAgent...")
        job_agent = JobAgent()
        
        print("Fetching all jobs from database...")
        all_jobs = Job.query.all()
        print(f"Total jobs in database: {len(all_jobs)}")
        
        jobs_without_skills = [job for job in all_jobs if not job.required_skills]
        print(f"Jobs without skills: {len(jobs_without_skills)}")
        
        if jobs_without_skills:
            print("\nBackfilling skills for jobs without skill data...")
            updated_count = 0
            
            for i, job in enumerate(jobs_without_skills):
                try:
                    # Process the job description to extract skills
                    processed = job_agent.process_job_description(
                        description=job.description,
                        requirements=job.requirements,
                        responsibilities=job.responsibilities
                    )
                    
                    # Update the job with extracted skills
                    job.required_skills = processed["skill_names"]
                    
                    # Commit in batches to avoid memory issues
                    if i % 50 == 0:
                        db.session.commit()
                        print(f"  Updated {i+1}/{len(jobs_without_skills)} jobs...")
                    
                    updated_count += 1
                    
                except Exception as e:
                    print(f"  Error processing job {job.id}: {e}")
                    db.session.rollback()  # Rollback on error to maintain data integrity
        
            # Final commit
            try:
                db.session.commit()
                print(f"\n✅ Successfully updated {updated_count} jobs with skill data!")
                
                # Verify the update
                jobs_with_skills = Job.query.filter(Job.required_skills.isnot(None)).filter(Job.required_skills != []).count()
                print(f"Jobs now with skills: {jobs_with_skills}")
                
            except Exception as e:
                print(f"Error committing final batch: {e}")
                db.session.rollback()
        else:
            print("\n✅ No jobs without skills found. All jobs already have skill data.")


if __name__ == '__main__':
    backfill_job_skills()