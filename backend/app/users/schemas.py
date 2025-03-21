"""
[users] schemas.py

Defines Pydantic schemas and enums for user management:
- User creation, update, output
- Role validation and normalization
- Token and login request models
"""

from typing import Optional, List
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, EmailStr, field_validator


# --- Enum Definitions ---

class UserRole(str, Enum):
    ADMIN = "ADMIN"
    CLIENT = "CLIENT"
    WORKER = "WORKER"


# --- Base User Schema ---

class UserBase(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    phone_number: str
    role: str

    @field_validator("role")
    @classmethod
    def normalize_role(cls, value: str) -> UserRole:
        """
        Ensures role is a valid UserRole enum and normalizes to uppercase.
        """
        upper_value = value.upper()
        if upper_value not in UserRole.__members__:
            raise ValueError(f"Invalid role. Must be one of: {', '.join(UserRole.__members__.keys())}")
        return UserRole[upper_value]

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        """
        Ensures name fields are at least 2 characters.
        """
        if len(value.strip()) < 2:
            raise ValueError("First name and last name must be at least 2 characters long.")
        return value.strip()

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        """
        Validates phone number contains only digits and is between 10–15 digits.
        """
        digits = ''.join(filter(str.isdigit, value))
        if len(digits) < 10 or len(digits) > 15:
            raise ValueError("Phone number must be between 10 and 15 digits.")
        return digits


# --- Request Schemas ---

class UserCreate(UserBase):
    """
    Schema for creating a new user.
    Includes required password field.
    """
    password: str


class UserUpdate(BaseModel):
    """
    Schema for updating user details.
    All fields are optional for partial/full update use cases.
    """
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    role: Optional[str] = None
    is_verified: Optional[bool] = None
    last_active: Optional[datetime] = None

    @field_validator("role")
    @classmethod
    def normalize_role_optional(cls, value: Optional[str]) -> Optional[UserRole]:
        """
        Optional validator for role field during updates.
        Converts to uppercase and validates enum membership.
        """
        if value is None:
            return None
        upper_value = value.upper()
        if upper_value not in UserRole.__members__:
            raise ValueError(f"Invalid role. Must be one of: {', '.join(UserRole.__members__.keys())}")
        return UserRole[upper_value]

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_optional_name(cls, value: Optional[str]) -> Optional[str]:
        """
        Ensures name fields are valid if provided.
        """
        if value is not None and len(value.strip()) < 2:
            raise ValueError("First name and last name must be at least 2 characters long.")
        return value.strip() if value else value

    @field_validator("phone_number")
    @classmethod
    def validate_optional_phone(cls, value: Optional[str]) -> Optional[str]:
        """
        Validates phone number format if provided.
        """
        if value is None:
            return None
        digits = ''.join(filter(str.isdigit, value))
        if len(digits) < 10 or len(digits) > 15:
            raise ValueError("Phone number must be between 10 and 15 digits.")
        return digits


# --- Response Schemas ---

class UserOut(BaseModel):
    """
    Schema for serialized user output.
    Includes all relevant fields returned in API responses.
    """
    id: int
    email: EmailStr
    first_name: str
    last_name: str
    phone_number: str
    role: UserRole
    is_verified: bool
    last_active: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # Enables ORM model parsing


class UserList(BaseModel):
    """
    Schema for a list of users returned to admin endpoints.
    """
    users: List[UserOut]


# --- Auth Schemas ---

class Token(BaseModel):
    """
    Schema representing a JWT token returned on successful login.
    """
    access_token: str
    token_type: str


class LoginRequest(BaseModel):
    """
    Schema for submitting login credentials.
    """
    email: EmailStr
    password: str
