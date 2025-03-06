"""
Tests for job search functionality.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fireball.interfaces.interface import Fireball
from fireball.storage.models import Job, ApplyType, JobSearchMetadata

class AsyncIteratorMock:
    """Mock class that implements async iterator protocol."""
    def __init__(self, items):
        self.items = items
        self.index = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.index >= len(self.items):
            raise StopAsyncIteration
        item = self.items[self.index]
        self.index += 1
        return item

@pytest.fixture
def mock_linkedin():
    """Create a mock LinkedIn job search instance."""
    mock = AsyncMock()
    mock.login = AsyncMock()
    
    # Make search_jobs return an async iterator directly
    mock.search_jobs = AsyncMock()
    mock.search_jobs.return_value = AsyncIteratorMock([])
    return mock

@pytest.fixture
def mock_storage():
    """Create a mock storage manager instance."""
    mock = MagicMock()
    mock.add_job = MagicMock()
    mock.add_job_ids = MagicMock()
    return mock

@pytest.fixture
def fireball(mock_linkedin, mock_storage):
    """Create a Fireball instance with mocked dependencies."""
    with patch('fireball.interfaces.interface.LinkedInJobSearch', return_value=mock_linkedin), \
         patch('fireball.interfaces.interface.JsonStorageManager', return_value=mock_storage):
        return Fireball(
            linkedin_credentials={"username": "test", "password": "test"},
            storage_path="test_data.json"
        )

@pytest.mark.asyncio
async def test_search_jobs_stores_metadata(fireball, mock_linkedin, mock_storage):
    """Test that job search stores job IDs with search metadata."""
    # Create sample job
    sample_job = Job(
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
    
    # Mock the search results
    mock_linkedin.search_jobs.return_value = AsyncIteratorMock([sample_job])
    
    # Perform search
    job_ids = await fireball.search_jobs(
        keywords="python developer",
        location="United States",
        experience_levels=["entry", "associate"],
        store_details=True
    )
    
    # Verify job IDs were stored with metadata
    mock_storage.add_job_ids.assert_called_once()
    args, kwargs = mock_storage.add_job_ids.call_args
    assert args[0] == ["test_job_1"]  # job_ids
    assert isinstance(kwargs['search_metadata'], JobSearchMetadata)
    assert kwargs['search_metadata'].keywords == ["python developer"]
    assert kwargs['search_metadata'].location == "United States"
    assert kwargs['search_metadata'].experience_levels == ["entry", "associate"]
    
    # Verify return value
    assert job_ids == ["test_job_1"]

@pytest.mark.asyncio
async def test_search_jobs_without_storing_details(fireball, mock_linkedin, mock_storage):
    """Test that job search works without storing job details."""
    # Create sample job
    sample_job = Job(
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
    
    # Mock the search results
    mock_linkedin.search_jobs.return_value = AsyncIteratorMock([sample_job])
    
    # Perform search without storing details
    job_ids = await fireball.search_jobs(
        keywords="python developer",
        location="United States",
        experience_levels=["entry", "associate"],
        store_details=False
    )
    
    # Verify job IDs were stored with metadata
    mock_storage.add_job_ids.assert_called_once()
    args, kwargs = mock_storage.add_job_ids.call_args
    assert args[0] == ["test_job_1"]  # job_ids
    assert isinstance(kwargs['search_metadata'], JobSearchMetadata)
    
    # Verify job details were not stored
    mock_storage.add_job.assert_not_called()
    
    # Verify return value
    assert job_ids == ["test_job_1"]

@pytest.mark.asyncio
async def test_search_jobs_with_multiple_results(fireball, mock_linkedin, mock_storage):
    """Test that job search handles multiple results correctly."""
    # Create sample jobs
    sample_jobs = [
        Job(
            job_id=f"test_job_{i}",
            job_title=f"Test Engineer {i}",
            company_name="Test Corp",
            location="Test City",
            posted_days_ago="2 days ago",
            ppl_applied="100 applicants",
            apply_link=f"https://test.com/apply/{i}",
            apply_type=ApplyType.EASY_APPLY,
            raw_description=f"Test job description {i}"
        )
        for i in range(1, 4)
    ]
    
    # Mock the search results
    mock_linkedin.search_jobs.return_value = AsyncIteratorMock(sample_jobs)
    
    # Perform search
    job_ids = await fireball.search_jobs(
        keywords="python developer",
        location="United States",
        experience_levels=["entry", "associate"],
        store_details=True
    )
    
    # Verify job IDs were stored with metadata
    mock_storage.add_job_ids.assert_called_once()
    args, kwargs = mock_storage.add_job_ids.call_args
    assert len(args[0]) == 3  # job_ids
    assert set(args[0]) == {"test_job_1", "test_job_2", "test_job_3"}
    assert isinstance(kwargs['search_metadata'], JobSearchMetadata)
    
    # Verify all jobs were stored
    assert mock_storage.add_job.call_count == 3
    
    # Verify return value
    assert len(job_ids) == 3
    assert set(job_ids) == {"test_job_1", "test_job_2", "test_job_3"} 