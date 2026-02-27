"""Script to delete all mock jobs from the database."""
import os
import sys

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.extensions import db
from app.models.job import Job
from sqlalchemy import text

app = create_app()

with app.app_context():
    # Find all mock jobs
    mock_jobs = Job.query.filter_by(source_platform='mock').all()
    
    print(f"Found {len(mock_jobs)} mock jobs to delete")
    
    if not mock_jobs:
        print("No mock jobs found in the database.")
        sys.exit(0)
    
    # Show what will be deleted
    print("\nMock jobs to be deleted:")
    for job in mock_jobs:
        print(f"  - {job.title} at {job.company.name if job.company else 'Unknown'} (ID: {job.id})")
    
    # Confirm deletion
    confirm = input(f"\nDelete {len(mock_jobs)} mock jobs? (yes/no): ")
    
    if confirm.lower() == 'yes':
        # Delete mock jobs
        deleted_count = 0
        for job in mock_jobs:
            db.session.delete(job)
            deleted_count += 1
        
        db.session.commit()
        print(f"\nSuccessfully deleted {deleted_count} mock jobs.")
    else:
        print("\nDeletion cancelled.")
