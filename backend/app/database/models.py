"""
models.py

Defines SQLAlchemy ORM shared models used across the platform, like:
- User and KYC verification
- Includes role-based access and one-to-one KYC relationship
"""

from typing import List
import uuid
from sqlalchemy import (
    String, Boolean, Enum, DateTime, ForeignKey, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base
from app.database.enums import UserRole, KYCStatus
from app.client.models import ClientProfile, FavoriteWorker


# -------------------------
# USER MODEL
# -------------------------
class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False)

    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    middle_name: Mapped[str] = mapped_column(String(100), nullable=True)
    profile_picture: Mapped[str] = mapped_column(String, nullable=True)
    location: Mapped[str] = mapped_column(String, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # Relationships
    client_profile: Mapped["ClientProfile"] = relationship("ClientProfile", back_populates="user", uselist=False)
    kyc: Mapped["KYC"] = relationship("KYC", back_populates="user", uselist=False)
    # Which workers did this user favorite?
    favorite_clients: Mapped[List["FavoriteWorker"]] = relationship("FavoriteWorker", foreign_keys="[FavoriteWorker.client_id]")
    # Which users (clients) favorited me?
    favorited_by: Mapped[List["FavoriteWorker"]] = relationship("FavoriteWorker", foreign_keys="[FavoriteWorker.worker_id]")



# -------------------------
# KYC MODEL
# -------------------------
class KYC(Base):
    __tablename__ = "kyc"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, unique=True)

    document_type: Mapped[str] = mapped_column(String(50), nullable=False)
    document_path: Mapped[str] = mapped_column(String, nullable=False)
    selfie_path: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[KYCStatus] = mapped_column(Enum(KYCStatus), default=KYCStatus.PENDING, nullable=False)
    submitted_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    reviewed_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="kyc")
