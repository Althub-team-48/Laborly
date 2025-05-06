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

from app.service.schemas import ServiceBase


# ---------------------------------------------------
# Partial Schemas for Embedding
# ---------------------------------------------------
class JobClientInfo(BaseModel):
    """Partial client information for embedding in JobRead."""

    id: UUID = Field(..., description="Client's unique identifier")
    first_name: str = Field(..., description="Client's first name")
    last_name: str = Field(..., description="Client's last name")

    model_config = ConfigDict(from_attributes=True)


class JobWorkerInfo(BaseModel):
    """Partial worker information for embedding in JobRead."""

    id: UUID = Field(..., description="Worker's unique identifier")
    first_name: str = Field(..., description="Worker's first name")
    last_name: str = Field(..., description="Worker's last name")

    model_config = ConfigDict(from_attributes=True)


class JobServiceInfo(ServiceBase):
    """Partial service information for embedding in JobRead."""

    id: UUID = Field(..., description="Service's unique identifier")

    model_config = ConfigDict(from_attributes=True)


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

    client: JobClientInfo = Field(..., description="Details of the client who created the job")
    worker: JobWorkerInfo | None = Field(
        None, description="Details of the worker assigned to the job"
    )
    service: JobServiceInfo | None = Field(None, description="Details of the related service")

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
