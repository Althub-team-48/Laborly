"""
client/schemas.py

Defines Pydantic schemas for:
- Client profile creation, update, and read
- Favorite workers
- Client job history
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime


# ------------------------------------
# Client Profile Schemas
# ------------------------------------
class ClientProfileBase(BaseModel):
    business_name: Optional[str] = Field(default=None, description="Optional business name for the client")


class ClientProfileWrite(ClientProfileBase):
    """Schema used for creating a client profile."""
    pass


class ClientProfileUpdate(ClientProfileBase):
    """Schema used for updating a client profile."""
    pass


class ClientProfileRead(ClientProfileBase):
    """Schema returned when reading a client profile."""
    id: UUID = Field(..., description="Unique identifier for the client profile")
    user_id: UUID = Field(..., description="UUID of the user this profile belongs to")
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
    """Schema returned when reading a client's job record."""
    id: UUID = Field(..., description="Unique identifier of the job")
    service_id: Optional[UUID] = Field(default=None, description="ID of the service related to the job")
    worker_id: UUID = Field(..., description="ID of the worker assigned to the job")
    status: str = Field(..., description="Current status of the job")
    started_at: Optional[datetime] = Field(default=None, description="Timestamp when the job started")
    completed_at: Optional[datetime] = Field(default=None, description="Timestamp when the job was completed")
    cancelled_at: Optional[datetime] = Field(default=None, description="Timestamp when the job was cancelled")
    cancel_reason: Optional[str] = Field(default=None, description="Reason for job cancellation, if any")

    class Config:
        from_attributes = True
