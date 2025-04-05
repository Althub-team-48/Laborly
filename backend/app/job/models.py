"""
job/models.py

Defines the Job model and status enum used for managing job lifecycle states.
"""

import uuid
import enum
from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, ForeignKey, Text, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class JobStatus(str, enum.Enum):
    """
    Enum representing the various states a job can be in.
    """
    NEGOTIATING = "NEGOTIATING"
    ACCEPTED = "ACCEPTED"
    COMPLETED = "COMPLETED"
    FINALIZED = "FINALIZED"
    CANCELLED = "CANCELLED"


class Job(Base):
    """
    Represents a job posted by a client and assigned to a worker.
    """
    __tablename__ = "jobs"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique identifier for the job"
    )

    client_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        comment="Client who created the job"
    )

    worker_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        comment="Worker assigned to the job"
    )

    service_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("services.id"),
        nullable=True,
        comment="Service related to the job"
    )

    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus),
        default=JobStatus.NEGOTIATING,
        nullable=False,
        comment="Current status of the job"
    )

    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="Timestamp when the job started"
    )

    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="Timestamp when the job was completed"
    )

    cancelled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="Timestamp when the job was cancelled"
    )

    cancel_reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Reason provided for job cancellation"
    )
