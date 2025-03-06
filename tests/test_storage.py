"""
Tests for storage functionality.
"""
import json
import pytest
from pathlib import Path
from datetime import datetime
from fireball.storage.json_store import JsonStorageManager
from fireball.storage.models import Job, ApplyType, JobSearchMetadata, JobIdEntry, JobIdsState
import time

@pytest.fixture
def temp_storage_dir(tmp_path):
    """Create a temporary storage directory for testing."""
    storage_dir = tmp_path / "test_storage"
    storage_dir.mkdir()
    return storage_dir

@pytest.fixture
def temp_backup_dir(tmp_path):
    """Create a temporary backup directory for testing."""
    backup_dir = tmp_path / "test_backups"
    backup_dir.mkdir()
    return backup_dir

@pytest.fixture
def storage_manager(temp_storage_dir):
    """Create a storage manager instance for testing."""
    return JsonStorageManager(str(temp_storage_dir))

@pytest.fixture
def sample_job():
    """Create a sample job for testing."""
    return Job(
        job_id="test_job_1",
        job_title="Test Engineer",
        company_name="Test Corp",
        location="Test City",
        posted_days_ago="2 days ago",
        ppl_applied="100 applicants",
        apply_link="https://test.com/apply",
        apply_type=ApplyType.EASY_APPLY,
        raw_description="Test job description"
    )

@pytest.fixture
def sample_search_metadata():
    """Create sample search metadata for testing."""
    return JobSearchMetadata(
        keywords=["python", "developer"],
        location="New York",
        experience_levels=["Entry Level", "Mid Level"]
    )

def test_initialization(temp_storage_dir):
    """Test storage manager initialization."""
    manager = JsonStorageManager(str(temp_storage_dir))
    
    # Check if files were created
    assert (temp_storage_dir / "job_ids.json").exists()
    assert (temp_storage_dir / "jobs.jsonl").exists()
    
    # Check initial job_ids.json content
    with open(temp_storage_dir / "job_ids.json", 'r') as f:
        data = json.load(f)
        assert data == {
            "to_scrape": [],
            "scraped": [],
            "last_updated": data["last_updated"]  # Timestamp will be dynamic
        }

def test_add_job_ids(storage_manager, sample_search_metadata):
    """Test adding job IDs to scrape with metadata."""
    job_ids = ["job1", "job2", "job3"]
    storage_manager.add_job_ids(job_ids, sample_search_metadata)
    
    # Check if entries were added to to_scrape
    assert len(storage_manager.job_ids_state.to_scrape) == 3
    assert len(storage_manager.job_ids_state.scraped) == 0
    
    # Verify metadata for each entry
    for entry in storage_manager.job_ids_state.to_scrape:
        assert entry.job_id in job_ids
        assert entry.search_metadata == sample_search_metadata
        assert isinstance(entry.added_at, datetime)
        assert isinstance(entry.last_updated, datetime)
    
    # Check if file was updated
    with open(storage_manager.job_ids_file, 'r') as f:
        data = json.load(f)
        assert len(data["to_scrape"]) == 3
        assert data["scraped"] == []

def test_add_job(storage_manager, sample_job, sample_search_metadata):
    """Test adding a job and moving it to scraped."""
    # First add job ID with metadata
    storage_manager.add_job_ids([sample_job.job_id], sample_search_metadata)
    
    # Add the job
    storage_manager.add_job(sample_job)
    
    # Check if job was moved to scraped
    assert len(storage_manager.job_ids_state.to_scrape) == 0
    assert len(storage_manager.job_ids_state.scraped) == 1
    
    # Verify the entry in scraped
    entry = storage_manager.job_ids_state.scraped[0]
    assert entry.job_id == sample_job.job_id
    assert entry.search_metadata == sample_search_metadata
    assert isinstance(entry.last_updated, datetime)
    
    # Verify job details were saved
    restored_job = storage_manager.get_job(sample_job.job_id)
    assert restored_job is not None
    assert restored_job.job_id == sample_job.job_id
    assert restored_job.job_title == sample_job.job_title

def test_add_job_ids_after_scraping(storage_manager, sample_job, sample_search_metadata):
    """Test adding job IDs that were already scraped."""
    # First add and scrape a job
    storage_manager.add_job_ids([sample_job.job_id], sample_search_metadata)
    storage_manager.add_job(sample_job)
    
    # Try to add the same job ID again
    storage_manager.add_job_ids([sample_job.job_id], sample_search_metadata)
    
    # Check if it wasn't added to to_scrape
    assert len(storage_manager.job_ids_state.to_scrape) == 0
    assert len(storage_manager.job_ids_state.scraped) == 1
    assert storage_manager.job_ids_state.scraped[0].job_id == sample_job.job_id

def test_get_job_search_metadata(storage_manager, sample_job, sample_search_metadata):
    """Test retrieving search metadata for a job."""
    # Add job ID with metadata
    storage_manager.add_job_ids([sample_job.job_id], sample_search_metadata)
    
    # Get metadata before scraping
    metadata = storage_manager.get_job_search_metadata(sample_job.job_id)
    assert metadata == sample_search_metadata
    
    # Add the job
    storage_manager.add_job(sample_job)
    
    # Get metadata after scraping
    metadata = storage_manager.get_job_search_metadata(sample_job.job_id)
    assert metadata == sample_search_metadata
    
    # Try to get metadata for non-existent job
    metadata = storage_manager.get_job_search_metadata("nonexistent")
    assert metadata is None

def test_backup_and_restore(storage_manager, temp_backup_dir, sample_job, sample_search_metadata):
    """Test backup creation and restoration."""
    # Add some test data
    storage_manager.add_job_ids(["job1", "job2"], sample_search_metadata)
    storage_manager.add_job_ids([sample_job.job_id], sample_search_metadata)
    storage_manager.add_job(sample_job)
    
    # Create backup
    backup_dir = storage_manager.backup(str(temp_backup_dir))
    
    # Verify backup files exist
    assert (backup_dir / "job_ids.json").exists()
    assert (backup_dir / "jobs.jsonl").exists()
    assert (backup_dir / "backup_info.json").exists()
    
    # Verify backup info
    with open(backup_dir / "backup_info.json", 'r') as f:
        info = json.load(f)
        assert info["num_jobs_to_scrape"] == 2  # Both job1 and job2 are to scrape
        assert info["num_jobs_scraped"] == 1    # sample_job is scraped
        assert info["total_jobs"] == 3
        assert "random_suffix" in info
        assert len(info["random_suffix"]) == 4
    
    # Clear current storage
    storage_manager.job_ids_state = JobIdsState()
    storage_manager._save_job_ids()
    storage_manager.jobs_file.write_text("")
    
    # Restore from backup
    storage_manager.restore_from_backup(str(backup_dir))
    
    # Verify restoration
    assert len(storage_manager.job_ids_state.to_scrape) == 2
    assert len(storage_manager.job_ids_state.scraped) == 1
    
    # Verify job details and metadata
    restored_job = storage_manager.get_job(sample_job.job_id)
    assert restored_job is not None
    assert restored_job.job_id == sample_job.job_id
    assert restored_job.job_title == sample_job.job_title
    
    metadata = storage_manager.get_job_search_metadata(sample_job.job_id)
    assert metadata == sample_search_metadata

def test_backup_cleanup(storage_manager, temp_backup_dir, sample_search_metadata):
    """Test backup cleanup when exceeding max_backups limit."""
    # Create multiple backups
    for i in range(6):  # Create 6 backups when max is 5
        storage_manager.add_job_ids([f"job{i}"], sample_search_metadata)
        storage_manager.backup(str(temp_backup_dir), max_backups=5)
    
    # Get all backup directories
    backup_dirs = sorted(
        [d for d in temp_backup_dir.iterdir() 
         if d.is_dir() and d.name.startswith("backup_")]
    )
    
    # Verify only 5 backups remain
    assert len(backup_dirs) == 5
    
    # Verify oldest backup was removed
    backup_timestamps = [d.name.split("_")[1] for d in backup_dirs]
    assert len(backup_timestamps) == 5
    assert all(t1 <= t2 for t1, t2 in zip(backup_timestamps, backup_timestamps[1:]))

def test_restore_nonexistent_backup(storage_manager):
    """Test restoring from a non-existent backup."""
    with pytest.raises(ValueError, match="Backup directory not found"):
        storage_manager.restore_from_backup("nonexistent_backup")

def test_job_search_metadata(tmp_path):
    """Test storing job IDs with search metadata."""
    storage = JsonStorageManager(str(tmp_path / "test_data"))
    
    # Create search metadata
    search_metadata = JobSearchMetadata(
        keywords=["python developer"],
        location="United States",
        experience_levels=["entry", "associate"]
    )
    
    # Add some job IDs with metadata
    job_ids = ["job1", "job2", "job3"]
    storage.add_job_ids(job_ids, search_metadata)
    
    # Verify job IDs were added to to_scrape
    assert "job1" in storage.job_ids.to_scrape
    assert "job2" in storage.job_ids.to_scrape
    assert "job3" in storage.job_ids.to_scrape
    
    # Verify metadata was stored correctly
    job1_entry = storage.job_ids.to_scrape["job1"]
    assert job1_entry.search_metadata.keywords == ["python developer"]
    assert job1_entry.search_metadata.location == "United States"
    assert job1_entry.search_metadata.experience_levels == ["entry", "associate"]
    
    # Mark a job as scraped
    storage.mark_job_scraped("job1")
    
    # Verify job moved to scraped with same metadata
    assert "job1" not in storage.job_ids.to_scrape
    assert "job1" in storage.job_ids.scraped
    assert storage.job_ids.scraped["job1"].search_metadata.keywords == ["python developer"]
    
    # Add same job IDs with different metadata
    new_metadata = JobSearchMetadata(
        keywords=["senior developer"],
        location="Remote",
        experience_levels=["senior"]
    )
    storage.add_job_ids(job_ids, new_metadata)
    
    # Verify metadata was updated for unscraped jobs
    assert storage.job_ids.to_scrape["job2"].search_metadata.keywords == ["senior developer"]
    assert storage.job_ids.to_scrape["job2"].search_metadata.location == "Remote"
    
    # Verify scraped job kept old metadata
    assert storage.job_ids.scraped["job1"].search_metadata.keywords == ["python developer"]
    assert storage.job_ids.scraped["job1"].search_metadata.location == "United States" 