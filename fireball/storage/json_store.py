"""
JSON storage implementation.
"""
from datetime import datetime
import json
import shutil
import time
import random
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from .models import JobInfo, Resume, JobApplication, JobIdsState, JobIdEntry, JobSearchMetadata

class JsonStorageManager:
    """Manages job data storage in JSON format."""
    
    def __init__(self, storage_dir: str = "data/active"):
        """Initialize storage manager."""
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # File to store job IDs in different states
        self.job_ids_file = self.storage_dir / "job_ids.json"
        # File to store job info in JSONL format
        self.job_info_file = self.storage_dir / "job_info.jsonl"
        
        # Create empty files if they don't exist
        self.job_ids_file.touch(exist_ok=True)
        self.job_info_file.touch(exist_ok=True)
        
        self._load_or_create_job_ids()

    def _load_or_create_job_ids(self):
        """Load or create the job IDs tracking file."""
        if self.job_ids_file.stat().st_size == 0:
            self.job_ids_state = JobIdsState()
            self._save_job_ids()
        else:
            with open(self.job_ids_file, 'r') as f:
                data = json.load(f)
                self.job_ids_state = JobIdsState(**data)
    
    def _save_job_ids(self):
        """Save job IDs to file."""
        with open(self.job_ids_file, 'w') as f:
            json.dump(self.job_ids_state.model_dump(), f, indent=2, default=str)

    def add_job_ids(self, job_ids: List[str], search_metadata: JobSearchMetadata):
        """Add job IDs to the to_scrape list with search metadata.
        
        Args:
            job_ids: List of job IDs to add
            search_metadata: Metadata about how these jobs were found
        """
        # Only add IDs that aren't already scraped
        existing_scraped_ids = {entry.job_id for entry in self.job_ids_state.scraped}
        new_ids = set(job_ids) - existing_scraped_ids
        
        # Create entries for new IDs
        for job_id in new_ids:
            entry = JobIdEntry(
                job_id=job_id,
                search_metadata=search_metadata
            )
            self.job_ids_state.to_scrape.append(entry)
        
        self._save_job_ids()

    def add_job_info(self, job_info: JobInfo):
        """Add a job info to storage and mark as scraped.
        
        Args:
            job_info: JobInfo object to store
        """
        # Find and move job entry from to_scrape to scraped
        entry = None
        for i, e in enumerate(self.job_ids_state.to_scrape):
            if e.job_id == job_info.job_id:
                entry = self.job_ids_state.to_scrape.pop(i)
                break
        
        if entry:
            entry.last_updated = datetime.utcnow()
            self.job_ids_state.scraped.append(entry)
            self._save_job_ids()
        
        # Append job info to JSONL file
        with open(self.job_info_file, 'a') as f:
            f.write(json.dumps(job_info.model_dump(), default=str) + '\n')

    def get_job_info(self, job_id: str) -> Optional[JobInfo]:
        """Get a job info by ID.
        
        Args:
            job_id: ID of job to retrieve
            
        Returns:
            JobInfo object if found, None otherwise
        """
        if not any(entry.job_id == job_id for entry in self.job_ids_state.scraped):
            return None
            
        with open(self.job_info_file, 'r') as f:
            for line in f:
                job_data = json.loads(line)
                if job_data['job_id'] == job_id:
                    return JobInfo(**job_data)
        return None

    def get_jobs_to_scrape(self) -> List[JobIdEntry]:
        """Get list of job entries that need to be scraped.
        
        Returns:
            List of JobIdEntry objects to scrape
        """
        return self.job_ids_state.to_scrape

    def get_scraped_jobs(self) -> List[JobIdEntry]:
        """Get list of job entries that have been scraped.
        
        Returns:
            List of scraped JobIdEntry objects
        """
        return self.job_ids_state.scraped

    def get_job_search_metadata(self, job_id: str) -> Optional[JobSearchMetadata]:
        """Get search metadata for a job ID.
        
        Args:
            job_id: ID of job to look up
            
        Returns:
            JobSearchMetadata if found, None otherwise
        """
        for entry in self.job_ids_state.to_scrape + self.job_ids_state.scraped:
            if entry.job_id == job_id:
                return entry.search_metadata
        return None

    def backup(self, backup_dir: str = "data/backups", max_backups: int = 5):
        """Create a backup of all data.
        
        Args:
            backup_dir: Directory to store backups
            max_backups: Maximum number of backups to keep
        """
        # Create backup directory if it doesn't exist
        backup_path = Path(backup_dir)
        backup_path.mkdir(parents=True, exist_ok=True)
        
        # Create timestamped backup directory with random suffix
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        random_suffix = ''.join(random.choices('0123456789abcdef', k=4))
        backup_dir = backup_path / f"backup_{timestamp}_{random_suffix}"
        backup_dir.mkdir()
        
        # Copy current files to backup
        shutil.copy2(self.job_ids_file, backup_dir / "job_ids.json")
        shutil.copy2(self.job_info_file, backup_dir / "job_info.jsonl")
        
        # Create backup info file
        backup_info = {
            "timestamp": timestamp,
            "random_suffix": random_suffix,
            "num_jobs_to_scrape": len(self.job_ids_state.to_scrape),
            "num_jobs_scraped": len(self.job_ids_state.scraped),
            "total_jobs": len(self.job_ids_state.to_scrape) + len(self.job_ids_state.scraped)
        }
        with open(backup_dir / "backup_info.json", 'w') as f:
            json.dump(backup_info, f, indent=2)
        
        # Clean up old backups if needed
        self._cleanup_old_backups(backup_path, max_backups)
        
        return backup_dir

    def _cleanup_old_backups(self, backup_dir: Path, max_backups: int):
        """Remove old backups if exceeding max_backups limit.
        
        Args:
            backup_dir: Directory containing backups
            max_backups: Maximum number of backups to keep
        """
        # Get all backup directories
        backup_dirs = sorted(
            [d for d in backup_dir.iterdir() if d.is_dir() and d.name.startswith("backup_")],
            key=lambda x: x.name.split("_")[1]  # Sort by timestamp only
        )
        
        # Remove oldest backups if exceeding limit
        while len(backup_dirs) > max_backups:
            shutil.rmtree(backup_dirs.pop(0))

    def restore_from_backup(self, backup_dir: str):
        """Restore data from a backup.
        
        Args:
            backup_dir: Path to backup directory to restore from
        """
        backup_path = Path(backup_dir)
        if not backup_path.exists():
            raise ValueError(f"Backup directory not found: {backup_dir}")
        
        # Copy backup files to current storage
        shutil.copy2(backup_path / "job_ids.json", self.job_ids_file)
        shutil.copy2(backup_path / "job_info.jsonl", self.job_info_file)
        
        # Reload job IDs
        self._load_or_create_job_ids()

    def add_application(self, application: JobApplication):
        """Add an application to storage."""
        # To be implemented
        pass

    def get_application(self, job_id: str) -> Optional[JobApplication]:
        """Get an application by job ID."""
        # To be implemented
        pass

    def get_storage_stats(self) -> Dict[str, int]:
        """Get current storage statistics.
        
        Returns:
            Dictionary containing:
            - num_to_scrape: Number of jobs waiting to be scraped
            - num_scraped: Number of jobs marked as scraped
            - num_job_info: Number of job info entries in JSONL file
        """
        # Count jobs in JSONL file
        num_job_info = 0
        if self.job_info_file.exists():
            with open(self.job_info_file, 'r') as f:
                for _ in f:
                    num_job_info += 1
        
        return {
            "num_to_scrape": len(self.job_ids_state.to_scrape),
            "num_scraped": len(self.job_ids_state.scraped),
            "num_job_info": num_job_info
        }

    def get_scraping_changes(self, before_stats: Dict[str, int]) -> Dict[str, int]:
        """Calculate changes in storage statistics.
        
        Args:
            before_stats: Statistics from before scraping
            
        Returns:
            Dictionary containing changes:
            - change_to_scrape: Change in number of jobs to scrape
            - change_scraped: Change in number of scraped jobs
            - change_job_info: Change in number of job info entries
        """
        current_stats = self.get_storage_stats()
        
        return {
            "change_to_scrape": current_stats["num_to_scrape"] - before_stats["num_to_scrape"],
            "change_scraped": current_stats["num_scraped"] - before_stats["num_scraped"],
            "change_job_info": current_stats["num_job_info"] - before_stats["num_job_info"]
        } 