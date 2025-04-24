"""
auth/routes.py

Handles authentication routes including:
- User registration and login via JSON or OAuth2
- Google OAuth2 login flow
- JWT token issuance and user logout handling
- Email verification
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.schemas import (
    AuthSuccessResponse,
    LoginRequest,
    MessageResponse,
    SignupRequest,
)
from app.auth.services import (
    handle_google_callback,
    handle_google_login,
    login_user_json,
    login_user_oauth,
    logout_user_token,
    signup_user,
    verify_email_token,
)
from app.core.dependencies import get_db, oauth2_scheme
from app.core.limiter import limiter

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
    description="Registers a new user and returns a success message. Email verification is required.",
)
@limiter.limit("5/minute")
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
    description="Authenticates user using email and password via JSON request body.",
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
    description="Authenticates user using OAuth2-compatible form data (username = email).",
)
@limiter.limit("10/minute")
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
    status_code=status.HTTP_200_OK,
    summary="Start Google OAuth2 Flow",
    description="Redirects the user to Google's OAuth2 consent screen.",
)
@limiter.limit("10/minute")
async def google_login(request: Request) -> Any:
    """
    Initiates the Google OAuth2 login flow by redirecting to Google.
    """
    return await handle_google_login(request)


@router.get(
    "/google/callback",
    status_code=status.HTTP_200_OK,
    summary="Handle Google OAuth2 Callback",
    description="Handles the callback from Google after OAuth2 login.",
)
@limiter.limit("10/minute")
async def google_callback(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Any:
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
    description="Blacklists the user's JWT access token to terminate session.",
)
@limiter.limit("20/minute")
async def logout_user(
    request: Request,
    token: str = Depends(oauth2_scheme),
) -> dict[str, str]:
    """
    Logs out a user by blacklisting their JWT access token.
    """
    try:
        return logout_user_token(token)
    except JWTError:
        logger.warning("[LOGOUT] Invalid token on logout request.")
        raise HTTPException(status_code=400, detail="Invalid token")


# ---------------------------------------------------
# Email Verification
# ---------------------------------------------------
@router.get(
    "/verify-email",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify Email",
    description="Verifies a user's email using a token sent via email.",
)
async def verify_email(
    token: str,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """
    Verifies a user's email address using a verification token.
    """
    return await verify_email_token(token, db)
