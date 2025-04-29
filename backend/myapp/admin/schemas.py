"""
backend/app/admin/schemas.py

Admin Response Schemas

Defines the schemas used in administrative operations including:
- User detail views
- KYC submission and review handling
- User status updates (freeze, ban, unban, delete)
- Flagged review management for moderation
- Pre-signed URL generation for KYC documents
- Generic success/info message responses
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl

from myapp.database.enums import KYCStatus, UserRole


# -----------------------------------------------------
# Admin User View Schema
# -----------------------------------------------------
class AdminUserView(BaseModel):
    """
    Detailed view of a user account for administrators.
    """

    id: UUID = Field(..., description="User's unique identifier")
    email: EmailStr = Field(..., description="User's email address")
    phone_number: str = Field(..., description="User's phone number")
    role: UserRole = Field(..., description="User's role (CLIENT, WORKER, ADMIN)")
    first_name: str = Field(..., description="User's first name")
    last_name: str = Field(..., description="User's last name")
    location: str | None = Field(None, description="User's location")
    is_active: bool = Field(..., description="Whether the user account is currently active")
    is_frozen: bool = Field(..., description="Whether the user account is temporarily frozen")
    is_banned: bool = Field(..., description="Whether the user account is banned")
    is_deleted: bool = Field(..., description="Whether the user account is marked as deleted")
    is_verified: bool = Field(..., description="Whether the user has verified their email")
    created_at: datetime = Field(..., description="Timestamp when the user was created")
    updated_at: datetime = Field(..., description="Timestamp when the user was last updated")

    model_config = ConfigDict(from_attributes=True)


# -----------------------------------------------------
# Pending KYC Submission Schema
# -----------------------------------------------------
class KYCPendingListItem(BaseModel):
    """
    Schema for listing users with pending KYC submissions.
    """

    user_id: UUID = Field(..., description="User ID associated with the KYC submission")
    document_type: str = Field(
        ..., description="Type of document submitted (e.g., Passport, Driver's License)"
    )
    submitted_at: datetime = Field(..., description="Timestamp when the KYC was submitted")

    model_config = ConfigDict(from_attributes=True)


# -----------------------------------------------------
# KYC Detail View Schema
# -----------------------------------------------------
class KYCDetailAdminView(BaseModel):
    """
    Detailed view of a specific KYC record for an administrator.
    """

    user_id: UUID = Field(..., description="User ID associated with the KYC submission")
    status: KYCStatus = Field(
        ..., description="Current status of the KYC submission (PENDING, APPROVED, REJECTED)"
    )
    document_type: str = Field(..., description="Type of document submitted")
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
    status: KYCStatus = Field(..., description="Updated KYC status after review")
    reviewed_at: datetime = Field(..., description="Timestamp of the review action")

    model_config = ConfigDict(from_attributes=True)


# -----------------------------------------------------
# User Status Update Response Schema
# -----------------------------------------------------
class UserStatusUpdateResponse(BaseModel):
    """
    Schema returned after an admin updates a user's status (freeze, ban, unban, etc.).
    """

    user_id: UUID = Field(..., description="ID of the user affected by the action")
    action: str = Field(..., description="Action taken on the user (e.g., 'frozen', 'banned')")
    success: bool = Field(..., description="Indicates if the action was successful")
    timestamp: datetime = Field(..., description="Timestamp when the update occurred")


# -----------------------------------------------------
# Flagged Review Read Schema
# -----------------------------------------------------
class FlaggedReviewRead(BaseModel):
    """
    Schema for reading information about flagged reviews requiring moderation.
    """

    id: UUID = Field(..., alias="review_id", description="Unique ID of the flagged review")
    client_id: UUID = Field(..., description="ID of the user who wrote the review")
    worker_id: UUID = Field(..., description="ID of the worker being reviewed")
    job_id: UUID = Field(..., description="ID of the job associated with the review")
    rating: int | None = Field(None, description="Star rating given in the review")
    review_text: str | None = Field(None, description="Content of the review text")
    is_flagged: bool = Field(..., description="Whether the review has been flagged for moderation")
    created_at: datetime = Field(..., description="Timestamp when the review was created")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# -----------------------------------------------------
# Generic Message Response Schema
# -----------------------------------------------------
class MessageResponse(BaseModel):
    """
    Schema for returning simple success or informational messages.
    """

    detail: str = Field(..., description="Message describing the operation result")


# -----------------------------------------------------
# Pre-signed URL Response Schema
# -----------------------------------------------------
class PresignedUrlResponse(BaseModel):
    """
    Schema for returning a generated pre-signed URL for temporary S3 document access.
    """

    url: HttpUrl = Field(..., description="Temporary pre-signed URL to access a protected resource")
