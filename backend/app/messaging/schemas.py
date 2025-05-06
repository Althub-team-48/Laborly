"""
backend/app/messaging/schemas.py

Messaging Schemas

Defines Pydantic schemas for the messaging system, including:
- Message creation and response models
- Thread structure models
- Participant information models
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.job.models import JobStatus
from app.service.schemas import ServiceBase


# ---------------------------------------------------
# Partial Schemas for Embedding
# ---------------------------------------------------
class ThreadJobServiceInfo(ServiceBase):
    """Partial service information for embedding within ThreadJobInfo."""

    id: UUID = Field(..., description="Service's unique identifier")

    model_config = ConfigDict(from_attributes=True)


class ThreadJobInfo(BaseModel):
    """Partial job information for embedding in ThreadRead."""

    id: UUID = Field(..., description="Job's unique identifier")
    status: JobStatus = Field(..., description="Current status of the job")
    service: ThreadJobServiceInfo | None = Field(
        None, description="Partial details of the service related to the job"
    )

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------
# Participant Information Schema
# ---------------------------------------------------
class ParticipantInfo(BaseModel):
    """
    Basic information about a user involved in a message thread.
    """

    id: UUID = Field(..., description="User ID")
    first_name: str = Field(..., description="User's first name")
    last_name: str = Field(..., description="User's last name")
    profile_picture: HttpUrl | None = Field(None, description="URL to the user's profile picture")

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------
# Base Message Schema
# ---------------------------------------------------
class MessageBase(BaseModel):
    """
    Base schema for message content.
    """

    content: str = Field(..., description="Content of the message")


# ---------------------------------------------------
# Message Creation Schema
# ---------------------------------------------------
class MessageCreate(MessageBase):
    """
    Schema for creating a new message, either new thread or reply.
    """

    thread_id: UUID | None = Field(None, description="Thread ID if replying to an existing thread")
    job_id: UUID | None = Field(None, description="Job ID associated with the message")
    service_id: UUID | None = Field(None, description="Service ID associated with the message")


# ---------------------------------------------------
# Message Response Schema
# ---------------------------------------------------
class MessageRead(MessageBase):
    """
    Schema for reading a message, including sender information.
    """

    id: UUID = Field(..., description="Unique identifier for the message")
    sender: ParticipantInfo = Field(..., description="Information about the message sender")
    thread_id: UUID = Field(..., description="Thread ID the message belongs to")
    timestamp: datetime = Field(..., description="Timestamp when the message was sent")

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------
# Thread Initiation Schema
# ---------------------------------------------------
class ThreadInitiate(MessageBase):
    """
    Schema for initiating a new message thread.
    """

    service_id: UUID = Field(..., description="Service ID associated with the initial message")
    receiver_id: UUID | None = Field(None, description="Receiver ID (required if sender is Admin)")


# ---------------------------------------------------
# Thread Participant Schema
# ---------------------------------------------------
class ThreadParticipantRead(BaseModel):
    """
    Schema for reading thread participant details.
    """

    user: ParticipantInfo = Field(..., description="Information about the thread participant")

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------
# Thread with Messages Schema
# ---------------------------------------------------
class ThreadRead(BaseModel):
    """
    Detailed view of a message thread, including participants and messages.
    """

    id: UUID = Field(..., description="Unique identifier for the message thread")
    created_at: datetime = Field(..., description="Timestamp when the thread was created")
    job: ThreadJobInfo | None = Field(
        None, description="Partial job details if thread is job-related"
    )
    is_closed: bool = Field(..., description="Whether the thread is closed and inactive")
    participants: list[ThreadParticipantRead] = Field(
        ..., description="List of users involved in the thread"
    )
    messages: list[MessageRead] = Field(
        ..., description="List of messages in the thread, ordered by timestamp"
    )

    model_config = ConfigDict(from_attributes=True)
