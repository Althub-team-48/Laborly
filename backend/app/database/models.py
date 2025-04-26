"""
backend/app/database/models.py

Core SQLAlchemy ORM Models

Defines:
- User: Authenticated user accounts with role-based access
- KYC: One-to-one KYC verification attached to users

Includes relationships with:
- ClientProfile
- WorkerProfile
- FavoriteWorker (favorites system)
- Review (given_reviews and received_reviews)
- Job (created_jobs and assigned_jobs)
- Service (services offered by workers)
- ThreadParticipant (messaging threads)
- Message (sent messages)
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, func
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

# ---------------------------------------------------
# User Model: Authenticated Platform User
# ---------------------------------------------------


class User(Base):
    __tablename__ = "users"

    # -------------------------------------
    # Fields
    # -------------------------------------
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique identifier for the user",
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, comment="User's email address"
    )
    phone_number: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False, comment="User's phone number"
    )
    hashed_password: Mapped[str] = mapped_column(
        String, nullable=False, comment="Hashed password for authentication"
    )
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole), nullable=False, comment="User role (CLIENT, WORKER, ADMIN)"
    )
    first_name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="User's first name"
    )
    last_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="User's last name")
    middle_name: Mapped[str] = mapped_column(
        String(100), nullable=True, comment="User's middle name (optional)"
    )
    profile_picture: Mapped[str] = mapped_column(
        String, nullable=True, comment="Path to user's profile picture (optional)"
    )
    location: Mapped[str] = mapped_column(
        String, nullable=True, comment="User's location (optional)"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, comment="Whether the user account is active"
    )
    is_frozen: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="Whether the user account is temporarily frozen"
    )
    is_banned: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="Whether the user account is banned"
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="Whether the user account is marked as deleted"
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="Whether the user's email is verified"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="Timestamp when the user was created",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="Timestamp when the user was last updated",
    )

    # -------------------------------------
    # Relationships (With Inline Explanations)
    # -------------------------------------

    # One-to-One: A user may have a client profile if role is CLIENT
    client_profile: Mapped["ClientProfile"] = relationship(
        "ClientProfile", back_populates="user", uselist=False
    )

    # One-to-One: A user may have a worker profile if role is WORKER
    worker_profile: Mapped["WorkerProfile"] = relationship(
        "WorkerProfile", back_populates="user", uselist=False
    )

    # One-to-One: A user can have one KYC verification record
    kyc: Mapped["KYC"] = relationship("KYC", back_populates="user", uselist=False)

    # One-to-Many: A client can favorite multiple workers
    favorite_clients: Mapped[list["FavoriteWorker"]] = relationship(
        "FavoriteWorker",
        foreign_keys=[FavoriteWorker.client_id],
        back_populates="client",
    )

    # One-to-Many: A worker can be favorited by multiple clients
    favorited_by: Mapped[list["FavoriteWorker"]] = relationship(
        "FavoriteWorker",
        foreign_keys=[FavoriteWorker.worker_id],
        back_populates="worker",
    )

    # One-to-Many: A client can give many reviews to workers
    given_reviews: Mapped[list["Review"]] = relationship(
        "Review",
        back_populates="client",
        foreign_keys=[Review.client_id],
    )

    # One-to-Many: A worker can receive many reviews from clients
    received_reviews: Mapped[list["Review"]] = relationship(
        "Review",
        back_populates="worker",
        foreign_keys=[Review.worker_id],
    )

    # One-to-Many: A client can create multiple jobs
    created_jobs: Mapped[list["Job"]] = relationship(
        "Job",
        back_populates="client",
        foreign_keys=[Job.client_id],
    )

    # One-to-Many: A worker can be assigned to multiple jobs
    assigned_jobs: Mapped[list["Job"]] = relationship(
        "Job",
        back_populates="worker",
        foreign_keys=[Job.worker_id],
    )

    # One-to-Many: A worker can offer multiple services
    services: Mapped[list["Service"]] = relationship(
        "Service",
        back_populates="worker",
    )

    # One-to-Many: A user can participate in multiple message threads
    threads: Mapped[list["ThreadParticipant"]] = relationship(
        "ThreadParticipant",
        back_populates="user",
    )

    # One-to-Many: A user can send multiple messages
    sent_messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="sender",
    )


# ---------------------------------------------------
# KYC Model: User Identity Verification
# ---------------------------------------------------


class KYC(Base):
    __tablename__ = "kyc"

    # -------------------------------------
    # Fields
    # -------------------------------------
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique identifier for the KYC record",
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            use_alter=True,
            name="fk_kyc_user_id",
            deferrable=True,
            initially="DEFERRED",
        ),
        nullable=False,
        unique=True,
        comment="Reference to the associated user",
    )
    document_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="Type of identification document"
    )
    document_path: Mapped[str] = mapped_column(
        String, nullable=False, comment="Path to uploaded document"
    )
    selfie_path: Mapped[str] = mapped_column(
        String, nullable=False, comment="Path to uploaded selfie"
    )
    status: Mapped[KYCStatus] = mapped_column(
        Enum(KYCStatus),
        default=KYCStatus.PENDING,
        nullable=False,
        comment="KYC verification status (PENDING, APPROVED, REJECTED)",
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="Timestamp when the KYC was submitted",
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when the KYC was reviewed",
    )

    # -------------------------------------
    # Relationships (With Inline Explanation)
    # -------------------------------------

    # One-to-One: A KYC record belongs to a single user
    user: Mapped["User"] = relationship(
        "User",
        back_populates="kyc",
    )
