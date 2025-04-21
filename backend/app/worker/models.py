"""
worker/models.py

Defines SQLAlchemy models specific to the Worker module:
- WorkerProfile: Stores profile and availability details for a worker
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.database.models import User


# ------------------------------------------------------
# WorkerProfile Model
# ------------------------------------------------------
class WorkerProfile(Base):
    """
    Represents additional profile information for users with the 'WORKER' role.
    Stores professional background and experience of the worker.
    """
    __tablename__ = "worker_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique identifier for the worker profile"
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", use_alter=True, name="fk_worker_profiles_user_id", deferrable=True, initially="DEFERRED"),
        nullable=False,
        comment="Reference to the associated user"
    )

    professional_skills: Mapped[str] = mapped_column(
        String,
        nullable=True,
        comment="Comma-separated list of skills (e.g., plumbing, carpentry)"
    )

    work_experience: Mapped[str] = mapped_column(
        String,
        nullable=True,
        comment="Brief summary of the worker's experience or background"
    )

    years_experience: Mapped[int] = mapped_column(
        nullable=True,
        comment="Number of years of experience"
    )

    availability_note: Mapped[str] = mapped_column(
        String,
        nullable=True,
        comment="Custom note about availability"
    )

    bio: Mapped[str] = mapped_column(
        String,
        nullable=True,
        comment="Short biography of the worker"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="Timestamp when the profile was created"
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="Timestamp when the profile was last updated"
    )

    is_available: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
        comment="Availability status for job assignments"
    )

    is_kyc_verified: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
        comment="KYC verification status"
    )
    
    # -------------------------------------
    # Relationships
    # -------------------------------------
    # One-to-One Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="worker_profile",
        foreign_keys=[user_id],
        # Relationship: One WorkerProfile belongs to one User
    )