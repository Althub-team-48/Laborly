"""
messaging/models.py

SQLAlchemy models for the reusable messaging system:
- MessageThread: Holds thread metadata for a conversation.
- ThreadParticipant: Links users to threads.
- Message: Individual messages sent within threads.
"""

from typing import TYPE_CHECKING
import uuid
from datetime import datetime

from sqlalchemy import Text, DateTime, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.database.models import User

# ----------------------------------------
# MessageThread Model
# ----------------------------------------
class MessageThread(Base):
    __tablename__ = "message_threads"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
        comment="Unique identifier for the message thread"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow,
        comment="Timestamp when the thread was created"
    )
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=True,
        comment="Optional job linked to this thread"
    )
    is_closed: Mapped[bool] = mapped_column(
        Boolean, default=False,
        comment="Whether this thread is closed and no longer active"
    )

    # Relationships
    participants = relationship(
        "ThreadParticipant",
        back_populates="thread",
        cascade="all, delete"
    )
    messages = relationship(
        "Message",
        back_populates="thread",
        cascade="all, delete"
    )


# ----------------------------------------
# ThreadParticipant Model
# ----------------------------------------
class ThreadParticipant(Base):
    __tablename__ = "thread_participants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
        comment="Unique identifier for the thread participant"
    )
    thread_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("message_threads.id"),
        comment="The message thread this user is part of"
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"),
        comment="User participating in the thread"
    )

    # Relationships
    thread = relationship("MessageThread", back_populates="participants")
    user = relationship("User")


# ----------------------------------------
# Message Model
# ----------------------------------------
class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
        comment="Unique identifier for the message"
    )
    thread_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("message_threads.id"),
        comment="Thread this message belongs to"
    )
    sender_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"),
        comment="User who sent this message"
    )
    content: Mapped[str] = mapped_column(
        Text, nullable=False,
        comment="Content of the message"
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow,
        comment="Timestamp when the message was sent"
    )

    # Relationships
    thread = relationship("MessageThread", back_populates="messages")
    sender = relationship("User")