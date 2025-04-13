"""
client/models.py

Defines SQLAlchemy models specific to the Client module:
- ClientProfile: Stores additional profile information for a client user
- FavoriteWorker: Represents a relationship where a client marks a worker as a favorite
"""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.database.models import User


# ----------------------------------------------------
# ClientProfile Model
# ----------------------------------------------------
class ClientProfile(Base):
    """
    Represents additional profile data for users with the 'CLIENT' role.
    """
    __tablename__ = "client_profiles"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique identifier for a client profile"
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        unique=True,
        nullable=False,
        comment="ID of the user this profile belongs to"
    )
    business_name: Mapped[str] = mapped_column(
        String,
        nullable=True,
        comment="Optional business name for the client"
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

    # Relationship: one-to-one with User
    user: Mapped["User"] = relationship("User", back_populates="client_profile")


# ----------------------------------------------------
# FavoriteWorker Model
# ----------------------------------------------------
class FavoriteWorker(Base):
    """
    Represents a many-to-many relationship where a client user
    marks a worker user as a favorite.
    """
    __tablename__ = "favorites"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique identifier for a favorite entry"
    )
    client_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        comment="User ID of the client who favorited the worker"
    )
    worker_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        comment="User ID of the worker who was favorited"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        comment="Timestamp when the favorite relationship was created"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        comment="Timestamp when the favorite relationship was last updated"
    )

    # Relationship: many-to-one to User (as client)
    client: Mapped["User"] = relationship(
        "User",
        foreign_keys=[client_id],
        back_populates="favorite_clients"
    )

    # Relationship: many-to-one to User (as worker)
    worker: Mapped["User"] = relationship(
        "User",
        foreign_keys=[worker_id],
        back_populates="favorited_by"
    )
