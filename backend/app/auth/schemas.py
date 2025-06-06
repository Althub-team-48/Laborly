"""
auth/schemas.py

Defines Pydantic models for authentication flows:
- Login & signup request payloads
- JWT token payload and response structure
- Authenticated user response schema
- Factory method for Google OAuth user creation
- Forgot password and email update schemas
"""

from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
)

from app.core.validators import password_validator
from app.database.enums import UserRole
from app.database.models import User

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
        description="Password must include uppercase, lowercase, digit, special character, and only ASCII characters.",
    )


class SignupRequest(BaseModel):
    """
    Request schema for new user registration.
    """

    email: EmailStr = Field(..., description="Email address for new account")

    phone_number: str = Field(
        ..., min_length=10, max_length=15, description="Phone number for the new account"
    )
    password: PasswordStr = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Password must include uppercase, lowercase, digit, special character, and only ASCII characters.",
    )
    first_name: str = Field(..., max_length=50, description="User's first name")
    last_name: str = Field(..., max_length=50, description="User's last name")
    role: UserRole = Field(..., description="User role: CLIENT, WORKER, or ADMIN")

    @field_validator("email")
    def normalize_email(cls, v: str) -> str:
        """
        Normalize the email address by stripping leading/trailing whitespace
        and converting it to lowercase.
        """
        email = str(v.strip().lower())
        return email


# --------------------------------------------------
# PASSWORD RESET SCHEMAS
# --------------------------------------------------
class ForgotPasswordRequest(BaseModel):
    """
    Request schema for initiating the password reset process.
    """

    email: EmailStr = Field(..., description="Email address of the user requesting password reset")


class ResetPasswordRequest(BaseModel):
    """
    Request schema for resetting the password using a token.
    """

    token: str = Field(..., description="Password reset token received via email")
    new_password: PasswordStr = Field(
        ...,
        min_length=8,
        max_length=128,
        description="New password (must meet complexity requirements)",
    )


# --------------------------------------------------
# EMAIL UPDATE SCHEMAS
# --------------------------------------------------
class UpdateEmailRequest(BaseModel):
    """
    Request schema for initiating an email address update.
    Requires authentication.
    """

    new_email: EmailStr = Field(..., description="The desired new email address")


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
    Decoded JWT payload structure for access tokens.
    """

    sub: UUID = Field(..., description="Subject (user ID)")
    role: UserRole = Field(..., description="User role encoded in the token")
    exp: int = Field(..., description="Expiration timestamp of the token")
    jti: str = Field(..., description="JWT ID (used for token blacklist)")


class VerificationTokenPayload(BaseModel):
    """
    Decoded JWT payload structure for verification tokens (email, password reset, etc.).
    Includes optional fields specific to the verification type.
    """

    sub: UUID = Field(..., description="Subject (user ID)")
    type: str = Field(
        ...,
        description="Type of verification token (e.g., 'email_verification', 'password_reset', 'new_email_verification')",
    )
    exp: int = Field(..., description="Expiration timestamp of the token")
    new_email: EmailStr | None = Field(
        None, description="The new email address being verified (used for email updates)"
    )


# --------------------------------------------------
# AUTH RESPONSE SCHEMAS
# --------------------------------------------------
class AuthUserResponse(BaseModel):
    """
    Response schema representing authenticated user data.
    """

    id: UUID = Field(..., description="Unique identifier for the user")
    email: EmailStr = Field(..., description="User's email address")
    phone_number: str | None = Field(None, description="User's phone number")
    first_name: str = Field(..., description="User's first name")
    last_name: str = Field(..., description="User's last name")
    role: UserRole = Field(..., description="User's role in the system")
    is_verified: bool = Field(..., description="Indicates if the user's email is verified")
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
# OAuth State Token Schema
# --------------------------------------------------
class OAuthStatePayload(BaseModel):
    """
    Payload for the short-lived JWT used as the OAuth state parameter.
    """

    role: UserRole | None = Field(None, description="Intended user role for signup")
    nonce: str = Field(..., description="Cryptographic nonce for CSRF protection")


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
    phone_number: str | None
    hashed_password: str
    role: UserRole

    @classmethod
    def from_google(
        cls,
        user_info: dict[str, Any],
        hashed_password: str,
        assigned_role: UserRole,
    ) -> "UserCreate":
        """
        Factory method to generate user data from Google OAuth2 payload.
        """
        return cls(
            email=user_info.get("email", ""),
            first_name=user_info.get("given_name", ""),
            last_name=user_info.get("family_name", ""),
            phone_number=user_info.get("phone_number") or None,
            hashed_password=hashed_password,
            role=getattr(UserRole, assigned_role.upper(), UserRole.CLIENT),
        )


# --------------------------------------------------
# GOOGLE OAUTH CODE EXCHANGE SCHEMA
# --------------------------------------------------
class GoogleCodeExchangeRequest(BaseModel):
    """
    Schema for receiving the authorization code from the frontend
    to be exchanged for tokens at the backend.
    """

    code: str = Field(
        ..., description="The authorization code received from Google via frontend redirect"
    )
    state: str | None = Field(None, description="State parameter for verification")


class LoginResponse(BaseModel):
    """
    Response schema after successful login, containing user details.
    The access token is set separately in an HttpOnly cookie.
    """

    user: AuthUserResponse = Field(..., description="Details of the authenticated user")


class InternalLoginResult(BaseModel):
    """Internal model to pass login results from service to route."""

    user: User
    access_token: str

    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)
