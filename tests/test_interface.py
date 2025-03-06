"""
Tests for the Fireball interface functionality.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fireball.interfaces.interface import Fireball
from fireball.storage.models import Job, ApplyType, JobSearchMetadata

@pytest.fixture
def mock_linkedin():
    """Create a mock LinkedIn job search instance."""
    mock = AsyncMock()
    mock.login = AsyncMock()
    mock.close = AsyncMock()
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
async def test_search_jobs_with_metadata(fireball, mock_linkedin, mock_storage):
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
    mock_linkedin.search_jobs.return_value = [sample_job]
    
    # Perform search
    job_ids = await fireball.search_jobs(
        keywords="python developer",
        location="United States",
        experience_levels=["entry", "associate"],
        store_details=True
    )
    
    # Verify login was called
    mock_linkedin.login.assert_called_once()
    
    # Verify search was called with correct parameters
    mock_linkedin.search_jobs.assert_called_once_with(
        keywords=["python developer"],
        location="United States",
        experience_levels=["entry", "associate"]
    )
    
    # Verify job was stored
    mock_storage.add_job.assert_called_once_with(sample_job)
    
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
async def test_search_jobs_simple_demo(fireball, mock_linkedin, mock_storage):
    """Test the simple demo search function."""
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
    mock_linkedin.search_jobs.return_value = [sample_job]
    
    # Perform search
    jobs = await fireball.search_jobs_simple_demo(
        keywords="python developer",
        location="United States",
        experience_levels=["entry", "associate"]
    )
    
    # Verify login was called
    mock_linkedin.login.assert_called_once()
    
    # Verify search was called with correct parameters
    mock_linkedin.search_jobs.assert_called_once_with(
        keywords=["python developer"],
        location="United States",
        experience_levels=["entry", "associate"]
    )
    
    # Verify job was stored
    mock_storage.add_job.assert_called_once_with(sample_job)
    
    # Verify job IDs were stored with metadata
    mock_storage.add_job_ids.assert_called_once()
    args, kwargs = mock_storage.add_job_ids.call_args
    assert args[0] == ["test_job_1"]  # job_ids
    assert isinstance(kwargs['search_metadata'], JobSearchMetadata)
    assert kwargs['search_metadata'].keywords == ["python developer"]
    assert kwargs['search_metadata'].location == "United States"
    assert kwargs['search_metadata'].experience_levels == ["entry", "associate"]
    
    # Verify return value
    assert len(jobs) == 1
    assert jobs[0]["job_id"] == "test_job_1"
    assert jobs[0]["job_title"] == "Test Engineer"

@pytest.mark.asyncio
async def test_search_jobs_no_login_needed(fireball, mock_linkedin, mock_storage):
    """Test that login is not called when not needed."""
    # Set need_login to False
    fireball.need_login = False
    
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
    mock_linkedin.search_jobs.return_value = [sample_job]
    
    # Perform search
    await fireball.search_jobs(
        keywords="python developer",
        location="United States",
        experience_levels=["entry", "associate"]
    )
    
    # Verify login was not called
    mock_linkedin.login.assert_not_called() 