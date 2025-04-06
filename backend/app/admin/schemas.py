"""
admin/schemas.py

Defines response schemas for admin operations:
- KYC review status update
- User status changes (e.g., freeze, ban, unban)
- Flagged review information for moderation
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


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
    Schema used when returning reviews flagged for moderation.
    """
    review_id: UUID = Field(..., description="Unique ID of the flagged review")
    user_id: UUID = Field(..., description="ID of the user who wrote the review")
    job_id: UUID = Field(..., description="ID of the job associated with the review")
    content: str = Field(..., description="Text content of the review")
    is_flagged: bool = Field(..., description="Indicates whether the review is flagged")
    created_at: datetime = Field(..., description="Date and time the review was created")

    class Config:
        from_attributes = True  # Enables conversion from ORM models
