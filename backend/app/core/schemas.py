# backend/app/core/schemas.py
"""
backend/app/core/schemas.py

Core Schemas

Defines core Pydantic models used across the application, including:
- Generic paginated response schema.
"""

from typing import Generic, TypeVar

from pydantic import BaseModel, Field


# Define a type variable for the items in the paginated response
T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Generic schema for paginated list responses.
    """

    total_count: int = Field(..., description="Total number of items available")
    has_next_page: bool = Field(..., description="Indicates if there are more items available")
    items: list[T] = Field(..., description="List of items for the current page")
