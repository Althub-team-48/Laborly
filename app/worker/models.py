"""
worker/models.py

Defines SQLAlchemy models specific to the Worker module:
- WorkerProfile: Stores profile and availability details for a worker
"""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import (
    String,
    Text,
    DateTime,
    ForeignKey,
    Boolean,
    Integer
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import mapped_column, Mapped, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.database.models import User


# ------------------------------------------------------
# WorkerProfile Model
# ------------------------------------------------------
class WorkerProfile(Base):
    __tablename__ = "worker_profiles"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique identifier for a worker profile"
    )

    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        unique=True,
        nullable=False,
        comment="Related user account"
    )

    bio: Mapped[str] = mapped_column(
        Text,
        nullable=True,
        comment="Short biography of the worker"
    )

    years_experience: Mapped[int] = mapped_column(
        Integer,
        nullable=True,
        comment="Number of years of relevant experience"
    )

    availability_note: Mapped[str] = mapped_column(
        Text,
        nullable=True,
        comment="Custom note regarding availability (e.g., preferred hours)"
    )

    is_available: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Availability status for taking on job assignments"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        comment="Timestamp when the profile was created"
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        comment="Timestamp when the profile was last updated"
    )

    # One-to-one relationship with the User model
    user: Mapped["User"] = relationship("User", back_populates="worker_profile")
