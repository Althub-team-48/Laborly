"""
auth/schemas.py

Defines Pydantic models for authentication flows:
- Login & signup request payloads
- JWT token responses and payloads
- Authenticated user response shape
"""

from pydantic import BaseModel, EmailStr, Field
from uuid import UUID
from datetime import datetime
from app.database.enums import UserRole


# -------------------------
# AUTH REQUEST SCHEMAS
# -------------------------
class LoginRequest(BaseModel):
    """
    Payload for user login via JSON.
    """
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=6, max_length=64, description="User password (6-64 characters)")


class SignupRequest(BaseModel):
    """
    Payload for user registration.
    """
    email: EmailStr = Field(..., description="Email address for new account")
    password: str = Field(..., min_length=6, max_length=64, description="Password for the account (6-64 characters)")
    first_name: str = Field(..., max_length=50, description="User's first name")
    last_name: str = Field(..., max_length=50, description="User's last name")
    role: UserRole = Field(..., description="Role of the user: CLIENT, WORKER, or ADMIN")


# -------------------------
# AUTH TOKEN SCHEMAS
# -------------------------
class TokenResponse(BaseModel):
    """
    JWT token response model after successful login.
    """
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Type of the token")


class TokenPayload(BaseModel):
    """
    JWT token payload data decoded from the token.
    """
    sub: UUID = Field(..., description="Subject (user ID) from token")
    role: UserRole = Field(..., description="Role embedded in the token")
    exp: int = Field(..., description="Token expiration timestamp")


# -------------------------
# AUTH RESPONSE SCHEMAS
# -------------------------
class AuthUserResponse(BaseModel):
    """
    Serialized authenticated user data.
    """
    id: UUID = Field(..., description="Unique identifier of the user")
    email: EmailStr = Field(..., description="User's email address")
    first_name: str = Field(..., description="User's first name")
    last_name: str = Field(..., description="User's last name")
    role: UserRole = Field(..., description="User's role in the system")
    created_at: datetime = Field(..., description="Time user was created")
    updated_at: datetime = Field(..., description="Time user was last updated")

    class Config:
        from_attributes = True


class AuthSuccessResponse(BaseModel):
    """
    Successful authentication response containing JWT and user.
    """
    access_token: str = Field(..., description="JWT access token")
    user: AuthUserResponse = Field(..., description="Authenticated user details")
