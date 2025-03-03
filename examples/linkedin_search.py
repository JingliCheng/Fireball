"""
Example script demonstrating LinkedIn job search functionality using browser-use.
"""
import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from fireball.job_search.linkedin import LinkedInJobSearch
from fireball.storage.json_store import JsonStorageManager

async def main():
    # Load environment variables
    load_dotenv()
    
    # Initialize storage
    storage = JsonStorageManager()
    
    # Initialize LinkedIn job search
    linkedin = LinkedInJobSearch({
        "username": os.getenv("LINKEDIN_USERNAME"),
        "password": os.getenv("LINKEDIN_PASSWORD")
    })
    
    try:
        # Login to LinkedIn
        await linkedin.login()
        print("Successfully logged in to LinkedIn")
        
        # Search for jobs
        print("Searching for Python developer positions...")
        async for job in linkedin.search_jobs(
            keywords=["python developer"],
            location="United States",
            experience_levels=["entry", "mid-senior"]
        ):
            print(f"\nFound job: {job.job_title}")
            print(f"Company: {job.company_name}")
            print(f"Location: {job.location}")
            print(f"Posted: {job.posted_days_ago}")
            print(f"Apply type: {job.apply_type}")
            print(f"Apply link: {job.apply_link}")
            
            # Store job in JSON storage
            storage.add_job(job)
        
        print("\nJob search completed. All jobs have been stored.")
    
    finally:
        # Ensure browser is closed
        await linkedin.close()

if __name__ == "__main__":
    asyncio.run(main()) 