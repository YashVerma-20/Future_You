"""Script to remove all non-Indian jobs from the database."""
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.extensions import db
from app.models.job import Job
from sqlalchemy import text

# India-related keywords to check in location
INDIA_KEYWORDS = [
    'india', 'bangalore', 'bengaluru', 'mumbai', 'delhi', 'pune', 
    'hyderabad', 'chennai', 'kolkata', 'gurgaon', 'gurugram', 'noida',
    'ahmedabad', 'jaipur', 'lucknow', 'kanpur', 'nagpur', 'indore',
    'thane', 'bhopal', 'visakhapatnam', 'vadodara', 'firozabad',
    'ludhiana', 'rajkot', 'agra', 'siliguri', 'durgapur', 'chandigarh',
    'coimbatore', 'mysore', 'trivandrum', 'kochi', 'goa', 'remote',
    'work from home', 'wfh', 'anywhere'
]

# India-focused job platforms
INDIA_PLATFORMS = ['indeed', 'internshala', 'naukri']

def is_indian_job(job):
    """Check if a job is an India job based on location or source platform."""
    # Check if job is from India-focused platform
    if job.source_platform and job.source_platform.lower() in INDIA_PLATFORMS:
        return True
    
    # Check if location contains India keywords
    if job.location:
        location_lower = job.location.lower()
        if any(keyword in location_lower for keyword in INDIA_KEYWORDS):
            return True
    
    # If no location specified but from India platform, it's likely India job
    if not job.location and job.source_platform and job.source_platform.lower() in INDIA_PLATFORMS:
        return True
    
    return False

def remove_non_indian_jobs():
    """Remove all non-Indian jobs from the database."""
    app = create_app()
    
    with app.app_context():
        print("Fetching all jobs from database...")
        all_jobs = Job.query.all()
        print(f"Total jobs in database: {len(all_jobs)}")
        
        # Categorize jobs
        indian_jobs = []
        non_indian_jobs = []
        
        for job in all_jobs:
            if is_indian_job(job):
                indian_jobs.append(job)
            else:
                non_indian_jobs.append(job)
        
        print(f"\nIndian jobs: {len(indian_jobs)}")
        print(f"Non-Indian jobs to delete: {len(non_indian_jobs)}")
        
        if non_indian_jobs:
            print("\nNon-Indian jobs found:")
            for job in non_indian_jobs[:20]:  # Show first 20
                print(f"  - {job.title} | {job.location or 'No location'} | {job.source_platform or 'No platform'}")
            
            if len(non_indian_jobs) > 20:
                print(f"  ... and {len(non_indian_jobs) - 20} more")
            
            # Confirm deletion
            confirm = input(f"\nDelete {len(non_indian_jobs)} non-Indian jobs? (yes/no): ")
            
            if confirm.lower() == 'yes':
                print("\nDeleting non-Indian jobs...")
                deleted_count = 0
                for job in non_indian_jobs:
                    db.session.delete(job)
                    deleted_count += 1
                    
                    # Commit in batches to avoid memory issues
                    if deleted_count % 100 == 0:
                        db.session.commit()
                        print(f"  Deleted {deleted_count}/{len(non_indian_jobs)} jobs...")
                
                # Final commit
                db.session.commit()
                print(f"\n✅ Successfully deleted {deleted_count} non-Indian jobs!")
                print(f"Remaining jobs in database: {len(indian_jobs)}")
            else:
                print("\nDeletion cancelled.")
        else:
            print("\n✅ No non-Indian jobs found. All jobs are India-based.")

if __name__ == '__main__':
    remove_non_indian_jobs()
