"""
service/schemas.py

Defines Pydantic schemas for:
- Creating a service
- Updating a service
- Reading a service (response model)
"""

from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime


# --------------------------------
# Base Schema for Service
# --------------------------------
class ServiceBase(BaseModel):
    title: str = Field(..., description="Title or name of the service")
    description: Optional[str] = Field(default=None, description="Detailed description of the service")
    location: Optional[str] = Field(default=None, description="Location where the service is offered")


# --------------------------------
# Service Creation Schema
# --------------------------------
class ServiceCreate(ServiceBase):
    """Schema used to create a new service listing."""
    pass


# --------------------------------
# Service Update Schema
# --------------------------------
class ServiceUpdate(ServiceBase):
    """Schema used to update an existing service listing."""
    pass


# --------------------------------
# Service Read/Response Schema
# --------------------------------
class ServiceRead(ServiceBase):
    """Schema returned when reading a service listing."""
    id: UUID = Field(..., description="Unique identifier for the service")
    worker_id: UUID = Field(..., description="UUID of the worker offering the service")
    created_at: datetime = Field(..., description="Timestamp when the service was created")
    updated_at: datetime = Field(..., description="Timestamp when the service was last updated")

    class Config:
        from_attributes = True
