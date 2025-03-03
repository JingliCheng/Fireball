"""
Main interface for Fireball users.
"""
from typing import Dict, List, Optional
from langchain.chat_models.base import BaseChatModel
from ..job_search.linkedin import LinkedInJobSearch
from ..storage.json_store import JsonStorageManager

class Fireball:
    """Main interface for job application automation."""
    
    def __init__(
        self, 
        linkedin_credentials: Dict[str, str],
        storage_path: str = "job_data.json",
        llm: Optional[BaseChatModel] = None,
        model_name: str = "gpt-4-mini",
        chrome_path: Optional[str] = None
    ):
        """Initialize Fireball with credentials and optional configurations.
        
        Args:
            linkedin_credentials: Dict with LinkedIn username and password
            storage_path: Path to store job data (default: job_data.json)
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
        self._storage = JsonStorageManager(storage_path)
        self.need_login = True if chrome_path is None else False

    async def search_jobs(
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
                            (e.g. ["ENTRY_LEVEL", "MID_SENIOR"])
        
        Returns:
            List of job dictionaries with details
        """
        # Login if needed
        if self.need_login:
            await self._linkedin.login()
        
        # Search and store jobs
        jobs = []
        async for job in self._linkedin.search_jobs(
            keywords=[keywords],  # Convert to list for compatibility
            location=location,
            experience_levels=experience_levels
        ):
            # Store job
            self._storage.add_job(job)
            # Convert to dict for API response
            jobs.append(job.dict())
        
        return jobs

    async def apply_to_job(self, job_id: str, resume_path: str):
        """Apply to a job.
        
        Args:
            job_id: ID of the job to apply to
            resume_path: Path to resume file
        """
        # To be implemented
        pass

    async def close(self):
        """Clean up resources."""
        await self._linkedin.close()