"""
admin/schemas.py

Defines response schemas for admin operations:
- KYC review status update
- User status changes (e.g., freeze, ban, unban)
- Flagged review information for moderation
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# -----------------------------------------------------
# KYC Review Response Schema
# -----------------------------------------------------
class KYCReviewResponse(BaseModel):
    """
    Schema returned after an admin reviews a user's KYC submission.
    """

    user_id: UUID = Field(..., description="User ID whose KYC was reviewed")
    status: str = Field(..., description="Updated KYC status after review")
    reviewed_at: datetime = Field(..., description="Timestamp when the KYC was reviewed")


# -----------------------------------------------------
# User Status Update Response Schema
# -----------------------------------------------------
class UserStatusUpdateResponse(BaseModel):
    """
    Schema returned after an admin updates a user's status (e.g., ban, freeze).
    """

    user_id: UUID = Field(..., description="ID of the user affected by the action")
    action: str = Field(..., description="Action taken on the user (e.g., 'frozen', 'banned')")
    success: bool = Field(..., description="Indicates if the action was successful")
    timestamp: datetime = Field(..., description="Timestamp of when the update occurred")


# -----------------------------------------------------
# Flagged Review Read Schema
# -----------------------------------------------------
class FlaggedReviewRead(BaseModel):
    """
    Schema for reading flagged review information.
    """

    id: UUID = Field(..., alias="review_id", description="Unique ID of the flagged review")
    client_id: UUID = Field(..., alias="user_id", description="ID of the user who wrote the review")
    job_id: UUID = Field(..., description="ID of the job associated with the review")
    rating: int | None = Field(None, description="Star rating given in the review")
    review_text: str | None = Field(None, alias="content", description="Text content of the review")
    is_flagged: bool = Field(..., description="Indicates whether the review is flagged")
    created_at: datetime = Field(..., description="Date and time the review was created")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# -----------------------------------------------------
# Generic Message Response Schema
# -----------------------------------------------------
class MessageResponse(BaseModel):
    """
    Generic response schema for simple success or info messages.
    """

    detail: str = Field(..., description="Description of the operation result")
