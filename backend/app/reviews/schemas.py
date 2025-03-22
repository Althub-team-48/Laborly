"""
[reviews] schemas.py

Defines Pydantic models for review handling:
- Creation, update, output, and validation
- Enforces rating range and structured output
"""

from typing import Optional, List
from datetime import datetime

from pydantic import BaseModel, field_validator
from users.schemas import UserOut
from jobs.schemas import JobOut


# --- Base Review Schema ---

class ReviewBase(BaseModel):
    job_id: int
    reviewee_id: int
    rating: int

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, value: int) -> int:
        """
        Ensures that the rating is between 1 and 5.
        """
        if not 1 <= value <= 5:
            raise ValueError("Rating must be between 1 and 5")
        return value


# --- Create Review ---

class ReviewCreate(ReviewBase):
    """
    Schema for creating a new review.
    Inherits job_id, reviewee_id, and rating.
    """
    pass


# --- Update Review ---

class ReviewUpdate(BaseModel):
    """
    Schema for updating a review (admin only).
    Allows optional rating updates.
    """
    rating: Optional[int] = None

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, value: Optional[int]) -> Optional[int]:
        """
        Validates optional rating to ensure it is within 1 to 5.
        """
        if value is not None and not 1 <= value <= 5:
            raise ValueError("Rating must be between 1 and 5")
        return value


# --- Review Output Schema ---

class ReviewOut(BaseModel):
    """
    Output schema for returning a review with user and job details.
    """
    id: int
    job: JobOut
    reviewer: UserOut
    reviewee: UserOut
    rating: int
    created_at: datetime

    class Config:
        from_attributes = True  # Enable ORM to Pydantic conversion


# --- Review List ---

class ReviewList(BaseModel):
    """
    Wrapper schema for a list of reviews.
    """
    reviews: List[ReviewOut]
