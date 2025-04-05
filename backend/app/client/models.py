"""
client/models.py

Defines SQLAlchemy models specific to the Client module:
- ClientProfile: Stores profile information for a client
- FavoriteWorker: Represents workers marked as favorites by a client
"""

from datetime import datetime, timezone
import uuid
from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import mapped_column, Mapped, relationship

from app.database.base import Base
from app.database.models import User


class ClientProfile(Base):
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
        comment="Related user account"
    )
    business_name: Mapped[str] = mapped_column(
        String,
        nullable=True,
        comment="Optional business name"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        comment="Profile creation timestamp"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        comment="Profile update timestamp"
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="client_profile")


class FavoriteWorker(Base):
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
        comment="Client who favorited the worker"
    )
    worker_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        comment="Favorited worker"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        comment="When the favorite was created"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        comment="When the favorite was last updated"
    )

    # Relationships
    client: Mapped["User"] = relationship("User", foreign_keys=[client_id], back_populates="favorite_clients")
    worker: Mapped["User"] = relationship("User", foreign_keys=[worker_id], back_populates="favorited_by")
