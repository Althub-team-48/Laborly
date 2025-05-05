"""
backend/app/client/schemas.py

Client Schemas
Defines Pydantic models for client profile management, favorite worker handling,
job history records, and generic message responses.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


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
    phone_number: str | None = Field(..., description="Phone number of the client")
    first_name: str = Field(..., description="First name of the client")
    last_name: str = Field(..., description="Last name of the client")
    location: str | None = Field(default=None, description="Location of the client")
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

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------
# Favorite Worker Schemas
# ---------------------------------------------------
class FavoriteBase(BaseModel):
    """Base schema for favorite worker information."""

    worker_id: UUID = Field(..., description="UUID of the worker being favorited")


class FavoriteRead(FavoriteBase):
    """Schema returned when reading a favorite worker record."""

    id: UUID = Field(..., description="Unique identifier for the favorite entry")
    client_id: UUID = Field(..., description="UUID of the client who favorited the worker")
    created_at: datetime = Field(..., description="Timestamp when the favorite was created")

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------
# Client Job History Schemas
# ---------------------------------------------------
class ClientJobRead(BaseModel):
    """Schema returned when reading a job from the client's job history."""

    id: UUID = Field(..., description="Unique identifier of the job")
    service_id: UUID | None = Field(default=None, description="Service related to the job")
    worker_id: UUID | None = Field(None, description="Worker assigned to the job")
    status: str = Field(..., description="Current status of the job")
    started_at: datetime | None = Field(default=None, description="Job start timestamp")
    completed_at: datetime | None = Field(default=None, description="Job completion timestamp")
    cancelled_at: datetime | None = Field(
        default=None, description="Timestamp when the job was cancelled"
    )
    cancel_reason: str | None = Field(default=None, description="Reason for job cancellation")

    model_config = ConfigDict(from_attributes=True)
