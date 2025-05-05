# filename: backend/app/service/schemas.py
"""
backend/app/service/schemas.py

Service Schemas
Defines Pydantic schemas for:
- Creating a service
- Updating a service
- Reading a service (response model)
- Generic message responses (imported from core)
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# NOTE: MessageResponse will be imported from app.core.schemas in routes.py

# ---------------------------------------------------
# Base Schema for Service Fields
# ---------------------------------------------------


class ServiceBase(BaseModel):
    """Base schema containing shared fields for service creation and update."""

    title: str = Field(..., max_length=100, description="Title or name of the service")
    description: str | None = Field(default=None, description="Detailed description of the service")
    location: str | None = Field(
        default=None, max_length=100, description="Location where the service is offered"
    )


# ---------------------------------------------------
# Create Service Schema
# ---------------------------------------------------


class ServiceCreate(ServiceBase):
    """Schema used to create a new service listing."""

    pass


# ---------------------------------------------------
# Update Service Schema
# ---------------------------------------------------


class ServiceUpdate(BaseModel):
    """Schema used to update an existing service listing."""

    # Allow fields to be optional during update
    title: str | None = Field(None, max_length=100, description="Title or name of the service")
    description: str | None = Field(default=None, description="Detailed description of the service")
    location: str | None = Field(
        default=None, max_length=100, description="Location where the service is offered"
    )


# ---------------------------------------------------
# Read (Response) Schema
# ---------------------------------------------------


class ServiceRead(ServiceBase):
    """Schema returned when reading a service listing."""

    id: UUID = Field(..., description="Unique identifier for the service")
    worker_id: UUID = Field(..., description="UUID of the worker offering the service")
    # Include worker details for context? Optional, depending on frontend needs.
    # For now, keeping it simple as per original schema.
    created_at: datetime = Field(..., description="Timestamp when the service was created")
    updated_at: datetime = Field(..., description="Timestamp when the service was last updated")

    model_config = ConfigDict(from_attributes=True)


# Removed MessageResponse - will be imported from app.core.schemas
