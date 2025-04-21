"""
auth/routes.py

Handles authentication routes including:
- User registration and login via JSON or OAuth2
- Google OAuth2 login flow
- JWT token issuance and user logout handling
- Email verification
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.schemas import (
    LoginRequest,
    SignupRequest,
    AuthSuccessResponse,
    MessageResponse,
)
from app.auth.services import (
    signup_user,
    login_user_json,
    login_user_oauth,
    handle_google_login,
    handle_google_callback,
    logout_user_token,
    verify_email_token,
)
from app.core.dependencies import get_db, oauth2_scheme
from app.core.limiter import limiter

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = logging.getLogger(__name__)


# ------------------------------
# Registration
# ------------------------------
@router.post(
    "/signup",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register New User",
    description="Registers a new user and returns a success message. Email verification is required."
)
@limiter.limit("5/minute")
async def signup(
    request: Request,
    payload: SignupRequest,
    db: AsyncSession = Depends(get_db),
):
    return await signup_user(payload, db)


# ------------------------------
# Login (JSON)
# ------------------------------
@router.post(
    "/login/json",
    response_model=AuthSuccessResponse,
    status_code=status.HTTP_200_OK,
    summary="Login with JSON",
    description="Authenticates user using email and password via JSON request body."
)
@limiter.limit("10/minute")
async def login_json(
    request: Request,
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    return await login_user_json(payload, db)


# ------------------------------
# Login (OAuth2 form)
# ------------------------------
@router.post(
    "/login/oauth",
    response_model=AuthSuccessResponse,
    status_code=status.HTTP_200_OK,
    summary="Login with OAuth2 Form",
    description="Authenticates user using OAuth2-compatible form data (username = email)."
)
@limiter.limit("10/minute")
async def login_oauth(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    return await login_user_oauth(form_data, db)


# ------------------------------
# Google OAuth2 Login
# ------------------------------
@router.get(
    "/google/login",
    status_code=status.HTTP_200_OK,
    summary="Start Google OAuth2 Flow",
    description="Redirects the user to Google's OAuth2 consent screen."
)
@limiter.limit("10/minute")
async def google_login(request: Request):
    return await handle_google_login(request)


@router.get(
    "/google/callback",
    status_code=status.HTTP_200_OK,
    summary="Handle Google OAuth2 Callback",
    description="Handles the callback from Google after OAuth2 login."
)
@limiter.limit("10/minute")
async def google_callback(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    return await handle_google_callback(request, db)


# ------------------------------
# Logout
# ------------------------------
@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    response_model=dict,
    summary="Logout User",
    description="Blacklists the user's JWT access token to terminate session."
)
@limiter.limit("20/minute")
async def logout_user(
    request: Request,
    token: str = Depends(oauth2_scheme),
):
    try:
        return logout_user_token(token)
    except JWTError:
        logger.warning("[LOGOUT] Invalid token on logout request.")
        raise HTTPException(status_code=400, detail="Invalid token")


# ------------------------------
# Email Verification
# ------------------------------
@router.get(
    "/verify-email",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify Email",
    description="Verifies a user's email using a token sent via email."
)
async def verify_email(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    message = await verify_email_token(token, db)
    return {"detail": message}
