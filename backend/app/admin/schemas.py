"""
admin/schemas.py

Defines response schemas for admin operations:
- KYC review status
- User status changes (freeze, ban, etc.)
- Flagged review listing
"""

from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime


# ----------------------------------------
# KYC Review Response Schema
# ----------------------------------------
class KYCReviewResponse(BaseModel):
    """
    Returned after admin reviews a user's KYC.
    """
    user_id: UUID = Field(..., description="User ID whose KYC was reviewed")
    status: str = Field(..., description="Updated KYC status")
    reviewed_at: datetime = Field(..., description="Time the KYC was reviewed")


# ----------------------------------------
# User Status Update Response Schema
# ----------------------------------------
class UserStatusUpdateResponse(BaseModel):
    """
    Returned after admin updates a user's status (ban, freeze, etc.).
    """
    user_id: UUID = Field(..., description="Affected user ID")
    action: str = Field(..., description="Action taken, e.g., 'frozen', 'banned', 'unbanned'")
    success: bool = Field(..., description="Whether the action was successful")
    timestamp: datetime = Field(..., description="Timestamp of the update")


# ----------------------------------------
# Flagged Review Read Schema
# ----------------------------------------
class FlaggedReviewRead(BaseModel):
    """
    Returned when listing reviews flagged for admin moderation.
    """
    review_id: UUID = Field(..., description="ID of the flagged review")
    user_id: UUID = Field(..., description="User who posted the review")
    job_id: UUID = Field(..., description="Job associated with the review")
    content: str = Field(..., description="Review content")
    is_flagged: bool = Field(..., description="Indicates if review was flagged")
    created_at: datetime = Field(..., description="Review creation time")

    class Config:
        from_attributes = True
