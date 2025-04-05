"""
service/models.py

Defines the SQLAlchemy model for services offered by workers.
Each service is linked to a user with the WORKER role.
"""

import uuid
from sqlalchemy import String, Text, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.models import User


class Service(Base):
    __tablename__ = "services"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique identifier for the service"
    )
    worker_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
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
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="Timestamp when the service was created"
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="Timestamp when the service was last updated"
    )

    # Relationships
    worker: Mapped["User"] = relationship(
        "User",
        backref="services",
        lazy="joined" # Loads the worker's user info immediately in the same database query
    )
