"""
job/schemas.py

Pydantic schemas for job-related operations:
- Job creation and acceptance
- Completion and cancellation
- Reading job details
"""

from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.job.models import JobStatus


# --------------------------------------------------
# Shared Fields Schema
# --------------------------------------------------
class JobBase(BaseModel):
    """
    Shared base schema for job-related payloads.
    """

    service_id: UUID = Field(..., description="UUID of the service associated with the job")
    thread_id: UUID = Field(..., description="UUID of the conversation thread initiating the job")


# --------------------------------------------------
# Job Creation Schema
# --------------------------------------------------
class JobCreate(JobBase):
    """
    Client creates a job by specifying service and thread.
    Worker is inferred from the service.
    """

    pass


# --------------------------------------------------
# Accept Job Schema
# --------------------------------------------------
class JobAccept(BaseModel):
    """
    Worker accepts a job previously created by a client.
    """

    job_id: UUID = Field(..., description="UUID of the job to accept")
    worker_id: UUID | None = Field(None, description="UUID of the worker accepting the job")


# --------------------------------------------------
# Complete Job Schema (Empty Payload)
# --------------------------------------------------
class JobComplete(BaseModel):
    """
    Worker marks job as completed — no payload needed.
    """

    pass


# --------------------------------------------------
# Cancel Job Schema
# --------------------------------------------------
class CancelJobRequest(BaseModel):
    """
    Client cancels a job and provides a cancellation reason.
    """

    cancel_reason: str = Field(
        ..., description="Reason provided by the client for cancelling the job"
    )


# --------------------------------------------------
# Read Job Schema (Output)
# --------------------------------------------------
class JobRead(BaseModel):
    """
    Job detail used for list and detail views.
    """

    id: UUID = Field(..., description="Job unique identifier")
    client_id: UUID = Field(..., description="UUID of the client who created the job")
    worker_id: UUID = Field(..., description="UUID of the worker assigned to the job")
    service_id: UUID | None = Field(default=None, description="Related service UUID (if any)")

    status: JobStatus = Field(..., description="Current status of the job")
    cancel_reason: str | None = Field(default=None, description="Reason for cancellation (if any)")

    started_at: datetime | None = Field(default=None, description="When the job started")
    completed_at: datetime | None = Field(default=None, description="When the job was completed")
    cancelled_at: datetime | None = Field(default=None, description="When the job was cancelled")
    created_at: datetime = Field(..., description="When the job was created")
    updated_at: datetime = Field(..., description="When the job was last updated")

    model_config = ConfigDict(from_attributes=True)
