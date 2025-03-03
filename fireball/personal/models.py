"""
Personal data models (placeholder for future implementation).
"""
from datetime import date
from typing import List, Optional
from pydantic import BaseModel

class PersonalProfile(BaseModel):
    """Basic personal profile data."""
    name: str
    email: str
    phone: Optional[str] = None
    location: Optional[str] = None

# Placeholder for future models:
# - Experience
# - Skills
# - Education
# - Projects
# - Achievements 