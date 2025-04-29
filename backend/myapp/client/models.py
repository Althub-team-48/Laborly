"""
backend/app/client/models.py

Client Database Models
Defines SQLAlchemy models specific to the Client module:
- ClientProfile: Stores additional profile information for a client user.
- FavoriteWorker: Represents the relationship where a client marks a worker as a favorite.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from myapp.database.base import Base

if TYPE_CHECKING:
    from myapp.database.models import User


# ---------------------------------------------------
# Client Profile Model
# ---------------------------------------------------


class ClientProfile(Base):
    """Represents additional profile data for users with the 'CLIENT' role."""

    __tablename__ = "client_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique identifier for the client profile",
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            use_alter=True,
            name="fk_client_profiles_user_id",
            deferrable=True,
            initially="DEFERRED",
        ),
        nullable=False,
        comment="Linked user ID for this client profile",
    )

    profile_description: Mapped[str] = mapped_column(
        String,
        nullable=True,
        comment="Optional profile description or note",
    )

    address: Mapped[str] = mapped_column(
        String,
        nullable=True,
        comment="Optional client address",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="Timestamp when the client profile was created",
    )

    # ---------------------------------------------------
    # Relationships
    # ---------------------------------------------------

    user: Mapped["User"] = relationship(
        "User",
        back_populates="client_profile",
        foreign_keys=[user_id],
        # Relationship: One ClientProfile belongs to one User
    )


# ---------------------------------------------------
# Favorite Worker Model
# ---------------------------------------------------


class FavoriteWorker(Base):
    """Represents a many-to-many relationship where a client marks a worker as a favorite."""

    __tablename__ = "favorites"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique identifier for the favorite relationship",
    )

    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            use_alter=True,
            name="fk_favorite_client_id",
            deferrable=True,
            initially="DEFERRED",
        ),
        nullable=False,
        comment="User ID of the client who favorited the worker",
    )

    worker_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            use_alter=True,
            name="fk_client_profiles_worker_id",
            deferrable=True,
            initially="DEFERRED",
        ),
        nullable=False,
        comment="User ID of the worker who was favorited",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="Timestamp when the favorite relationship was created",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="Timestamp when the favorite relationship was last updated",
    )

    # ---------------------------------------------------
    # Relationships
    # ---------------------------------------------------

    client: Mapped["User"] = relationship(
        "User",
        foreign_keys=[client_id],
        back_populates="favorite_clients",
        # Relationship: Many FavoriteWorker records can reference one User (client)
    )

    worker: Mapped["User"] = relationship(
        "User",
        foreign_keys=[worker_id],
        back_populates="favorited_by",
        # Relationship: Many FavoriteWorker records can reference one User (worker)
    )
