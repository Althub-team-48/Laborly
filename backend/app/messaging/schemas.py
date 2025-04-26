"""
messaging/schemas.py

Pydantic schemas for reusable messaging system:
- Message creation and response
- Thread structure and participant responses
"""

from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class ParticipantInfo(BaseModel):
    """Basic information about a user involved in messaging."""

    id: UUID = Field(..., description="User ID")
    first_name: str = Field(..., description="User's first name")
    last_name: str = Field(..., description="User's last name")
    profile_picture: HttpUrl | None = Field(None, description="URL to user's profile picture")

    model_config = ConfigDict(from_attributes=True)


# -------------------------------
# Base Schema for Messages
# -------------------------------
class MessageBase(BaseModel):
    content: str = Field(..., description="Content of the message")


# -------------------------------
# Message Creation Schema
# -------------------------------
class MessageCreate(MessageBase):
    thread_id: UUID | None = Field(None, description="Thread ID if replying to an existing thread")
    job_id: UUID | None = Field(None, description="Job ID associated with the message")
    service_id: UUID | None = Field(None, description="Service ID associated with the message")


# -------------------------------
# Message Response Schema (Updated)
# -------------------------------
class MessageRead(MessageBase):
    """Schema for reading a message, including sender info."""

    id: UUID = Field(..., description="Unique identifier for the message")
    sender: ParticipantInfo = Field(..., description="Information about the message sender")
    thread_id: UUID = Field(..., description="Thread ID the message belongs to")
    timestamp: datetime = Field(..., description="Timestamp when the message was sent")

    model_config = ConfigDict(from_attributes=True)


# -------------------------------
# Thread Initiate Schema
# -------------------------------
class ThreadInitiate(MessageBase):
    service_id: UUID = Field(..., description="Service ID to associate with the message")
    receiver_id: UUID | None = Field(None, description="Required if sender is Admin")


# -------------------------------
# Thread Participant Schema (Updated)
# -------------------------------
class ThreadParticipantRead(BaseModel):
    """Schema for reading thread participant details."""

    user: ParticipantInfo = Field(..., description="Information about the participant")
    model_config = ConfigDict(from_attributes=True)


# -------------------------------
# Thread with Messages Schema (Updated)
# -------------------------------
class ThreadRead(BaseModel):
    """Detailed view of a thread including participants and messages."""

    id: UUID = Field(..., description="Unique identifier for the message thread")
    created_at: datetime = Field(..., description="Timestamp when the thread was created")
    job_id: UUID | None = Field(None, description="Associated job ID if thread is job-related")
    is_closed: bool = Field(..., description="Flag indicating if the thread is closed")
    participants: list[ThreadParticipantRead] = Field(
        ..., description="Users involved in the thread"
    )
    messages: list[MessageRead] = Field(
        ..., description="Messages in the thread, typically ordered by timestamp"
    )

    model_config = ConfigDict(from_attributes=True)
