"""
core/exceptions.py

Description:
Defines a standard error response format for the API.
"""

from fastapi import HTTPException
from typing import Any

class APIError(HTTPException):
    """Custom exception with standardized error response."""
    def __init__(self, status_code: int, message: str, headers: dict[str, Any] = None):
        super().__init__(status_code=status_code, detail={"error": message}, headers=headers)