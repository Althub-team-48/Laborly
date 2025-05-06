"""
backend/app/client/schemas.py

Client Schemas
Defines Pydantic models for client profile management, favorite worker handling,
job history records, and generic message responses.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.service.schemas import ServiceBase
from app.job.models import JobStatus


# ---------------------------------------------------
# Partial Schemas for Embedding
# ---------------------------------------------------
class FavoriteWorkerInfo(BaseModel):
    """Partial worker information for embedding in FavoriteRead."""

    id: UUID = Field(..., description="Worker's unique identifier")
    first_name: str = Field(..., description="Worker's first name")
    last_name: str = Field(..., description="Worker's last name")
    professional_skills: str | None = Field(None, description="Worker's professional skills")
    location: str | None = Field(None, description="Worker's location")
    is_available: bool = Field(False, description="Worker's current availability status")

    model_config = ConfigDict(from_attributes=True)


class ClientJobWorkerInfo(BaseModel):
    """Partial worker information for embedding in ClientJobRead."""

    id: UUID = Field(..., description="Worker's unique identifier")
    first_name: str = Field(..., description="Worker's first name")
    last_name: str = Field(..., description="Worker's last name")

    model_config = ConfigDict(from_attributes=True)


class ClientJobServiceInfo(ServiceBase):
    """Partial service information for embedding in ClientJobRead."""

    id: UUID = Field(..., description="Service's unique identifier")

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------
# Client Profile Schemas
# ---------------------------------------------------
class ClientProfileBase(BaseModel):
    """Base schema for client profile information."""

    profile_description: str | None = Field(
        default=None, description="Optional profile description or note"
    )
    address: str | None = Field(default=None, description="Optional client address")


class ClientProfileWrite(ClientProfileBase):
    """Schema used when creating a new client profile."""

    pass


class ClientProfileUpdate(ClientProfileBase):
    """Schema used when updating an existing client profile."""

    phone_number: str | None = Field(default=None, description="Client's phone number")
    first_name: str | None = Field(default=None, description="Client's first name")
    last_name: str | None = Field(default=None, description="Client's last name")
    location: str | None = Field(default=None, description="Client's general location")


class ClientProfileRead(ClientProfileBase):
    """Schema returned when reading a client profile for the authenticated user."""

    id: UUID = Field(..., description="Unique identifier for the client profile")
    user_id: UUID = Field(..., description="UUID of the user this profile belongs to")
    email: str = Field(..., description="Email address of the client")
    phone_number: str | None = Field(None, description="Phone number of the client")
    first_name: str = Field(..., description="First name of the client")
    last_name: str = Field(..., description="Last name of the client")
    location: str | None = Field(default=None, description="Location of the client")
    profile_picture: HttpUrl | None = Field(None, description="URL to the client's profile picture")
    created_at: datetime = Field(..., description="Profile creation timestamp")
    updated_at: datetime = Field(..., description="Profile last update timestamp")

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------
# Public Client Profile Schema
# ---------------------------------------------------
class PublicClientRead(BaseModel):
    """Schema for a public view of a client profile (excluding sensitive information)."""

    user_id: UUID = Field(..., description="UUID of the user this profile belongs to")
    first_name: str = Field(..., description="First name of the client")
    last_name: str = Field(..., description="Last name of the client")
    location: str | None = Field(default=None, description="Location of the client")
    profile_picture: HttpUrl | None = Field(None, description="URL to the client's profile picture")

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------
# Favorite Worker Schemas
# ---------------------------------------------------
class FavoriteBase(BaseModel):
    """Base schema for favorite worker information."""

    pass


class FavoriteRead(FavoriteBase):
    """Schema returned when reading a favorite worker record."""

    id: UUID = Field(..., description="Unique identifier for the favorite entry")
    client_id: UUID = Field(..., description="UUID of the client who favorited the worker")
    worker: FavoriteWorkerInfo = Field(..., description="Details of the favorited worker")
    created_at: datetime = Field(..., description="Timestamp when the favorite was created")

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------
# Client Job History Schemas
# ---------------------------------------------------
class ClientJobRead(BaseModel):
    """Schema returned when reading a job from the client's job history."""

    id: UUID = Field(..., description="Unique identifier of the job")
    service: ClientJobServiceInfo | None = Field(
        None, description="Partial details of the service related to the job"
    )
    worker: ClientJobWorkerInfo | None = Field(
        None, description="Partial details of the worker assigned to the job"
    )

    status: JobStatus = Field(..., description="Current status of the job")
    started_at: datetime | None = Field(default=None, description="Job start timestamp")
    completed_at: datetime | None = Field(default=None, description="Job completion timestamp")
    cancelled_at: datetime | None = Field(
        default=None, description="Timestamp when the job was cancelled"
    )
    cancel_reason: str | None = Field(default=None, description="Reason for job cancellation")
    created_at: datetime = Field(..., description="Timestamp when the job was created")
    updated_at: datetime = Field(..., description="Timestamp when the job was last updated")

    model_config = ConfigDict(from_attributes=True)
