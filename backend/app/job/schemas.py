"""
schemas.py

Pydantic schemas for job-related operations:
- Job acceptance
- Job completion and cancellation
- Job retrieval and listing
"""

from uuid import UUID
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from app.job.models import JobStatus


# -------------------------------
# Base Job Schema
# -------------------------------
class JobBase(BaseModel):
    service_id: Optional[UUID] = Field(
        default=None,
        description="ID of the associated service"
    )


# -------------------------------
# Accept Job Schema
# -------------------------------
class JobAccept(BaseModel):
    thread_id: UUID = Field(
        ...,
        description="ID of the thread that triggered this job"
    )


# -------------------------------
# Complete Job Schema
# -------------------------------
class JobComplete(BaseModel):
    """
    No additional fields required to complete a job.
    """
    pass


# -------------------------------
# Cancel Job Schema
# -------------------------------
class CancelJobRequest(BaseModel):
    cancel_reason: str = Field(
        ...,
        description="Reason for cancelling the job"
    )


# -------------------------------
# Read Job Schema
# -------------------------------
class JobRead(BaseModel):
    id: UUID = Field(..., description="Unique identifier for the job")
    client_id: UUID = Field(..., description="ID of the client who created the job")
    worker_id: UUID = Field(..., description="ID of the assigned worker")
    service_id: Optional[UUID] = Field(default=None, description="Service linked to the job")
    status: JobStatus = Field(..., description="Current status of the job")
    cancel_reason: Optional[str] = Field(default=None, description="Reason for cancellation, if cancelled")
    started_at: Optional[datetime] = Field(default=None, description="Timestamp when the job started")
    completed_at: Optional[datetime] = Field(default=None, description="Timestamp when the job was completed")
    cancelled_at: Optional[datetime] = Field(default=None, description="Timestamp when the job was cancelled")
    created_at: datetime = Field(..., description="Timestamp when the job was created")
    updated_at: datetime = Field(..., description="Timestamp when the job was last updated")

    class Config:
        from_attributes = True
