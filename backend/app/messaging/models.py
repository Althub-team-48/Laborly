"""
messaging/models.py

SQLAlchemy models for the reusable messaging system:
- MessageThread: Holds thread metadata for a conversation.
- ThreadParticipant: Links users to threads.
- Message: Individual messages sent within threads.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List

from sqlalchemy import Text, DateTime, Boolean, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.job.models import Job

if TYPE_CHECKING:
    from app.database.models import User


# ----------------------------------------
# MessageThread Model
# ----------------------------------------
class MessageThread(Base):
    __tablename__ = "message_threads"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique identifier for the message thread"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="Timestamp when the thread was created"
    )
    is_closed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Whether this thread is closed and no longer active"
    )

    # -------------------------------------
    # Relationships (grouped by type)
    # -------------------------------------
    # One-to-Many Relationships
    participants: Mapped[List["ThreadParticipant"]] = relationship(
        "ThreadParticipant",
        back_populates="thread",
        cascade="all, delete",
        # Relationship: One MessageThread can have many ThreadParticipants
    )
    messages: Mapped[List["Message"]] = relationship(
        "Message",
        back_populates="thread",
        cascade="all, delete",
        # Relationship: One MessageThread can have many Messages
    )

    # One-to-One Relationships
    job: Mapped["Job"] = relationship(
        "Job",
        back_populates="thread",
        uselist=False,
        # Relationship: One MessageThread is linked to one Job via Job.thread_id
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
        comment="Unique identifier for the thread participant"
    )
    thread_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("message_threads.id"),
        nullable=False,
        comment="The message thread this user is part of"
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        comment="User participating in the thread"
    )

    # -------------------------------------
    # Relationships (grouped by type)
    # -------------------------------------
    # Many-to-One Relationships
    thread: Mapped["MessageThread"] = relationship(
        "MessageThread",
        back_populates="participants",
        # Relationship: Many ThreadParticipants belong to one MessageThread
    )
    user: Mapped["User"] = relationship(
        "User",
        back_populates="threads",
        # Relationship: Many ThreadParticipants can reference one User
    )


# ----------------------------------------
# Message Model
# ----------------------------------------
class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique identifier for the message"
    )
    thread_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("message_threads.id"),
        nullable=False,
        comment="Thread this message belongs to"
    )
    sender_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        comment="User who sent this message"
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Content of the message"
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="Timestamp when the message was sent"
    )

    # -------------------------------------
    # Relationships (grouped by type)
    # -------------------------------------
    # Many-to-One Relationships
    thread: Mapped["MessageThread"] = relationship(
        "MessageThread",
        back_populates="messages",
        # Relationship: Many Messages belong to one MessageThread
    )
    sender: Mapped["User"] = relationship(
        "User",
        back_populates="sent_messages",
        # Relationship: Many Messages can be sent by one User
    )