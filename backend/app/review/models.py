"""
backend/app/review/models.py

Review Database Model
Defines the Review model for storing job-related feedback:
- Each review is linked to a specific job (one-to-one) and user pair (client and worker).
- Supports star ratings, optional review text, and admin flagging for moderation.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.schema import CheckConstraint

from app.database.base import Base

if TYPE_CHECKING:
    from app.database.models import User
    from app.job.models import Job


# ---------------------------------------------------
# Review Model
# ---------------------------------------------------


class Review(Base):
    """Review submitted by a client about a worker for a specific job."""

    __tablename__ = "reviews"
    __table_args__ = (CheckConstraint("rating >= 1 AND rating <= 5", name="rating_range"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique identifier for the review",
    )

    # ---------------------------------------------------
    # Review Content Fields
    # ---------------------------------------------------

    review_text: Mapped[str] = mapped_column(
        String,
        nullable=True,
        comment="Optional text content of the review",
    )

    rating: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Star rating from 1 to 5",
    )

    # ---------------------------------------------------
    # Foreign Key Fields
    # ---------------------------------------------------

    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            use_alter=True,
            name="fk_reviews_client_id",
            deferrable=True,
            initially="DEFERRED",
        ),
        nullable=False,
        comment="User ID of the client who submitted the review",
    )

    worker_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            use_alter=True,
            name="fk_reviews_worker_id",
            deferrable=True,
            initially="DEFERRED",
        ),
        nullable=False,
        comment="User ID of the worker being reviewed",
    )

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "jobs.id",
            use_alter=True,
            name="fk_reviews_job_id",
            deferrable=True,
            initially="DEFERRED",
        ),
        nullable=False,
        comment="ID of the related job",
    )

    # ---------------------------------------------------
    # Admin Moderation
    # ---------------------------------------------------

    is_flagged: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Whether the review is flagged for moderation",
    )

    # ---------------------------------------------------
    # Timestamp
    # ---------------------------------------------------

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="Timestamp when the review was created",
    )

    # ---------------------------------------------------
    # Relationships
    # ---------------------------------------------------

    client: Mapped["User"] = relationship(
        "User",
        back_populates="given_reviews",
        foreign_keys=[client_id],
        # Relationship: Many reviews can be submitted by one client
    )

    worker: Mapped["User"] = relationship(
        "User",
        back_populates="received_reviews",
        foreign_keys=[worker_id],
        # Relationship: Many reviews can be received by one worker
    )

    job: Mapped["Job"] = relationship(
        "Job",
        back_populates="review",
        uselist=False,
        # Relationship: One review is linked to one job
    )
