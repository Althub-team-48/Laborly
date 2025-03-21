"""
[worker] schemas.py

Defines Pydantic schemas for Worker Availability:
- Create, update, output representations
- Enforces timezone-aware datetime fields
"""

from typing import Optional, List
from datetime import datetime, timezone
from pydantic import BaseModel, field_validator

from users.schemas import UserOut


class WorkerAvailabilityBase(BaseModel):
    """
    Shared base schema containing start and end times.
    """
    start_time: datetime
    end_time: datetime

    @field_validator("start_time", "end_time", mode="before")
    @classmethod
    def ensure_timezone(cls, value: datetime) -> datetime:
        """
        Ensures datetime fields include timezone info.
        Raises a ValueError if naive datetime is detected.
        """
        if value and value.tzinfo is None:
            raise ValueError("Datetime must include timezone information")
        return value

    @field_validator("end_time")
    @classmethod
    def validate_time_order(cls, end: datetime, values: dict) -> datetime:
        """
        Ensures start_time is before end_time.
        """
        start = values.get("start_time")
        if start and end <= start:
            raise ValueError("End time must be after start time")
        return end

    @field_validator("start_time")
    @classmethod
    def validate_future_start(cls, start: datetime) -> datetime:
        """
        Ensures start_time is in the future.
        """
        if start <= datetime.now(timezone.utc):
            raise ValueError("Start time must be in the future")
        return start


class WorkerAvailabilityCreate(WorkerAvailabilityBase):
    """
    Schema for creating a new availability slot.
    Inherits start_time and end_time from base.
    """
    pass


class WorkerAvailabilityUpdate(BaseModel):
    """
    Schema for updating an availability slot.
    Allows optional fields for partial updates.
    """
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    @field_validator("start_time", "end_time", mode="before")
    @classmethod
    def ensure_timezone(cls, value: Optional[datetime]) -> Optional[datetime]:
        """
        Ensures datetime fields include timezone info.
        Raises a ValueError if naive datetime is detected.
        """
        if value and value.tzinfo is None:
            raise ValueError("Datetime must include timezone information")
        return value

    @field_validator("end_time")
    @classmethod
    def validate_time_order(cls, end: Optional[datetime], values: dict) -> Optional[datetime]:
        """
        If both start and end are present, ensure end > start.
        """
        start = values.get("start_time")
        if start and end and end <= start:
            raise ValueError("End time must be after start time")
        return end

    @field_validator("start_time")
    @classmethod
    def validate_future_start(cls, start: Optional[datetime]) -> Optional[datetime]:
        """
        Ensures optional start_time is in the future.
        """
        if start and start <= datetime.now(timezone.utc):
            raise ValueError("Start time must be in the future")
        return start


class WorkerAvailabilityOut(WorkerAvailabilityBase):
    """
    Output schema for returning availability slots with related worker info.
    """
    id: int
    worker: UserOut
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # Required for ORM compatibility


class WorkerAvailabilityList(BaseModel):
    """
    Wrapper for returning a list of worker availabilities.
    """
    availabilities: List[WorkerAvailabilityOut]
