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
- Job (created_jobs and assigned_jobs)
- Service (services)
- ThreadParticipant (threads)
- Message (sent_messages)
"""

import uuid
from datetime import datetime
from typing import List

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.enums import UserRole, KYCStatus
from app.client.models import ClientProfile, FavoriteWorker
from app.job.models import Job
from app.worker.models import WorkerProfile
from app.review.models import Review
from app.service.models import Service
from app.messaging.models import ThreadParticipant, Message


# -----------------------------------------------------
# User Model: Authenticated platform user
# -----------------------------------------------------
class User(Base):
    __tablename__ = "users"

    # Primary Key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique identifier for the user"
    )

    # Identity and Auth
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        comment="User's email address"
    )
    phone_number: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
        comment="User's phone number"
    )
    hashed_password: Mapped[str] = mapped_column(
        String,
        nullable=False,
        comment="Hashed password for authentication"
    )

    # Role-based access
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole),
        nullable=False,
        comment="User role (CLIENT, WORKER, ADMIN)"
    )

    # Profile Info
    first_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="User's first name"
    )
    last_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="User's last name"
    )
    middle_name: Mapped[str] = mapped_column(
        String(100),
        nullable=True,
        comment="User's middle name (optional)"
    )
    profile_picture: Mapped[str] = mapped_column(
        String,
        nullable=True,
        comment="Path to user's profile picture (optional)"
    )
    location: Mapped[str] = mapped_column(
        String,
        nullable=True,
        comment="User's location (optional)"
    )

    # Status Flags
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        comment="Whether the user account is active"
    )
    is_frozen: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Whether the user account is temporarily frozen"
    )
    is_banned: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Whether the user account is banned"
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Whether the user account is marked as deleted"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="Timestamp when the user was created"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="Timestamp when the user was last updated"
    )

    # -------------------------------------
    # Relationships (grouped by type)
    # -------------------------------------
    # One-to-One Relationships
    client_profile: Mapped["ClientProfile"] = relationship(
        "ClientProfile",
        back_populates="user",
        uselist=False,
        # Relationship: One User has one ClientProfile (if CLIENT role)
    )
    worker_profile: Mapped["WorkerProfile"] = relationship(
        "WorkerProfile",
        back_populates="user",
        uselist=False,
        # Relationship: One User has one WorkerProfile (if WORKER role)
    )
    kyc: Mapped["KYC"] = relationship(
        "KYC",
        back_populates="user",
        uselist=False,
        # Relationship: One User has one KYC record
    )

    # One-to-Many Relationships
    favorite_clients: Mapped[List["FavoriteWorker"]] = relationship(
        "FavoriteWorker",
        foreign_keys=[FavoriteWorker.client_id],
        back_populates="client",
        # Relationship: One User (client) can favorite many workers
    )
    favorited_by: Mapped[List["FavoriteWorker"]] = relationship(
        "FavoriteWorker",
        foreign_keys=[FavoriteWorker.worker_id],
        back_populates="worker",
        # Relationship: One User (worker) can be favorited by many clients
    )
    given_reviews: Mapped[List["Review"]] = relationship(
        "Review",
        back_populates="client",
        foreign_keys=[Review.client_id],
        # Relationship: One User (client) can give many Reviews
    )
    received_reviews: Mapped[List["Review"]] = relationship(
        "Review",
        back_populates="worker",
        foreign_keys=[Review.worker_id],
        # Relationship: One User (worker) can receive many Reviews
    )
    created_jobs: Mapped[List["Job"]] = relationship(
        "Job",
        back_populates="client",
        foreign_keys=[Job.client_id],
        # Relationship: One User (client) can create many Jobs
    )
    assigned_jobs: Mapped[List["Job"]] = relationship(
        "Job",
        back_populates="worker",
        foreign_keys=[Job.worker_id],
        # Relationship: One User (worker) can be assigned many Jobs
    )
    services: Mapped[List["Service"]] = relationship(
        "Service",
        back_populates="worker",
        # Relationship: One User (worker) can offer many Services
    )
    threads: Mapped[List["ThreadParticipant"]] = relationship(
        "ThreadParticipant",
        back_populates="user",
        # Relationship: One User can participate in many Threads
    )
    sent_messages: Mapped[List["Message"]] = relationship(
        "Message",
        back_populates="sender",
        # Relationship: One User can send many Messages
    )


# -----------------------------------------------------
# KYC Model: One-to-one identity verification
# -----------------------------------------------------
class KYC(Base):
    __tablename__ = "kyc"

    # Primary Key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique identifier for the KYC record"
    )

    # Relationship to User
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        unique=True,
        comment="Reference to the associated user"
    )

    # Document Details
    document_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Type of identification document"
    )
    document_path: Mapped[str] = mapped_column(
        String,
        nullable=False,
        comment="Path to the uploaded document"
    )
    selfie_path: Mapped[str] = mapped_column(
        String,
        nullable=False,
        comment="Path to the uploaded selfie"
    )

    # Status & Timestamps
    status: Mapped[KYCStatus] = mapped_column(
        Enum(KYCStatus),
        default=KYCStatus.PENDING,
        nullable=False,
        comment="KYC verification status (PENDING, APPROVED, REJECTED)"
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="Timestamp when the KYC was submitted"
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when the KYC was reviewed (optional)"
    )

    # -------------------------------------
    # Relationships (grouped by type)
    # -------------------------------------
    # One-to-One Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="kyc",
        # Relationship: One KYC record belongs to one User
    )