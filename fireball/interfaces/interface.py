"""
Main interface for Fireball users.
"""
from typing import Dict, List, Optional, Set
from pathlib import Path
from langchain.chat_models.base import BaseChatModel
from ..job_search.linkedin import LinkedInJobSearch
from ..storage.json_store import JsonStorageManager
from ..storage.models import JobSearchMetadata, JobInfo
import asyncio
import random

class Fireball:
    """Main interface for job application automation."""
    
    def __init__(
        self, 
        linkedin_credentials: Dict[str, str],
        storage_path: Optional[str] = None,
        llm: Optional[BaseChatModel] = None,
        model_name: str = "gpt-4-mini",
        chrome_path: Optional[str] = None
    ):
        """Initialize Fireball with credentials and optional configurations.
        
        Args:
            linkedin_credentials: Dict with LinkedIn username and password
            storage_path: Optional path to store job data. If None, uses package's data/active directory
            llm: Optional pre-configured LLM instance
            model_name: Model name to use if llm not provided (default: gpt-4-mini)
            chrome_path: Optional path to Chrome executable. If None, will try to find automatically
        """
        # Initialize components with configurations
        self._linkedin = LinkedInJobSearch(
            credentials=linkedin_credentials,
            llm=llm,
            model_name=model_name,
            chrome_path=chrome_path
        )
        
        # Use package's data directory by default
        if storage_path is None:
            storage_path = str(Path(__file__).parent.parent.parent / "data" / "active")
        
        self._storage = JsonStorageManager(storage_path)
        self.need_login = True if chrome_path is None else False

    async def search_job_ids(
        self, 
        keywords: str,
        location: Optional[str] = None,
        experience_levels: Optional[List[str]] = None,
        num_scrolls: int = 6
    ) -> List[str]:
        """Search for jobs and return only job IDs without collecting full details.
        
        This function is faster than search_jobs() as it only collects job IDs
        without visiting each job's details page.
        
        Args:
            keywords: Search keywords (e.g. "python developer")
            location: Optional location filter (e.g. "United States")
            experience_levels: Optional list of experience levels
                            (i.e. ["internship", "entry", 
                              "associate", "mid-senior", 
                              "director", "executive"])
            num_scrolls: Number of times to scroll down to collect more jobs
        
        Returns:
            List of job IDs found in the search
        """
        # Login if needed
        if self.need_login:
            await self._linkedin.login()
        
        # Create search metadata
        search_metadata = JobSearchMetadata(
            keywords=[keywords],  # Convert to list for compatibility
            location=location,
            experience_levels=experience_levels
        )
        
        # Get job IDs from LinkedIn
        job_ids = await self._linkedin.collect_job_ids(
            keywords=[keywords],  # Convert to list for compatibility
            location=location,
            experience_levels=experience_levels,
            num_scrolls=num_scrolls
        )
        
        # Store job IDs with search metadata
        self._storage.add_job_ids(list(job_ids), search_metadata)
        
        print(f"\nFound {len(job_ids)} job ids.")
        return list(job_ids)  # Convert set to list before returning

    async def search_jobs(
        self, 
        keywords: str,
        location: Optional[str] = None,
        experience_levels: Optional[List[str]] = None,
        store_details: bool = True
    ) -> List[str]:
        """Search for jobs and return job IDs.
        
        This function searches for jobs on LinkedIn and returns their IDs.
        Optionally stores the full job details in the storage.
        
        Args:
            keywords: Search keywords (e.g. "python developer")
            location: Optional location filter (e.g. "United States")
            experience_levels: Optional list of experience levels
                            (i.e. ["internship", "entry", 
                              "associate", "mid-senior", 
                              "director", "executive"])
            store_details: Whether to store full job details (default: True)
        
        Returns:
            List of job IDs found in the search
        """
        # Login if needed
        if self.need_login:
            await self._linkedin.login()
        
        # Create search metadata
        search_metadata = JobSearchMetadata(
            keywords=[keywords],  # Convert to list for compatibility
            location=location,
            experience_levels=experience_levels
        )
        
        # Search and store jobs
        job_ids = set()
        async for job in self._linkedin.search_jobs(
            keywords=[keywords],  # Convert to list for compatibility
            location=location,
            experience_levels=experience_levels
        ):
            job_ids.add(job.job_id)
            if store_details:
                # Store job details
                self._storage.add_job(job)
        
        # Store all found job IDs with search metadata
        self._storage.add_job_ids(list(job_ids), search_metadata)
        
        print(f"\nFound {len(job_ids)} job ids.")
        return list(job_ids)  # Convert set to list before returning

    async def search_jobs_simple_demo(
        self, 
        keywords: str,
        location: Optional[str] = None,
        experience_levels: Optional[List[str]] = None
    ) -> List[Dict]:
        """Search for jobs.
        
        Args:
            keywords: Search keywords (e.g. "python developer")
            location: Optional location filter (e.g. "United States")
            experience_levels: Optional list of experience levels
                            (i.e. ["internship", "entry", 
                              "associate", "mid-senior", 
                              "director", "executive"])
        
        Returns:
            List of job dictionaries with details
        """
        # Login if needed
        if self.need_login:
            await self._linkedin.login()
        
        # Create search metadata
        search_metadata = JobSearchMetadata(
            keywords=[keywords],  # Convert to list for compatibility
            location=location,
            experience_levels=experience_levels
        )
        
        # Search and store jobs
        jobs = []
        job_ids = set()
        async for job_info in self._linkedin.search_jobs(
            keywords=[keywords],  # Convert to list for compatibility
            location=location,
            experience_levels=experience_levels
        ):
            job_ids.add(job_info.job_id)
            # Store job info
            self._storage.add_job_info(job_info)
            # Convert to dict for API response
            jobs.append(job_info.dict())
        
        # Store all found job IDs with search metadata
        self._storage.add_job_ids(list(job_ids), search_metadata)
        
        return jobs

    async def apply_to_job(self, job_id: str, resume_path: str):
        """Apply to a job.
        
        Args:
            job_id: ID of the job to apply to
            resume_path: Path to resume file
        """
        # To be implemented
        pass

    async def scrape_pending_job_info(self, limit: Optional[int] = None) -> List[JobInfo]:
        """Scrape information for jobs that haven't been processed yet.
        
        Args:
            limit: Optional maximum number of jobs to process
            
        Returns:
            List of successfully scraped JobInfo objects
        """
        # Get list of jobs to scrape
        to_scrape = self._storage.get_jobs_to_scrape()
        if limit:
            to_scrape = to_scrape[:limit]
            
        if not to_scrape:
            print("No jobs to scrape.")
            return []
            
        print(f"\nScraping information for {len(to_scrape)} jobs...")
        processed_jobs = []
        
        # Process each job
        for job_entry in to_scrape:
            try:
                # Scrape job info
                job_info = await self._linkedin.scrape_job_info(job_entry.job_id)
                if job_info:
                    # Save job info
                    self._storage.add_job_info(job_info)
                    processed_jobs.append(job_info)
                    print(f"Processed job {len(processed_jobs)}/{len(to_scrape)}: {job_info.job_title}")
                else:
                    print(f"Failed to scrape job {job_entry.job_id}")
                
                # Add delay between requests
                await asyncio.sleep(random.uniform(2.0, 4.0))
                
            except Exception as e:
                print(f"Error processing job {job_entry.job_id}: {str(e)}")
                continue
                
        print(f"\nSuccessfully processed {len(processed_jobs)} out of {len(to_scrape)} jobs.")
        return processed_jobs

    async def close(self):
        """Clean up resources."""
        await self._linkedin.close()