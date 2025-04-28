"""
backend/app/review/schemas.py

Review Schemas
Defines Pydantic schemas for job reviews:
- ReviewWrite: Client-submitted rating and optional text
- ReviewRead: Full response including metadata for authenticated views
- PublicReviewRead: Public view of review data (limited fields)
- WorkerReviewSummary: Aggregated rating statistics for a worker
"""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------
# Schema for Creating a Review (Client)
# ---------------------------------------------------


class ReviewWrite(BaseModel):
    """Payload schema used when submitting a review for a completed job."""

    rating: Annotated[int, Field(ge=1, le=5, description="Rating from 1 (lowest) to 5 (highest)")]
    text: str | None = Field(default=None, description="Optional text feedback from the client")


# ---------------------------------------------------
# Schema for Reading a Review (Authenticated Response)
# ---------------------------------------------------


class ReviewRead(BaseModel):
    """Full review response schema returned to authenticated users, including moderation flags."""

    id: UUID = Field(..., description="Review ID")
    client_id: UUID = Field(..., description="ID of the user (client) who submitted the review")
    worker_id: UUID = Field(..., description="ID of the worker being reviewed")
    job_id: UUID = Field(..., description="ID of the associated job")
    rating: int = Field(..., description="Star rating given by the client (1–5)")
    text: str | None = Field(default=None, description="Optional textual feedback")
    is_flagged: bool = Field(..., description="Whether the review is flagged for moderation")
    created_at: datetime = Field(..., description="Timestamp when the review was created")

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------
# Schema for Public View of a Review
# ---------------------------------------------------


class PublicReviewRead(BaseModel):
    """Schema for public view of a review, excluding sensitive information."""

    id: UUID = Field(..., description="Review ID")
    worker_id: UUID = Field(..., description="ID of the worker being reviewed")
    job_id: UUID = Field(..., description="ID of the associated job (for reference)")
    rating: int = Field(..., description="Star rating given by the client (1–5)")
    text: str | None = Field(default=None, description="Optional textual feedback")
    created_at: datetime = Field(..., description="Timestamp when the review was created")

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------
# Schema for Aggregated Review Summary
# ---------------------------------------------------


class WorkerReviewSummary(BaseModel):
    """Summary schema showing average rating and total review count for a worker."""

    average_rating: float = Field(..., description="Average star rating for the worker")
    total_reviews: int = Field(..., description="Total number of reviews received")
