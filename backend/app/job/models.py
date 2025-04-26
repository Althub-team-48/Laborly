"""
job/models.py

Defines the Job model and associated JobStatus enum.
- Represents tasks created by clients and handled by workers
- Tracks status transitions, assignment, and lifecycle timestamps
"""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

# TYPE CHECKING IMPORTS
if TYPE_CHECKING:
    from app.database.models import User
    from app.messaging.models import MessageThread
    from app.service.models import Service
    from app.review.models import Review


# ENUM: Job Status
class JobStatus(str, enum.Enum):
    NEGOTIATING = "NEGOTIATING"
    ACCEPTED = "ACCEPTED"
    COMPLETED = "COMPLETED"
    FINALIZED = "FINALIZED"
    CANCELLED = "CANCELLED"


# MODEL: Job
class Job(Base):
    __tablename__ = "jobs"

    # Basic Identifiers & Foreign Keys
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique identifier for the job",
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            use_alter=True,
            name="fk_jobs_client_id",
            deferrable=True,
            initially="DEFERRED",
        ),
        nullable=False,
        comment="Client who created the job",
    )
    worker_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            use_alter=True,
            name="fk_jobs_worker_id",
            deferrable=True,
            initially="DEFERRED",
        ),
        nullable=True,
        comment="Worker assigned to the job",
    )
    service_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "services.id",
            use_alter=True,
            name="fk_jobs_service_id",
            deferrable=True,
            initially="DEFERRED",
        ),
        nullable=True,
        comment="Optional service associated with the job",
    )

    # Job Status & Lifecycle Timestamps
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus),
        default=JobStatus.NEGOTIATING,
        nullable=False,
        comment="Current status of the job",
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Timestamp when the job started"
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Timestamp when the job was completed"
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Timestamp when the job was cancelled"
    )
    cancel_reason: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Reason provided for job cancellation"
    )

    # Audit Fields
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Timestamp when the job was created",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Timestamp when the job was last updated",
    )

    # Relationships
    client: Mapped["User"] = relationship(
        "User", back_populates="created_jobs", foreign_keys=[client_id]
    )
    worker: Mapped[Optional["User"]] = relationship(
        "User", back_populates="assigned_jobs", foreign_keys=[worker_id]
    )
    service: Mapped[Optional["Service"]] = relationship("Service", back_populates="jobs")

    # One-to-One Relationship (Job -> MessageThread)
    # This relationship now relies on the FK being on the MessageThread side
    thread: Mapped[Optional["MessageThread"]] = relationship(
        "MessageThread",
        back_populates="job",
        uselist=False,  # Indicate one-to-one nature from Job's perspective
        cascade="all, delete-orphan",  # If job deleted, delete associated thread
    )

    review: Mapped[Optional["Review"]] = relationship(
        "Review", back_populates="job", uselist=False, cascade="all, delete-orphan"
    )
