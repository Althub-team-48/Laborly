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

from app.job.schemas import JobServiceInfo
from app.job.models import JobStatus


# ---------------------------------------------------
# Partial Schemas for Embedding in Review Responses
# ---------------------------------------------------
class ReviewClientInfo(BaseModel):
    """Partial client information for embedding in review responses."""

    id: UUID = Field(..., description="Client's unique identifier")
    first_name: str = Field(..., description="Client's first name")
    last_name: str = Field(..., description="Client's last name")

    model_config = ConfigDict(from_attributes=True)


class ReviewWorkerInfo(BaseModel):
    """Partial worker information for embedding in review responses."""

    id: UUID = Field(..., description="Worker's unique identifier")
    first_name: str = Field(..., description="Worker's first name")
    last_name: str = Field(..., description="Worker's last name")

    model_config = ConfigDict(from_attributes=True)


class ReviewJobInfo(BaseModel):
    """Partial job information for embedding in review responses."""

    id: UUID = Field(..., description="Job's unique identifier")
    status: JobStatus = Field(..., description="Status of the job at the time of review or current")
    service: JobServiceInfo | None = Field(None, description="Partial service details for the job")

    model_config = ConfigDict(from_attributes=True)


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
    client: ReviewClientInfo = Field(
        ..., description="Details of the client who submitted the review"
    )
    worker: ReviewWorkerInfo = Field(..., description="Details of the worker being reviewed")
    job: ReviewJobInfo = Field(..., description="Details of the associated job")

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
    client: ReviewClientInfo = Field(
        ..., description="Partial details of the client who wrote the review"
    )
    worker: ReviewWorkerInfo = Field(..., description="Details of the worker being reviewed")
    job: ReviewJobInfo = Field(..., description="Partial details of the associated job")

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
