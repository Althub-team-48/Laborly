"""
job/schemas.py

Pydantic schemas for job-related operations, including:
- Job acceptance
- Job completion
- Job cancellation
- Reading job details and listings
"""

from uuid import UUID
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.job.models import JobStatus


# --------------------------------------------------
# Base Schema for Shared Fields
# --------------------------------------------------
class JobBase(BaseModel):
    """
    Shared base for job-related schemas.
    """
    service_id: Optional[UUID] = Field(
        default=None,
        description="ID of the service associated with the job"
    )


# --------------------------------------------------
# Accept Job Input Schema
# --------------------------------------------------
class JobAccept(BaseModel):
    """
    Payload for initiating a job based on a conversation thread.
    """
    thread_id: UUID = Field(
        ...,
        description="ID of the thread that triggered this job"
    )


# --------------------------------------------------
# Complete Job Schema (No Payload Required)
# --------------------------------------------------
class JobComplete(BaseModel):
    """
    No input fields required when marking a job as complete.
    """
    pass


# --------------------------------------------------
# Cancel Job Input Schema
# --------------------------------------------------
class CancelJobRequest(BaseModel):
    """
    Payload for cancelling a job with a reason.
    """
    cancel_reason: str = Field(
        ...,
        description="Reason provided by the client for cancelling the job"
    )


# --------------------------------------------------
# Read Job Output Schema
# --------------------------------------------------
class JobRead(BaseModel):
    """
    Full job detail response schema used for listings and detail views.
    """
    id: UUID = Field(..., description="Unique identifier for the job")
    client_id: UUID = Field(..., description="UUID of the client who created the job")
    worker_id: UUID = Field(..., description="UUID of the worker assigned to the job")
    service_id: Optional[UUID] = Field(default=None, description="UUID of the service related to the job")
    status: JobStatus = Field(..., description="Current status of the job")
    cancel_reason: Optional[str] = Field(default=None, description="Cancellation reason, if applicable")
    started_at: Optional[datetime] = Field(default=None, description="Timestamp when the job started")
    completed_at: Optional[datetime] = Field(default=None, description="Timestamp when the job was completed")
    cancelled_at: Optional[datetime] = Field(default=None, description="Timestamp when the job was cancelled")
    created_at: datetime = Field(..., description="Timestamp when the job was created")
    updated_at: datetime = Field(..., description="Timestamp when the job was last updated")

    class Config:
        from_attributes = True
