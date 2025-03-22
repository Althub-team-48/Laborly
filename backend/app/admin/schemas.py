"""
[admin] schemas.py

Pydantic schemas for admin operations:
- Dispute creation, update, and response serialization
- Admin-focused user and job listings
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, field_validator

from users.schemas import UserOut
from jobs.schemas import JobOut


# --- Dispute Schemas ---

class DisputeBase(BaseModel):
    job_id: int
    reason: str


class DisputeCreate(DisputeBase):
    """Schema for creating a new dispute."""
    pass


class DisputeUpdate(BaseModel):
    """Schema for updating dispute status."""
    status: Optional[str] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: Optional[str]) -> Optional[str]:
        """Validates status if provided."""
        valid_statuses = ["OPEN", "RESOLVED", "ESCALATED"]
        if value and value.upper() not in valid_statuses:
            raise ValueError(f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
        return value.upper() if value else None


class DisputeOut(BaseModel):
    """Serialized response for a dispute."""
    id: int
    job: JobOut
    raised_by: UserOut
    reason: str
    status: str
    created_at: datetime
    resolved_at: Optional[datetime]

    class Config:
        from_attributes = True


class DisputeList(BaseModel):
    """Wrapper schema for a list of disputes."""
    disputes: List[DisputeOut]


# --- Listing Schemas ---

class UserList(BaseModel):
    """Wrapper for returning a list of users."""
    users: List[UserOut]


class JobList(BaseModel):
    """Wrapper for returning a list of jobs."""
    jobs: List[JobOut]
