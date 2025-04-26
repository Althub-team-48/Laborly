"""
admin/schemas.py

Defines response schemas for admin operations:
- KYC review status update
- User status changes (e.g., freeze, ban, unban)
- Flagged review information for moderation
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.database.enums import KYCStatus


# -----------------------------------------------------
# Schema for Listing Pending KYC Items
# -----------------------------------------------------
class KYCPendingListItem(BaseModel):
    """
    Schema for items in the list of pending KYC submissions.
    """

    user_id: UUID = Field(..., description="User ID associated with the KYC submission")
    document_type: str = Field(
        ..., description="Type of document submitted (e.g., Passport, Driver's License)"
    )
    submitted_at: datetime = Field(..., description="Timestamp when the KYC was submitted")

    model_config = ConfigDict(from_attributes=True)


# -----------------------------------------------------
# Schema for Detailed Admin View of a KYC Record
# -----------------------------------------------------
class KYCDetailAdminView(BaseModel):
    """
    Detailed view of a specific KYC record for an admin.
    """

    user_id: UUID = Field(..., description="User ID associated with the KYC submission")
    status: KYCStatus = Field(
        ..., description="Current status of the KYC submission (PENDING, APPROVED, REJECTED)"
    )
    document_type: str = Field(
        ..., description="Type of document submitted (e.g., Passport, Driver's License)"
    )
    submitted_at: datetime = Field(..., description="Timestamp when the KYC was submitted")
    reviewed_at: datetime | None = Field(
        None, description="Timestamp when the KYC was reviewed (if applicable)"
    )

    model_config = ConfigDict(from_attributes=True)


# -----------------------------------------------------
# KYC Review Action Response Schema
# -----------------------------------------------------
class KYCReviewActionResponse(BaseModel):
    """
    Schema returned after an admin approves or rejects a KYC submission.
    """

    user_id: UUID = Field(..., description="User ID whose KYC was reviewed")
    status: KYCStatus = Field(
        ..., description="Updated KYC status after review (APPROVED or REJECTED)"
    )
    reviewed_at: datetime = Field(
        ..., description="Timestamp when the KYC review action was performed"
    )

    model_config = ConfigDict(from_attributes=True)


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


# -----------------------------------------------------
# Pre-signed URL Response Schema
# -----------------------------------------------------
class PresignedUrlResponse(BaseModel):
    """
    Schema for returning a generated pre-signed S3 URL.
    """

    url: HttpUrl = Field(..., description="Temporary pre-signed URL to access the S3 object")
