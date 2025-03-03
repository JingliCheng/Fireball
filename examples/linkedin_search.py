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
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from fireball.interfaces.interface import Fireball

async def main():
    # Load environment variables
    load_dotenv()
    
    # Example 1: Using default settings (auto-detect Chrome)
    fireball = Fireball(
        linkedin_credentials={
            "username": os.getenv("LINKEDIN_USERNAME"),
            "password": os.getenv("LINKEDIN_PASSWORD")
        },
        chrome_path=os.getenv("CHROME_PATH")  # Optional: use specific Chrome path
    )
    
    # Example 2: Specifying Chrome path and using Gemini
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if gemini_api_key:
        gemini_llm = ChatGoogleGenerativeAI(model='gemini-pro', api_key=gemini_api_key)
        fireball_gemini = Fireball(
            linkedin_credentials={
                "username": os.getenv("LINKEDIN_USERNAME"),
                "password": os.getenv("LINKEDIN_PASSWORD")
            },
            llm=gemini_llm,
        )
    
    # Use the default instance for this demo
    try:
        # Search for Python developer jobs
        jobs = await fireball.search_jobs(
            keywords="python developer",
            location="United States",
            experience_levels=["ENTRY_LEVEL", "MID_SENIOR"]
        )
        
        # Print results
        for job in jobs:
            print(f"\nFound job: {job['title']}")
            print(f"Company: {job['company_name']}")
            print(f"Location: {job['location']}")
            print(f"Apply type: {job['apply_type']}")
            print(f"Apply link: {job['apply_link']}")
    
    finally:
        # Clean up
        await fireball.close()

if __name__ == "__main__":
    asyncio.run(main()) 