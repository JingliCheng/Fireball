"""
Main interface for Fireball users.
"""
from typing import Dict, List, Optional

class Fireball:
    """Main interface for job application automation."""
    
    def __init__(self, linkedin_credentials: Dict[str, str]):
        """Initialize Fireball with credentials."""
        pass

    def search_jobs(self, keywords: List[str], location: Optional[str] = None):
        """Search for jobs."""
        pass

    def apply_to_job(self, job_id: str, resume_path: str):
        """Apply to a job."""
        pass 