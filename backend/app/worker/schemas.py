"""
worker/schemas.py

Defines Pydantic schemas for worker profile operations:
- Creation and updates
- Reading merged user and profile data
"""

from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from uuid import UUID
from datetime import datetime


# -------------------------------------
# Base Schema for Worker Profile Fields
# -------------------------------------
class WorkerProfileBase(BaseModel):
    bio: Optional[str] = Field(default=None, description="Short biography of the worker")
    years_experience: Optional[int] = Field(default=None, description="Number of years of experience")
    availability_note: Optional[str] = Field(default=None, description="Custom note about availability")


# -------------------------------------
# Schema for Writing New Profiles
# -------------------------------------
class WorkerProfileWrite(WorkerProfileBase):
    """
    Schema for creating a new worker profile.
    """
    pass


# -------------------------------------
# Schema for Updating Existing Profiles
# -------------------------------------
class WorkerProfileUpdate(WorkerProfileBase):
    """
    Schema for updating a worker profile and basic user fields.
    """
    is_available: Optional[bool] = Field(default=None, description="Availability status for job assignments")
    first_name: Optional[str] = Field(default=None, description="First name of the worker")
    last_name: Optional[str] = Field(default=None, description="Last name of the worker")
    phone_number: Optional[str] = Field(default=None, description="Worker's phone number")
    location: Optional[str] = Field(default=None, description="Worker's location")
    profile_picture: Optional[str] = Field(default=None, description="URL to profile picture")


# -------------------------------------
# Schema for Reading Merged Profile + User Info
# -------------------------------------
class WorkerProfileRead(WorkerProfileBase):
    """
    Schema returned when reading a full worker profile with user info.
    """
    id: UUID = Field(..., description="Unique identifier for the worker profile")
    user_id: UUID = Field(..., description="UUID of the user this profile belongs to")
    is_available: bool = Field(..., description="Availability status for job assignments")
    created_at: datetime = Field(..., description="Profile creation timestamp")
    updated_at: datetime = Field(..., description="Profile last update timestamp")

    # Related user fields
    email: str = Field(..., description="Worker's email address")
    first_name: str = Field(..., description="First name of the worker")
    last_name: str = Field(..., description="Last name of the worker")
    phone_number: Optional[str] = Field(default=None, description="Worker's phone number")
    location: Optional[str] = Field(default=None, description="Worker's location")
    profile_picture: Optional[str] = Field(default=None, description="URL to profile picture")

    model_config = ConfigDict(from_attributes=True)

