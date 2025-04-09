"""
review/models.py

Defines the Review model for storing job-related feedback.
- Each review is linked to a specific job and user pair.
- Supports star ratings, optional text, and admin flagging.
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.database.models import User


class Review(Base):
    """
    Review submitted by a client about a worker for a specific job.
    Includes a star rating (1-5), optional review text, and admin moderation flag.
    """
    __tablename__ = "reviews"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    # Review content
    review_text: Mapped[str] = mapped_column(String, nullable=True)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationships
    client_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    worker_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)

    # Admin moderation
    is_flagged: Mapped[bool] = mapped_column(Boolean, default=False)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationship mappings
    client: Mapped["User"] = relationship("User", back_populates="given_reviews", foreign_keys=[client_id])
    worker: Mapped["User"] = relationship("User", back_populates="received_reviews", foreign_keys=[worker_id])
