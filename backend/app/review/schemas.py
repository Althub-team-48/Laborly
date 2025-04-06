"""
review/schemas.py

Defines Pydantic schemas for job reviews:
- ReviewWrite: Client-submitted rating and text
- ReviewRead: Full response with metadata
- WorkerReviewSummary: Aggregated rating data for workers
"""

from uuid import UUID
from typing import Optional, Annotated
from datetime import datetime
from pydantic import BaseModel, Field


# -------------------------------------------------------
# Schema for Creating a Review (Client)
# -------------------------------------------------------
class ReviewWrite(BaseModel):
    """
    Payload schema used when submitting a review for a completed job.
    """
    rating: Annotated[int, Field(ge=1, le=5, description="Rating from 1 (lowest) to 5 (highest)")]
    text: Optional[str] = Field(
        default=None,
        description="Optional text feedback from the client"
    )


# -------------------------------------------------------
# Schema for Reading a Review (Response)
# -------------------------------------------------------
class ReviewRead(BaseModel):
    """
    Full review response schema returned in GET endpoints.
    """
    id: UUID = Field(..., description="Review ID")
    reviewer_id: UUID = Field(..., description="ID of the user who submitted the review")
    worker_id: UUID = Field(..., description="ID of the worker being reviewed")
    job_id: UUID = Field(..., description="ID of the associated job")
    rating: int = Field(..., description="Star rating given by the client (1–5)")
    text: Optional[str] = Field(default=None, description="Optional textual feedback")
    is_flagged: bool = Field(..., description="Whether this review is flagged for moderation")
    created_at: datetime = Field(..., description="Timestamp when the review was created")
    updated_at: datetime = Field(..., description="Timestamp when the review was last updated")

    class Config:
        from_attributes = True


# -------------------------------------------------------
# Schema for Aggregated Review Summary
# -------------------------------------------------------
class WorkerReviewSummary(BaseModel):
    """
    Summary schema representing review statistics for a worker.
    """
    average_rating: float = Field(..., description="Average star rating for the worker")
    total_reviews: int = Field(..., description="Total number of reviews received")
