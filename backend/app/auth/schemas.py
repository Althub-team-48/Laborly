"""
auth/schemas.py

Defines Pydantic models for authentication flows:
- Login & signup request payloads
- JWT token payload and response structure
- Authenticated user response schema
- Factory method for Google OAuth user creation
"""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    AfterValidator,
)

from app.core.validators import password_validator
from app.database.enums import UserRole


# --------------------------------------------------
# Custom Types
# --------------------------------------------------

PasswordStr = Annotated[str, AfterValidator(password_validator)]


# --------------------------------------------------
# AUTH REQUEST SCHEMAS
# --------------------------------------------------

class LoginRequest(BaseModel):
    """
    Request schema for user login using JSON payload.
    """
    email: EmailStr = Field(..., description="User email address")
    password: PasswordStr = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Password must include uppercase, lowercase, digit, special character, and only ASCII characters."
    )


class SignupRequest(BaseModel):
    """
    Request schema for new user registration.
    """
    email: EmailStr = Field(..., description="Email address for new account")
    phone_number: str = Field(..., min_length=10, max_length=15, description="Phone number for the new account")
    password: PasswordStr = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Password must include uppercase, lowercase, digit, special character, and only ASCII characters."
    )
    first_name: str = Field(..., max_length=50, description="User's first name")
    last_name: str = Field(..., max_length=50, description="User's last name")
    role: UserRole = Field(..., description="User role: CLIENT, WORKER, or ADMIN")


# --------------------------------------------------
# AUTH TOKEN SCHEMAS
# --------------------------------------------------

class TokenResponse(BaseModel):
    """
    Response schema for JWT access token.
    """
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Type of the token (default: bearer)")


class TokenPayload(BaseModel):
    """
    Decoded JWT payload structure.
    """
    sub: UUID = Field(..., description="Subject (user ID)")
    role: UserRole = Field(..., description="User role encoded in the token")
    exp: int = Field(..., description="Expiration timestamp of the token")
    jti: str = Field(..., description="JWT ID (used for token blacklist)")


# --------------------------------------------------
# AUTH RESPONSE SCHEMAS
# --------------------------------------------------

class AuthUserResponse(BaseModel):
    """
    Response schema representing authenticated user data.
    """
    id: UUID = Field(..., description="Unique identifier for the user")
    email: EmailStr = Field(..., description="User's email address")
    phone_number: str = Field(..., description="User's phone number")
    first_name: str = Field(..., description="User's first name")
    last_name: str = Field(..., description="User's last name")
    role: UserRole = Field(..., description="User's role in the system")
    created_at: datetime = Field(..., description="Timestamp when the user was created")
    updated_at: datetime = Field(..., description="Timestamp when the user was last updated")

    model_config = ConfigDict(from_attributes=True)


class AuthSuccessResponse(BaseModel):
    """
    Response schema after successful login or signup.
    """
    access_token: str = Field(..., description="JWT access token")
    user: AuthUserResponse = Field(..., description="Details of the authenticated user")


class MessageResponse(BaseModel):
    """
    Generic message response schema.
    """
    detail: str = Field(..., description="Response message detail")


# --------------------------------------------------
# GOOGLE OAUTH FACTORY SCHEMA
# --------------------------------------------------

class UserCreate(BaseModel):
    """
    Schema used to create a user instance from Google OAuth2 profile data.
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
        Factory method to generate user data from Google OAuth2 payload.
        """
        return cls(
            email=user_info.get("email"),
            first_name=user_info.get("given_name"),
            last_name=user_info.get("family_name"),
            phone_number=user_info.get("phone_number") or "0000000000",
            hashed_password=hashed_password,
            role=getattr(UserRole, default_role.upper(), UserRole.CLIENT)
        )
