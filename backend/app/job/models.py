"""
job/models.py

Defines the Job model and associated JobStatus enum.
- Represents tasks created by clients and handled by workers
- Tracks status transitions, assignment, and lifecycle timestamps
"""

import uuid
import enum
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    String, Text, DateTime, Enum, ForeignKey, func
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.database.models import User
    from app.messaging.models import MessageThread
    from app.service.models import Service
    from app.review.models import Review


# -----------------------------------------------
# ENUM: Job Status
# -----------------------------------------------
class JobStatus(str, enum.Enum):
    """
    Enum representing lifecycle states for a job.
    """
    NEGOTIATING = "NEGOTIATING"
    ACCEPTED = "ACCEPTED"
    COMPLETED = "COMPLETED"
    FINALIZED = "FINALIZED"
    CANCELLED = "CANCELLED"


# -----------------------------------------------
# MODEL: Job
# -----------------------------------------------
class Job(Base):
    """
    Represents a job posted by a client and assigned to a worker.
    """
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique identifier for the job"
    )

    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        comment="Client who created the job"
    )

    worker_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
        comment="Worker assigned to the job"
    )

    service_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("services.id"),
        nullable=True,
        comment="Optional service associated with the job"
    )

    thread_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("message_threads.id"),
        nullable=True,
        unique=True,
        comment="Thread ID for messaging related to the job"
    )

    review_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reviews.id"),
        nullable=True,
        unique=True,
        comment="Review associated with this job (optional, one-to-one)"
    )

    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus),
        default=JobStatus.NEGOTIATING,
        nullable=False,
        comment="Current status of the job"
    )

    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when the job started"
    )

    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when the job was completed"
    )

    cancelled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when the job was cancelled"
    )

    cancel_reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Reason provided for job cancellation"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Timestamp when the job was created"
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Timestamp when the job was last updated"
    )

    # -------------------------------------
    # Relationships (grouped by type)
    # -------------------------------------
    # One-to-Many Relationships
    client: Mapped["User"] = relationship(
        "User",
        back_populates="created_jobs",
        foreign_keys=[client_id],
        # Relationship: One User (client) can create many Jobs
    )
    worker: Mapped["User"] = relationship(
        "User",
        back_populates="assigned_jobs",
        foreign_keys=[worker_id],
        # Relationship: One User (worker) can be assigned to many Jobs
    )
    service: Mapped["Service"] = relationship(
        "Service",
        back_populates="jobs",
        # Relationship: One Service can be associated with many Jobs
    )

    # One-to-One Relationships
    thread: Mapped["MessageThread"] = relationship(
        "MessageThread",
        back_populates="job",
        uselist=False,
        foreign_keys=[thread_id],
        # Relationship: One Job has one MessageThread (unique constraint on thread_id)
    )
    review: Mapped["Review"] = relationship(
        "Review",
        back_populates="job",
        uselist=False,
        foreign_keys=[review_id],
        # Relationship: One Job has one Review (unique constraint on review_id)
    )