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
        ForeignKey("users.id"),
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

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="Timestamp when the profile was created"
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