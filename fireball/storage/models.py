"""
Data models for job applications.
"""
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

class ApplicationStatus(str, Enum):
    """Job application status."""
    NEW = "new"
    IN_PROGRESS = "in_progress"
    APPLIED = "applied"
    REJECTED = "rejected"
    INTERVIEW_SCHEDULED = "interview_scheduled"

class ApplyType(str, Enum):
    """Type of job application."""
    EASY_APPLY = "Easy Apply"
    REGULAR = "Apply"
    UNKNOWN = "Unknown"

class Job(BaseModel):
    """Job posting model."""
    job_id: str
    job_title: str
    company_name: str
    location: Optional[str] = None
    posted_days_ago: Optional[str] = None
    ppl_applied: Optional[str] = None
    apply_link: Optional[str] = None
    apply_type: ApplyType = ApplyType.UNKNOWN
    raw_description: Optional[str] = None  # Full raw description/second_head
    discovered_at: datetime = Field(default_factory=datetime.utcnow)

class Resume(BaseModel):
    """Resume model."""
    version: str
    file_path: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class JobApplication(BaseModel):
    """Job application model."""
    job_id: str
    resume_version: str
    status: ApplicationStatus = ApplicationStatus.NEW
    applied_at: Optional[datetime] = None
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    application_data: Optional[Dict] = None  # Store form data, answers, etc. 