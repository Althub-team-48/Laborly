"""
worker/schemas.py

Defines Pydantic schemas for worker profile operations:
- Creation and updates
- Reading merged user and profile data
"""

from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
from datetime import datetime

from app.database.enums import KYCStatus


# -------------------------------------
# Base Schema for Worker Profile Fields
# -------------------------------------
class WorkerProfileBase(BaseModel):
    bio: str | None = Field(default=None, description="Short biography of the worker")
    years_experience: int | None = Field(default=None, description="Number of years of experience")
    availability_note: str | None = Field(
        default=None, description="Custom note about availability"
    )


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

    is_available: bool | None = Field(
        default=None, description="Availability status for job assignments"
    )

    professional_skills: str | None = Field(
        default=None, description="Comma-separated list of skills"
    )

    work_experience: str | None = Field(default=None, description="Summary of work experience")

    first_name: str | None = Field(default=None, description="First name of the worker")

    last_name: str | None = Field(default=None, description="Last name of the worker")

    phone_number: str | None = Field(default=None, description="Worker's phone number")

    location: str | None = Field(default=None, description="Worker's location")


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
    is_kyc_verified: bool = Field(..., description="KYC verification status")
    professional_skills: str | None = Field(
        default=None, description="Comma-separated list of skills"
    )
    work_experience: str | None = Field(default=None, description="Summary of work experience")

    # Related user fields
    email: str = Field(..., description="Worker's email address")
    first_name: str = Field(..., description="First name of the worker")
    last_name: str = Field(..., description="Last name of the worker")
    phone_number: str | None = Field(default=None, description="Worker's phone number")
    location: str | None = Field(default=None, description="Worker's location")

    model_config = ConfigDict(from_attributes=True)


class KYCRead(BaseModel):
    id: UUID = Field(..., description="Unique identifier for the KYC record")
    user_id: UUID = Field(..., description="Reference to the associated user")
    document_type: str = Field(..., description="Type of identification document")
    document_path: str = Field(..., description="Path to the uploaded document")
    selfie_path: str = Field(..., description="Path to the uploaded selfie")
    status: KYCStatus = Field(..., description="KYC verification status")
    submitted_at: datetime = Field(..., description="Timestamp when the KYC was submitted")
    reviewed_at: datetime | None = Field(None, description="Timestamp when the KYC was reviewed")
    model_config = ConfigDict(from_attributes=True)


# -----------------------------------------------------
# Generic Message Response Schema
# -----------------------------------------------------
class MessageResponse(BaseModel):
    """
    Generic response schema for simple success or info messages.
    """

    detail: str = Field(..., description="Description of the operation result")
