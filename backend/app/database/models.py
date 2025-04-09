"""
database/models.py

Defines core SQLAlchemy ORM models shared across the platform:
- User: Authenticated user accounts with role-based access
- KYC: One-to-one KYC verification attached to each user

Includes relationships with:
- ClientProfile
- WorkerProfile
- FavoriteWorker (favorites feature)
- Review (given_reviews and received_reviews)
"""

import uuid
from typing import List

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.enums import UserRole, KYCStatus
from app.client.models import ClientProfile, FavoriteWorker
from app.worker.models import WorkerProfile
from app.review.models import Review


# -----------------------------------------------------
# User Model: Authenticated platform user
# -----------------------------------------------------
class User(Base):
    __tablename__ = "users"

    # Primary Key
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    # Identity and Auth
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    phone_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)

    # Role-based access
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
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # One-to-one Relationships
    client_profile: Mapped["ClientProfile"] = relationship("ClientProfile", back_populates="user", uselist=False)
    worker_profile: Mapped["WorkerProfile"] = relationship("WorkerProfile", back_populates="user", uselist=False)
    kyc: Mapped["KYC"] = relationship("KYC", back_populates="user", uselist=False)

    # Favorites (many-to-many through FavoriteWorker)
    favorite_clients: Mapped[List["FavoriteWorker"]] = relationship("FavoriteWorker", foreign_keys="[FavoriteWorker.client_id]")
    favorited_by: Mapped[List["FavoriteWorker"]] = relationship("FavoriteWorker", foreign_keys="[FavoriteWorker.worker_id]")

    # Reviews
    given_reviews: Mapped[List["Review"]] = relationship("Review", back_populates="client", foreign_keys="[Review.client_id]")
    received_reviews: Mapped[List["Review"]] = relationship("Review", back_populates="worker", foreign_keys="[Review.worker_id]")


# -----------------------------------------------------
# KYC Model: One-to-one identity verification
# -----------------------------------------------------
class KYC(Base):
    __tablename__ = "kyc"

    # Primary Key
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    # Relationship to User
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, unique=True)

    # Document Details
    document_type: Mapped[str] = mapped_column(String(50), nullable=False)
    document_path: Mapped[str] = mapped_column(String, nullable=False)
    selfie_path: Mapped[str] = mapped_column(String, nullable=False)

    # Status & Timestamps
    status: Mapped[KYCStatus] = mapped_column(Enum(KYCStatus), default=KYCStatus.PENDING, nullable=False)
    submitted_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    reviewed_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationship back to User
    user: Mapped["User"] = relationship("User", back_populates="kyc")
