"""
service/schemas.py

Defines Pydantic schemas for:
- Creating a service
- Updating a service
- Reading a service (response model)
"""

from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
from datetime import datetime


# -------------------------------
# Base Schema for Service Fields
# -------------------------------
class ServiceBase(BaseModel):
    """
    Base schema containing shared fields for service creation and update.
    """

    title: str = Field(..., description="Title or name of the service")
    description: str | None = Field(default=None, description="Detailed description of the service")
    location: str | None = Field(default=None, description="Location where the service is offered")


# -------------------------------
# Create Service Schema
# -------------------------------
class ServiceCreate(ServiceBase):
    """
    Schema used to create a new service listing.
    """

    pass


# -------------------------------
# Update Service Schema
# -------------------------------
class ServiceUpdate(ServiceBase):
    """
    Schema used to update an existing service listing.
    """

    pass


# -------------------------------
# Read (Response) Schema
# -------------------------------
class ServiceRead(ServiceBase):
    """
    Schema returned when reading a service listing.
    """

    id: UUID = Field(..., description="Unique identifier for the service")
    worker_id: UUID = Field(..., description="UUID of the worker offering the service")
    created_at: datetime = Field(..., description="Timestamp when the service was created")
    updated_at: datetime = Field(..., description="Timestamp when the service was last updated")

    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    """
    Generic message response schema.
    """

    detail: str = Field(..., description="Response message detail")
