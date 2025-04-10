"""
messaging/schemas.py

Pydantic schemas for reusable messaging system:
- Message creation and response
- Thread structure and participant responses
"""

from uuid import UUID
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


# -------------------------------
# Base Schema for Messages
# -------------------------------
class MessageBase(BaseModel):
    content: str = Field(..., description="Content of the message")


# -------------------------------
# Message Creation Schema
# -------------------------------
class MessageCreate(MessageBase):
    thread_id: Optional[UUID] = Field(None, description="Thread ID if replying to an existing thread")
    receiver_id: Optional[UUID] = Field(None, description="Receiver ID if starting a new thread")
    job_id: Optional[UUID] = Field(None, description="Job ID associated with the message (required for non-admins)")
    service_id: Optional[UUID] = Field(None, description="Service ID associated with the message (required for non-admins)")


# -------------------------------
# Message Response Schema
# -------------------------------
class MessageRead(MessageBase):
    id: UUID = Field(..., description="Unique identifier for the message")
    sender_id: UUID = Field(..., description="User ID of the message sender")
    timestamp: datetime = Field(..., description="Timestamp when the message was sent")

    model_config = ConfigDict(from_attributes=True)


# -------------------------------
# Thread Initiate Schema
# -------------------------------
class ThreadInitiate(BaseModel):
    content: str = Field(..., description="Message content to start a new thread")
    service_id: UUID = Field(..., description="Service ID to associate with the message")


# -------------------------------
# Thread Participant Schema
# -------------------------------
class ThreadParticipantRead(BaseModel):
    user_id: UUID = Field(..., description="User ID of the participant")

    model_config = ConfigDict(from_attributes=True)



# -------------------------------
# Thread with Messages Schema
# -------------------------------
class ThreadRead(BaseModel):
    id: UUID = Field(..., description="Unique identifier for the message thread")
    created_at: datetime = Field(..., description="Timestamp when the thread was created")
    job_id: Optional[UUID] = Field(None, description="Associated job ID if thread is job-related")
    is_closed: bool = Field(..., description="Flag indicating if the thread is closed")
    participants: List[ThreadParticipantRead] = Field(..., description="Users involved in the thread")
    messages: List[MessageRead] = Field(..., description="Messages in the thread")

    model_config = ConfigDict(from_attributes=True)

