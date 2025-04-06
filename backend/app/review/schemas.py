"""
schemas.py

Defines Pydantic schemas for job reviews:
- Review creation (write)
- Review retrieval (read)
- Summary of reviews for a worker
"""

from uuid import UUID
from typing import Optional, Annotated
from datetime import datetime
from pydantic import BaseModel, Field


# ----------------------------------------
# Schema for creating a review
# ----------------------------------------
class ReviewWrite(BaseModel):
    rating: Annotated[int, Field(ge=1, le=5, description="Rating from 1 to 5")]
    text: Optional[str] = Field(default=None, description="Optional review text")


# ----------------------------------------
# Schema for reading a review
# ----------------------------------------
class ReviewRead(BaseModel):
    id: UUID = Field(..., description="Review ID")
    reviewer_id: UUID = Field(..., description="ID of the reviewer (client)")
    worker_id: UUID = Field(..., description="ID of the worker being reviewed")
    job_id: UUID = Field(..., description="ID of the job the review is linked to")
    rating: int = Field(..., description="Rating given to the worker")
    text: Optional[str] = Field(default=None, description="Optional review content")
    is_flagged: bool = Field(..., description="Whether this review was flagged")
    created_at: datetime = Field(..., description="Timestamp when the review was created")
    updated_at: datetime = Field(..., description="Timestamp when the review was last updated")

    class Config:
        from_attributes = True


# ----------------------------------------
# Summary schema for worker reviews
# ----------------------------------------
class WorkerReviewSummary(BaseModel):
    average_rating: float = Field(..., description="Average rating for the worker")
    total_reviews: int = Field(..., description="Total number of reviews received")
