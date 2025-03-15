"""
Example script demonstrating how to scrape job information from existing job IDs.

This script shows how to:
1. Get the list of jobs that need to be scraped
2. Scrape detailed information for those jobs
3. Display the scraped job information
4. Show changes in storage statistics
"""
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

from fireball.interfaces.interface import Fireball

async def main():
    load_dotenv()
    
    # Initialize Fireball with credentials
    fireball = Fireball(
        linkedin_credentials={
            "username": os.getenv("LINKEDIN_USERNAME"),
            "password": os.getenv("LINKEDIN_PASSWORD")
        },
        chrome_path=os.getenv("CHROME_PATH")  # Optional: use specific Chrome path
    )
    
    # Get storage statistics before scraping
    before_stats = fireball._storage.get_storage_stats()
    print("\nStorage Statistics Before Scraping:")
    print(f"Jobs to scrape: {before_stats['num_to_scrape']}")
    print(f"Jobs scraped: {before_stats['num_scraped']}")
    print(f"Job info entries: {before_stats['num_job_info']}")
    
    if before_stats['num_to_scrape'] == 0:
        print("\nNo jobs to scrape. Please run search_job_ids first to collect some job IDs.")
        return
    
    scraped_jobs = []
    try:
        # Scrape detailed information for up to 5 jobs
        print("\nScraping job information...")
        scraped_jobs = await fireball.scrape_pending_job_info(limit=5)
        
        # Display the scraped job information
        if scraped_jobs:
            print("\nScraped Job Information:")
            print("-" * 50)
            
            for job_info in scraped_jobs:
                print(f"\nTitle: {job_info.job_title}")
                print(f"Company: {job_info.company_name}")
                print(f"Location: {job_info.location}")
                print(f"Apply Type: {job_info.apply_type}")
                print(f"Apply Link: {job_info.apply_link}")
                print(f"Posted: {job_info.posted_days_ago}")
                print(f"People Applied: {job_info.ppl_applied}")
                print("-" * 50)
        else:
            print("\nNo jobs were successfully scraped.")
    
    finally:
        # Always close the browser
        await fireball.close()
        
    # Show changes in storage statistics (outside try-finally)
    changes = fireball._storage.get_scraping_changes(before_stats)
    print("\nStorage Changes After Scraping:")
    print(f"Jobs to scrape: {changes['change_to_scrape']} ({before_stats['num_to_scrape']} → {before_stats['num_to_scrape'] + changes['change_to_scrape']})")
    print(f"Jobs scraped: +{changes['change_scraped']} ({before_stats['num_scraped']} → {before_stats['num_scraped'] + changes['change_scraped']})")
    print(f"Job info entries: +{changes['change_job_info']} ({before_stats['num_job_info']} → {before_stats['num_job_info'] + changes['change_job_info']})")
    
    # Return summary of what was scraped
    print(f"\nSuccessfully scraped {len(scraped_jobs)} jobs")

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main()) 