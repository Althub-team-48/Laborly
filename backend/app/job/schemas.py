"""
backend/app/job/schemas.py

Job Schemas
Pydantic schemas for job-related operations:
- Job creation and acceptance
- Job completion and cancellation
- Reading job details (Authenticated users)
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.job.models import JobStatus


# ---------------------------------------------------
# Shared Fields Schema
# ---------------------------------------------------
class JobBase(BaseModel):
    """Base schema containing shared fields for job-related payloads."""

    service_id: UUID = Field(..., description="UUID of the service associated with the job")
    thread_id: UUID = Field(..., description="UUID of the conversation thread initiating the job")


# ---------------------------------------------------
# Job Creation Schema (Authenticated Client)
# ---------------------------------------------------
class JobCreate(JobBase):
    """Schema used when a client creates a new job."""

    pass


# ---------------------------------------------------
# Accept Job Schema (Authenticated Worker)
# ---------------------------------------------------
class JobAccept(BaseModel):
    """Schema used when a worker accepts an assigned job."""

    job_id: UUID = Field(..., description="UUID of the job to accept")


# ---------------------------------------------------
# Reject Job Schema (Authenticated Worker)
# ---------------------------------------------------
class JobReject(BaseModel):
    """Schema used when a worker rejects an assigned job."""

    reject_reason: str | None = Field(None, description="Reason for rejecting the job")


# ---------------------------------------------------
# Complete Job Schema (Authenticated Worker)
# ---------------------------------------------------
class JobComplete(BaseModel):
    """Schema used when a worker marks a job as completed (no payload needed)."""

    pass


# ---------------------------------------------------
# Cancel Job Schema (Authenticated Client)
# ---------------------------------------------------
class CancelJobRequest(BaseModel):
    """Schema used when a client cancels a job and provides a cancellation reason."""

    cancel_reason: str = Field(
        ..., description="Reason provided by the client for cancelling the job"
    )


# ---------------------------------------------------
# Read Job Schema (Authenticated Output)
# ---------------------------------------------------
class JobRead(BaseModel):
    """Schema returned when reading job details (authenticated users)."""

    id: UUID = Field(..., description="Job unique identifier")
    client_id: UUID = Field(..., description="UUID of the client who created the job")
    worker_id: UUID = Field(..., description="UUID of the worker assigned to the job")
    service_id: UUID | None = Field(
        default=None, description="UUID of the related service (optional)"
    )

    status: JobStatus = Field(..., description="Current status of the job")
    cancel_reason: str | None = Field(default=None, description="Reason for cancellation (if any)")

    started_at: datetime | None = Field(
        default=None, description="Timestamp when the job was started"
    )
    completed_at: datetime | None = Field(
        default=None, description="Timestamp when the job was completed"
    )
    cancelled_at: datetime | None = Field(
        default=None, description="Timestamp when the job was cancelled"
    )
    created_at: datetime = Field(..., description="Timestamp when the job was created")
    updated_at: datetime = Field(..., description="Timestamp when the job was last updated")

    model_config = ConfigDict(from_attributes=True)
