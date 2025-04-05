"""
auth/schemas.py

Defines Pydantic models for authentication flows:
- Login & signup request payloads
- JWT token responses and payloads
- Authenticated user response shape
- Utility factory for Google OAuth user creation
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
    Request body schema for user login via JSON.
    """
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=6, max_length=64, description="User password (6–64 characters)")


class SignupRequest(BaseModel):
    """
    Request body schema for user registration.
    """
    email: EmailStr = Field(..., description="Email address for new account")
    phone_number: str = Field(..., min_length=10, max_length=15, description="Phone number for new account")
    password: str = Field(..., min_length=6, max_length=64, description="Password for the account (6–64 characters)")
    first_name: str = Field(..., max_length=50, description="User's first name")
    last_name: str = Field(..., max_length=50, description="User's last name")
    role: UserRole = Field(..., description="User role: CLIENT, WORKER, or ADMIN")


# -------------------------
# AUTH TOKEN SCHEMAS
# -------------------------
class TokenResponse(BaseModel):
    """
    Response schema containing JWT access token.
    """
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Type of the token")


class TokenPayload(BaseModel):
    """
    Decoded payload structure from JWT token.
    """
    sub: UUID = Field(..., description="Subject (user ID)")
    role: UserRole = Field(..., description="Role embedded in the token")
    exp: int = Field(..., description="Token expiration timestamp")


# -------------------------
# AUTH RESPONSE SCHEMAS
# -------------------------
class AuthUserResponse(BaseModel):
    """
    Response schema for authenticated user object.
    """
    id: UUID = Field(..., description="Unique identifier for the user")
    email: EmailStr = Field(..., description="User's email address")
    phone_number: str = Field(..., description="User's phone number")
    first_name: str = Field(..., description="User's first name")
    last_name: str = Field(..., description="User's last name")
    role: UserRole = Field(..., description="User's role in the system")
    created_at: datetime = Field(..., description="Timestamp when user was created")
    updated_at: datetime = Field(..., description="Timestamp when user was last updated")

    class Config:
        from_attributes = True


class AuthSuccessResponse(BaseModel):
    """
    Response schema for successful authentication (token + user).
    """
    access_token: str = Field(..., description="JWT access token")
    user: AuthUserResponse = Field(..., description="Authenticated user details")


# -------------------------
# GOOGLE OAUTH FACTORY SCHEMA
# -------------------------
class UserCreate(BaseModel):
    """
    Factory schema for creating a user from Google OAuth info.
    """
    email: EmailStr
    first_name: str
    last_name: str
    phone_number: str
    hashed_password: str
    role: UserRole

    @classmethod
    def from_google(cls, user_info: dict, hashed_password: str, default_role: str = "CLIENT") -> "UserCreate":
        """
        Factory method to create user data from Google OAuth payload.
        """
        return cls(
            email=user_info.get("email"),
            first_name=user_info.get("given_name"),
            last_name=user_info.get("family_name"),
            phone_number=user_info.get("phone_number") or "0000000000",
            hashed_password=hashed_password,
            role=getattr(UserRole, default_role.upper(), UserRole.CLIENT)
        )
