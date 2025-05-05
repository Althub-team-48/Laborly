"""
backend/app/worker/schemas.py

Worker Schemas
Defines Pydantic models for worker profile creation, updates, public display,
KYC handling, and related job data views.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.database.enums import KYCStatus


# -----------------------------------------------------
# Base Schema for Worker Profile Fields
# -----------------------------------------------------
class WorkerProfileBase(BaseModel):
    """Base fields shared across worker profile schemas."""

    bio: str | None = Field(default=None, description="Short biography of the worker")
    years_experience: int | None = Field(
        default=None, ge=0, description="Number of years of experience"
    )
    availability_note: str | None = Field(
        default=None, description="Custom note about availability"
    )


# -----------------------------------------------------
# Schema for Writing New Profiles
# -----------------------------------------------------
class WorkerProfileWrite(WorkerProfileBase):
    """Schema for creating a new worker profile."""

    pass


# -----------------------------------------------------
# Schema for Updating Existing Profiles
# -----------------------------------------------------
class WorkerProfileUpdate(WorkerProfileBase):
    """Schema for updating a worker profile and associated user fields."""

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


# -----------------------------------------------------
# Schema for Reading Full Profile + User Info (Authenticated)
# -----------------------------------------------------
class WorkerProfileRead(WorkerProfileBase):
    """Schema for retrieving a full worker profile with user information."""

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


# -----------------------------------------------------
# Schema for Public View of Worker Profile
# -----------------------------------------------------
class PublicWorkerRead(BaseModel):
    """Schema for displaying public worker profile information (non-sensitive)."""

    user_id: UUID = Field(..., description="UUID of the user this profile belongs to")
    first_name: str = Field(..., description="First name of the worker")
    last_name: str = Field(..., description="Last name of the worker")
    location: str | None = Field(default=None, description="Worker's location")
    professional_skills: str | None = Field(
        default=None, description="Comma-separated list of skills"
    )
    work_experience: str | None = Field(default=None, description="Summary of work experience")
    years_experience: int | None = Field(
        default=None, ge=0, description="Number of years of experience"
    )
    bio: str | None = Field(default=None, description="Short biography of the worker")
    is_available: bool = Field(..., description="Availability status for job assignments")
    is_kyc_verified: bool = Field(..., description="KYC verification status")
    model_config = ConfigDict(from_attributes=True)


# -----------------------------------------------------
# Schema for Reading KYC Information
# -----------------------------------------------------
class KYCRead(BaseModel):
    """Schema for retrieving KYC submission details."""

    id: UUID = Field(..., description="Unique identifier for the KYC record")
    user_id: UUID = Field(..., description="Reference to the associated user")
    document_type: str = Field(..., description="Type of identification document submitted")
    document_path: str = Field(..., description="Path to the uploaded identification document")
    selfie_path: str = Field(..., description="Path to the uploaded selfie")
    status: KYCStatus = Field(..., description="KYC verification status")
    submitted_at: datetime = Field(..., description="Timestamp when the KYC was submitted")
    reviewed_at: datetime | None = Field(
        None, description="Timestamp when the KYC was reviewed, if applicable"
    )
    model_config = ConfigDict(from_attributes=True)
