"""
auth/routes.py

Handles authentication routes including:
- User registration and login via JSON or OAuth2
- Google OAuth2 login flow (backend exchange)
- JWT token issuance and user logout handling
- Email verification, password reset, and secure email update
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status, Query, Response
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.schemas import (
    ForgotPasswordRequest,
    LoginRequest,
    LoginResponse,
    MessageResponse,
    ResetPasswordRequest,
    SignupRequest,
    UpdateEmailRequest,
)

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
from app.database.enums import UserRole
from app.database.session import get_db
from app.core.limiter import limiter
from app.core.config import settings
from app.database.models import User
from .schemas import AuthUserResponse

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
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Login with JSON (Cookie Auth)",
    description="Authenticates user via JSON. Returns user info in body; sets session token in HttpOnly cookie.",
)
@limiter.limit("10/minute")
async def login_json(
    request: Request,
    payload: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    """
    Authenticates a user using JSON payload (email and password).
    Sets the access token in an HttpOnly cookie for session management.
    """
    client_ip = request.client.host if request.client else "unknown"
    login_result = await login_user_json(payload, db, client_ip)

    access_token_value: str = login_result.access_token

    response.set_cookie(
        key="access_token",
        value=access_token_value,
        httponly=True,
        samesite="lax",
        secure=not settings.DEBUG,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
        domain=None,
    )
    return LoginResponse(user=AuthUserResponse.model_validate(login_result.user))


# ---------------------------------------------------
# Login (OAuth2 Form)
# ---------------------------------------------------
@router.post(
    "/login/oauth",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Login with OAuth2 Form (Cookie Auth)",
    description="Authenticates user via form data. Returns user info in body; sets session token in HttpOnly cookie.",
)
@limiter.limit("10/minute")
async def login_oauth(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    """
    Authenticates a user using OAuth2 form data (username and password).
    Sets the access token in an HttpOnly cookie for session management."""
    client_ip = request.client.host if request.client else "unknown"
    login_result = await login_user_oauth(form_data, db, client_ip)

    access_token_value: str = login_result.access_token

    response.set_cookie(
        key="access_token",
        value=access_token_value,
        httponly=True,
        samesite="lax",
        secure=not settings.DEBUG,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
        domain=None,
    )
    return LoginResponse(user=AuthUserResponse.model_validate(login_result.user))


# ---------------------------------------------------
# Google OAuth2 Login Flow
# ---------------------------------------------------
@router.get(
    "/google/login",
    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    summary="Start Google OAuth2 Flow",
    description="Redirects the user to Google's OAuth2 consent screen.",
    response_description="Redirects to Google authentication page.",
    response_class=RedirectResponse,
)
@limiter.limit("10/minute")
async def google_login(
    request: Request,
    role: UserRole | None = Query(
        None, description="The role the user intends to sign up as (CLIENT or WORKER)"
    ),
) -> RedirectResponse:
    """
    Initiates the Google OAuth2 login flow by redirecting to Google.
    Includes the intended role in the state parameter if provided.
    """
    return await handle_google_login(request, role)


# Modified google_callback route
@router.get(
    "/google/callback",
    response_class=RedirectResponse,
    summary="Handle Google OAuth2 Callback & Token Exchange",
    description="Handles callback from Google, validates state, exchanges code, logs in/signs up user, sets auth cookie, and redirects to frontend.",
    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
)
@limiter.limit("10/minute")
async def google_callback(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """
    Handles the Google OAuth2 callback, performs code exchange,
    authenticates/registers the user, sets HttpOnly cookie and redirects to the frontend.
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
    token: str = Depends(oauth2_scheme),
) -> dict[str, str]:
    """
    Logs out a user by blacklisting their JWT access token (from header or cookie).
    Note: Dependency get_current_user implicitly handles token extraction now.
          We might not need the explicit token dependency here if relying solely on cookie/header check in get_current_user.
          However, keeping it explicit might be clearer for the intent.
          Let's remove the explicit token dependency for logout and rely on get_current_user's logic,
          assuming logout requires an authenticated user session.
    """
    auth_header = request.headers.get("Authorization")
    token_from_cookie = request.cookies.get("access_token")
    token_to_blacklist = None
    if auth_header and auth_header.startswith("Bearer "):
        token_to_blacklist = auth_header.replace("Bearer ", "")
    elif token_from_cookie:
        token_to_blacklist = token_from_cookie

    if not token_to_blacklist:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    return await logout_user_token(token_to_blacklist)


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
    token: str,
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
    token: str,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """
    Handles the verification of the new email address using the provided token.
    """
    return await verify_new_email(token, db)
