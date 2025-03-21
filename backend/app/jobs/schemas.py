"""
[jobs] schemas.py

Defines Pydantic models and enums for:
- Job creation, update, and response serialization
- Job application creation, update, and output
- Used for request validation and response shaping in the jobs module
"""

from typing import Optional, List
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, field_validator
from users.schemas import UserOut


# --- Enums for status ---

class JobStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class ApplicationStatus(str, Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


# --- Job Models ---

class JobBase(BaseModel):
    title: str
    description: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    @field_validator("start_time", "end_time", mode="before")
    @classmethod
    def ensure_timezone(cls, value: Optional[datetime]) -> Optional[datetime]:
        """
        Ensures that datetime values have timezone information.
        """
        if value is not None and value.tzinfo is None:
            raise ValueError("Datetime values must include timezone information")
        return value


class JobCreate(JobBase):
    """
    Schema for creating a new job.
    Inherits title and description from JobBase.
    """
    pass


class JobUpdate(BaseModel):
    """
    Schema for updating an existing job.
    Allows partial updates of fields.
    """
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[JobStatus] = None
    worker_id: Optional[int] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, value: Optional[str]) -> Optional[JobStatus]:
        """
        Validates and normalizes job status strings to uppercase enum values.
        """
        if value is None:
            return None
        upper_value = value.upper()
        if upper_value not in JobStatus.__members__:
            raise ValueError(f"Invalid status. Must be one of: {', '.join(JobStatus.__members__.keys())}")
        return JobStatus[upper_value]
    
    @field_validator("start_time", "end_time", mode="before")
    @classmethod
    def ensure_timezone(cls, value: Optional[datetime]) -> Optional[datetime]:
        """
        Ensures that datetime values have timezone information.
        """
        if value is not None and value.tzinfo is None:
            raise ValueError("Datetime values must include timezone information")
        return value


class JobOut(BaseModel):
    """
    Serialized output schema for a job, including related client and worker info.
    """
    id: int
    title: str
    description: str
    client: UserOut
    worker: Optional[UserOut]
    status: JobStatus
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # Allows use with ORM models


class JobList(BaseModel):
    """
    List of jobs.
    """
    jobs: List[JobOut]


# --- Job Application Models ---

class JobApplicationCreate(BaseModel):
    job_id: int


class JobApplicationUpdate(BaseModel):
    status: Optional[ApplicationStatus] = None

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, value: Optional[str]) -> Optional[ApplicationStatus]:
        """
        Validates and normalizes application status strings to uppercase enum values.
        """
        if value is None:
            return None
        upper_value = value.upper()
        if upper_value not in ApplicationStatus.__members__:
            raise ValueError(f"Invalid status. Must be one of: {', '.join(ApplicationStatus.__members__.keys())}")
        return ApplicationStatus[upper_value]


class JobApplicationOut(BaseModel):
    """
    Serialized output schema for a job application.
    Includes job and worker details.
    """
    id: int
    job: JobOut
    worker: UserOut
    status: ApplicationStatus
    applied_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class JobApplicationList(BaseModel):
    """
    List of job applications.
    """
    applications: List[JobApplicationOut]
