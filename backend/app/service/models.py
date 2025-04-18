"""
service/models.py

Defines the SQLAlchemy model for services offered by workers.
Each service is linked to a worker (User with WORKER role).
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List

from sqlalchemy import String, Text, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.database.models import User
    from app.job.models import Job


class Service(Base):
    """
    Represents a service listing created by a worker.
    Services include details such as title, description, and location.
    """
    __tablename__ = "services"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique identifier for the service"
    )

    worker_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", use_alter=True, name="fk_services_worker_id", ondelete="CASCADE", deferrable=True, initially="DEFERRED"),
        nullable=False,
        comment="Worker (user) offering this service"
    )

    title: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Title or name of the service"
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=True,
        comment="Detailed description of the service"
    )

    location: Mapped[str] = mapped_column(
        String(100),
        nullable=True,
        comment="Location where the service is offered"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="Timestamp when the service was created"
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="Timestamp when the service was last updated"
    )

    # -------------------------------------
    # Relationships
    # -------------------------------------
    # Many-to-One Relationships
    worker: Mapped["User"] = relationship(
        "User",
        back_populates="services",
        lazy="joined",
        # Relationship: Many Services can be offered by one User (worker)
    )

    # One-to-Many Relationships
    jobs: Mapped[List["Job"]] = relationship(
        "Job",
        back_populates="service",
        lazy="joined",
        # Relationship: One Service can be associated with many Jobs
    )