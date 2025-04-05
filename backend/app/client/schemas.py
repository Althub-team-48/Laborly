"""
client/schemas.py

Defines Pydantic schemas for the Client module:
- Client profile (create, update, read)
- Favorite workers
- Job history views
"""

from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime

# ------------------------------------
# Client Profile Schemas
# ------------------------------------
class ClientProfileBase(BaseModel):
    business_name: Optional[str] = Field(
        default=None,
        description="Optional business name for the client"
    )


class ClientProfileWrite(ClientProfileBase):
    """Schema used for creating a client profile."""
    pass


class ClientProfileUpdate(ClientProfileBase):
    """Schema used for updating a client profile."""
    email: Optional[str] = Field(default=None, description="Client's email address")
    phone_number: Optional[str] = Field(default=None, description="Client's phone number")
    first_name: Optional[str] = Field(default=None, description="Client's first name")
    last_name: Optional[str] = Field(default=None, description="Client's last name")
    location: Optional[str] = Field(default=None, description="Client's general location")
    profile_picture: Optional[str] = Field(default=None, description="URL to client's profile picture")


class ClientProfileRead(ClientProfileBase):
    """Schema returned when reading a client profile."""
    id: UUID = Field(..., description="Unique identifier for the client profile")
    user_id: UUID = Field(..., description="UUID of the user this profile belongs to")
    email: str = Field(..., description="Email address of the client")
    phone_number: str = Field(..., description="Phone number of the client")
    first_name: str = Field(..., description="First name of the client")
    last_name: str = Field(..., description="Last name of the client")
    location: Optional[str] = Field(default=None, description="Location of the client")
    profile_picture: Optional[str] = Field(default=None, description="URL to client's profile picture")
    created_at: datetime = Field(..., description="Profile creation timestamp")
    updated_at: datetime = Field(..., description="Profile last update timestamp")

    class Config:
        from_attributes = True

# ------------------------------------
# Favorite Worker Schemas
# ------------------------------------
class FavoriteBase(BaseModel):
    worker_id: UUID = Field(..., description="UUID of the worker being favorited")


class FavoriteRead(FavoriteBase):
    """Schema returned when reading a favorite entry."""
    id: UUID = Field(..., description="Unique identifier for the favorite entry")
    client_id: UUID = Field(..., description="UUID of the client who favorited the worker")
    created_at: datetime = Field(..., description="Timestamp when the favorite was created")

    class Config:
        from_attributes = True

# ------------------------------------
# Client Job History Schemas
# ------------------------------------
class ClientJobRead(BaseModel):
    """Schema returned when reading a client's job history."""
    id: UUID = Field(..., description="Unique identifier of the job")
    service_id: Optional[UUID] = Field(default=None, description="Service related to the job")
    worker_id: UUID = Field(..., description="Worker assigned to the job")
    status: str = Field(..., description="Current status of the job")
    started_at: Optional[datetime] = Field(default=None, description="Job start timestamp")
    completed_at: Optional[datetime] = Field(default=None, description="Job completion timestamp")
    cancelled_at: Optional[datetime] = Field(default=None, description="Timestamp when the job was cancelled")
    cancel_reason: Optional[str] = Field(default=None, description="Reason for job cancellation")

    class Config:
        from_attributes = True
