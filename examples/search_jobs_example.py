"""
Example script demonstrating job search using Fireball.

Required environment variables in .env:
- LINKEDIN_USERNAME: Your LinkedIn username
- LINKEDIN_PASSWORD: Your LinkedIn password
Optional:
- CHROME_PATH: Path to Chrome executable
- GEMINI_API_KEY: API key for Gemini model
"""
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from fireball.interfaces.interface import Fireball

async def main():
    # Load environment variables
    load_dotenv()
    
    # Initialize Fireball with credentials
    fireball = Fireball(
        linkedin_credentials={
            "username": os.getenv("LINKEDIN_USERNAME"),
            "password": os.getenv("LINKEDIN_PASSWORD")
        },
        chrome_path=os.getenv("CHROME_PATH")  # Optional: use specific Chrome path
    )
    
    try:
        # Example 1: Basic job search with job IDs
        job_ids = await fireball.search_jobs(
            keywords="software engineer",
            location="United States",
            experience_levels=["entry", "mid-senior"],
            store_details=True  # This will store full job details in storage
        )
        
        # Verify storage
        print("\nVerifying storage...")
        data_dir = Path(__file__).parent.parent / "data" / "active"
        job_ids_file = data_dir / "job_ids.json"
        jobs_file = data_dir / "jobs.jsonl"
        
        if job_ids_file.exists():
            print(f"✓ Job IDs file created: {job_ids_file}")
        else:
            print(f"✗ Job IDs file not found: {job_ids_file}")
            
        if jobs_file.exists():
            print(f"✓ Jobs file created: {jobs_file}")
        else:
            print(f"✗ Jobs file not found: {jobs_file}")
    
    finally:
        print("\nClosing browser...")
        await fireball.close()
        print("Done!")

if __name__ == "__main__":
    asyncio.run(main()) 