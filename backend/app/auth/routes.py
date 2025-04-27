"""
auth/routes.py

Handles authentication routes including:
- User registration and login via JSON or OAuth2
- Google OAuth2 login flow
- JWT token issuance and user logout handling
- Email verification, password reset, and secure email update
"""

import logging

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

# Updated Schema Imports
from app.auth.schemas import (
    AuthSuccessResponse,
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    ResetPasswordRequest,
    SignupRequest,
    UpdateEmailRequest,
)

# Updated Service Imports
from app.auth.services import (
    handle_google_callback,
    handle_google_login,
    login_user_json,
    login_user_oauth,
    logout_user_token,
    request_email_update,
    request_new_verification_email,
    request_password_reset,
    reset_password,
    signup_user,
    verify_email_token,
    verify_new_email,
)

from app.core.dependencies import oauth2_scheme, get_current_user
from app.database.session import get_db
from app.core.limiter import limiter
from app.database.models import User

# ---------------------------------------------------
# Router Configuration
# ---------------------------------------------------
router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = logging.getLogger(__name__)


# ---------------------------------------------------
# Registration
# ---------------------------------------------------
@router.post(
    "/signup",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register New User",
    description="Registers a new user and sends a verification email.",
)
@limiter.limit("5/minute")  # Rate limit signup
async def signup(
    request: Request,
    payload: SignupRequest,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """
    Registers a new user.
    """
    return await signup_user(payload, db)


# ---------------------------------------------------
# Login (JSON)
# ---------------------------------------------------
@router.post(
    "/login/json",
    response_model=AuthSuccessResponse,
    status_code=status.HTTP_200_OK,
    summary="Login with JSON",
    description="Authenticates user using email and password via JSON request body. Requires email verification.",
)
@limiter.limit("10/minute")
async def login_json(
    request: Request,
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> AuthSuccessResponse:
    """
    Authenticates a user using email and password from a JSON request.
    """
    return await login_user_json(payload, db)


# ---------------------------------------------------
# Login (OAuth2 Form)
# ---------------------------------------------------
@router.post(
    "/login/oauth",
    response_model=AuthSuccessResponse,
    status_code=status.HTTP_200_OK,
    summary="Login with OAuth2 Form",
    description="Authenticates user using OAuth2-compatible form data (username = email). Requires email verification.",
)
@limiter.limit("10/minute")  # Rate limit login attempts
async def login_oauth(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> AuthSuccessResponse:
    """
    Authenticates a user using OAuth2 form data.
    """
    return await login_user_oauth(form_data, db)


# ---------------------------------------------------
# Google OAuth2 Login Flow
# ---------------------------------------------------
@router.get(
    "/google/login",
    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    summary="Start Google OAuth2 Flow",
    description="Redirects the user to Google's OAuth2 consent screen.",
    response_description="Redirects to Google authentication page.",
)
@limiter.limit("10/minute")
async def google_login(request: Request) -> RedirectResponse:
    """
    Initiates the Google OAuth2 login flow by redirecting to Google.
    """
    return await handle_google_login(request)


@router.get(
    "/google/callback",
    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    summary="Handle Google OAuth2 Callback",
    description="Handles the callback from Google after OAuth2 login, authenticates or registers the user, and redirects.",
    response_description="Redirects to the frontend application with an access token.",
)
@limiter.limit("10/minute")
async def google_callback(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """
    Handles the Google OAuth2 callback and authenticates the user.
    """
    return await handle_google_callback(request, db)


# ---------------------------------------------------
# Logout
# ---------------------------------------------------
@router.post(
    "/logout",
    response_model=dict[str, str],
    status_code=status.HTTP_200_OK,
    summary="Logout User",
    description="Blacklists the user's current JWT access token to terminate the session.",
)
@limiter.limit("20/minute")
async def logout(
    request: Request,
    token: str = Depends(oauth2_scheme),  # Requires Authorization: Bearer <token> header
) -> dict[str, str]:
    """
    Logs out a user by blacklisting their JWT access token.
    """
    return logout_user_token(token)


# ---------------------------------------------------
# Email Verification (Initial)
# ---------------------------------------------------
@router.get(
    "/verify-email",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify Email (Initial Registration)",
    description="Verifies a user's email using a token sent during registration.",
)
async def verify_initial_email(
    token: str,  # Token comes as a query parameter, e.g., /auth/verify-email?token=...
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """
    Verifies a user's email address using the initial verification token.
    """
    return await verify_email_token(token, db)


# ---------------------------------------------------
# Request New Verification Email
# ---------------------------------------------------
@router.post(
    "/request-verification-email/{email}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Request New Verification Email",
    description="Requests a new verification email via path parameter if the account is not verified.",
)
@limiter.limit("3/hour")
async def post_request_verification_email(
    request: Request,
    email: EmailStr,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """
    Handles the request to resend a verification email using email from the path.
    """
    return await request_new_verification_email(email, db)


# ---------------------------------------------------
# Forgot Password Flow
# ---------------------------------------------------
@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Request Password Reset",
    description="Sends a password reset link to the user's email if the account exists and is verified.",
)
@limiter.limit("5/minute")
async def post_forgot_password(
    request: Request,
    payload: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """
    Handles the request to initiate a password reset.
    """
    return await request_password_reset(payload, db)


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Reset Password",
    description="Resets the user's password using a valid token received via email.",
)
@limiter.limit("5/minute")
async def post_reset_password(
    request: Request,
    payload: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """
    Handles the password reset using the provided token and new password.
    """
    return await reset_password(payload, db)


# ---------------------------------------------------
# Secure Email Update Flow
# ---------------------------------------------------
@router.post(
    "/update-email",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Request Email Update (Authenticated)",
    description="Sends a verification link to the *new* email address. Requires user to be authenticated.",
)
@limiter.limit("5/hour")
async def post_update_email(
    request: Request,
    payload: UpdateEmailRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageResponse:
    """
    Handles the request to change the authenticated user's email address.
    Sends verification to the new email.
    """
    return await request_email_update(payload, current_user, db)


@router.get(
    "/verify-new-email",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify New Email Address",
    description="Verifies a new email address using a token sent to it, completing the email update process.",
)
async def get_verify_new_email(
    token: str,  # Token comes as a query parameter, e.g., /auth/verify-new-email?token=...
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """
    Handles the verification of the new email address using the provided token.
    """
    return await verify_new_email(token, db)
