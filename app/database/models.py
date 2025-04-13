"""
models.py

Defines core SQLAlchemy ORM models shared across the platform:
- User: Authenticated user accounts with role-based access
- KYC: One-to-one KYC verification attached to each user

Also includes relationships with:
- ClientProfile
- WorkerProfile
- FavoriteWorker (favorites feature)
"""

import uuid
from typing import List

from sqlalchemy import (
    String, Boolean, Enum, DateTime, ForeignKey, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.enums import UserRole, KYCStatus
from app.client.models import ClientProfile, FavoriteWorker
from app.worker.models import WorkerProfile


# -------------------------------------------------
# USER MODEL
# -------------------------------------------------
class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4
    )

    # Basic Identity
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    phone_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)

    # Role: CLIENT, WORKER, or ADMIN
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False)

    # Profile Info
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    middle_name: Mapped[str] = mapped_column(String(100), nullable=True)
    profile_picture: Mapped[str] = mapped_column(String, nullable=True)
    location: Mapped[str] = mapped_column(String, nullable=True)

    # Status Flags
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_frozen: Mapped[bool] = mapped_column(Boolean, default=False)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)

    # Timestamps
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # -------------------------
    # Relationships
    # -------------------------

    # One-to-one with ClientProfile
    client_profile: Mapped["ClientProfile"] = relationship(
        "ClientProfile", back_populates="user", uselist=False
    )

    # One-to-one with WorkerProfile
    worker_profile: Mapped["WorkerProfile"] = relationship(
        "WorkerProfile", back_populates="user", uselist=False
    )

    # One-to-one with KYC
    kyc: Mapped["KYC"] = relationship(
        "KYC", back_populates="user", uselist=False
    )

    # Users this client has favorited
    favorite_clients: Mapped[List["FavoriteWorker"]] = relationship(
        "FavoriteWorker",
        foreign_keys="[FavoriteWorker.client_id]"
    )

    # Users who favorited this worker
    favorited_by: Mapped[List["FavoriteWorker"]] = relationship(
        "FavoriteWorker",
        foreign_keys="[FavoriteWorker.worker_id]"
    )


# -------------------------------------------------
# KYC MODEL
# -------------------------------------------------
class KYC(Base):
    __tablename__ = "kyc"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        unique=True
    )

    document_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Type of document submitted (e.g., Passport, NIN)"
    )

    document_path: Mapped[str] = mapped_column(
        String,
        nullable=False,
        comment="File path to uploaded document"
    )

    selfie_path: Mapped[str] = mapped_column(
        String,
        nullable=False,
        comment="File path to uploaded selfie"
    )

    status: Mapped[KYCStatus] = mapped_column(
        Enum(KYCStatus),
        default=KYCStatus.PENDING,
        nullable=False,
        comment="KYC status: PENDING, APPROVED, REJECTED"
    )

    submitted_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    reviewed_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Time admin reviewed KYC"
    )

    # Relationship to parent user
    user: Mapped["User"] = relationship("User", back_populates="kyc")
