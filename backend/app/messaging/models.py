"""
messaging/models.py

SQLAlchemy models for the reusable messaging system:
- MessageThread: Holds thread metadata for a conversation.
- ThreadParticipant: Links users to threads.
- Message: Individual messages sent within threads.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Text, DateTime, Boolean, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.database.models import User
    from app.job.models import Job


# ----------------------------------------
# Message Model (Define Message first)
# ----------------------------------------
class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique identifier for the message",
    )
    thread_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "message_threads.id",
            use_alter=True,
            name="fk_messages_thread_id",
            deferrable=True,
            initially="DEFERRED",
        ),
        nullable=False,
        comment="Thread this message belongs to",
    )
    sender_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            use_alter=True,
            name="fk_messages_sender_id",
            deferrable=True,
            initially="DEFERRED",
        ),
        nullable=False,
        comment="User who sent this message",
    )
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="Content of the message")
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Timestamp when the message was sent",
    )

    # Relationships
    thread: Mapped["MessageThread"] = relationship(
        "MessageThread",
        back_populates="messages",
    )
    sender: Mapped["User"] = relationship("User", back_populates="sent_messages", lazy="joined")


# ----------------------------------------
# MessageThread Model
# ----------------------------------------
class MessageThread(Base):
    __tablename__ = "message_threads"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique identifier for the message thread",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Timestamp when the thread was created",
    )
    is_closed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether this thread is closed and no longer active",
    )
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "jobs.id",
            use_alter=True,
            name="fk_message_threads_job_id",
            deferrable=True,
            initially="DEFERRED",
            ondelete="SET NULL",
        ),
        nullable=True,
        unique=True,
        comment="Optional Job this thread is associated with",
    )

    # Relationships
    participants: Mapped[list["ThreadParticipant"]] = relationship(
        "ThreadParticipant", back_populates="thread", cascade="all, delete-orphan", lazy="selectin"
    )
    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="thread",
        cascade="all, delete-orphan",
        order_by=Message.timestamp.asc(),
        lazy="selectin",
    )

    job: Mapped[Optional["Job"]] = relationship(
        "Job", back_populates="thread", foreign_keys=[job_id]
    )


# ----------------------------------------
# ThreadParticipant Model
# ----------------------------------------
class ThreadParticipant(Base):
    __tablename__ = "thread_participants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique identifier for the thread participant",
    )
    thread_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("message_threads.id", ondelete="CASCADE"),
        nullable=False,
        comment="The message thread this user is part of",
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="User participating in the thread",
    )

    # Relationships
    thread: Mapped["MessageThread"] = relationship(
        "MessageThread",
        back_populates="participants",
    )
    user: Mapped["User"] = relationship("User", back_populates="threads", lazy="joined")
