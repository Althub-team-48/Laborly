"""
review/models.py

Defines the Review model for storing job-related feedback.
- Each review is linked to a specific job and user pair.
- Supports star ratings, optional text, and admin flagging.
"""

from datetime import datetime
from uuid import uuid4, UUID

from sqlalchemy import (
    ForeignKey, Integer, Text, DateTime, Boolean
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
        comment="Unique identifier for the review"
    )

    reviewer_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        comment="User who wrote the review (usually the client)"
    )

    worker_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        comment="Worker being reviewed"
    )

    job_id: Mapped[UUID] = mapped_column(
        ForeignKey("jobs.id"),
        unique=True,
        nullable=False,
        comment="Associated job (enforces one review per job)"
    )

    rating: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Star rating from 1 to 5"
    )

    text: Mapped[str] = mapped_column(
        Text,
        nullable=True,
        comment="Optional textual feedback"
    )

    is_flagged: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Admin moderation flag"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        comment="Timestamp when review was created"
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
        comment="Timestamp when review was last updated"
    )

    # ----------------------------
    # Relationships
    # ----------------------------

    reviewer = relationship(
        "User",
        foreign_keys=[reviewer_id],
        back_populates="given_reviews"
    )

    worker = relationship(
        "User",
        foreign_keys=[worker_id],
        back_populates="received_reviews"
    )

    job = relationship(
        "Job",
        back_populates="review"
    )
