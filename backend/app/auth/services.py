# ruff: noqa: E712
"""
auth/services.py

Handles authentication-related business logic:
- Password hashing and verification
- JWT token creation and logout
- Signup and login (JSON / OAuth2)
- Google OAuth2 login flow and callback
- Email verification, password reset, and secure email update
"""

import logging
import os
import random
import string
from datetime import datetime, timezone
from typing import Any, cast

from fastapi import HTTPException, Request, status
from fastapi.responses import RedirectResponse
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.inspection import inspect
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config as StarletteConfig

from app.auth.schemas import (
    AuthUserResponse,
    AuthSuccessResponse,
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    ResetPasswordRequest,
    SignupRequest,
    UpdateEmailRequest,
    UserCreate,
    VerificationTokenPayload,
)
from app.core.config import settings

from app.core.email import (
    send_email_verification,
    send_new_email_confirmed,
    send_password_reset_confirmation,
    send_welcome_email,
    send_password_reset_email,
    send_new_email_verification,
    send_email_change_notification,
)

from app.core.tokens import (
    create_access_token,
    create_email_verification_token,
    create_password_reset_token,
    create_new_email_verification_token,
    decode_verification_token,
)
from app.database.models import User
from app.core.blacklist import blacklist_token


logger = logging.getLogger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ------------------------------------------------
# Password Utilities
# ------------------------------------------------
def get_password_hash(password: str) -> str:
    """Hashes a plain text password."""
    return cast(str, pwd_context.hash(password))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain text password against a hash."""
    return cast(bool, pwd_context.verify(plain_password, hashed_password))


def generate_strong_password(length: int = 12) -> str:
    """Generates a cryptographically strong random password."""
    if length < 8:
        raise ValueError("Password length must be at least 8 characters")

    required = [
        random.choice(string.ascii_uppercase),
        random.choice(string.ascii_lowercase),
        random.choice(string.digits),
        random.choice(string.punctuation),
    ]
    all_chars = string.ascii_letters + string.digits + string.punctuation
    remaining = random.choices(all_chars, k=length - len(required))

    password_list = required + remaining
    random.shuffle(password_list)
    return ''.join(password_list)


# ------------------------------------------------
# Signup with Email Verification
# ------------------------------------------------
async def signup_user(payload: SignupRequest, db: AsyncSession) -> MessageResponse:
    """Registers a new user and sends a verification email."""
    # Check if email exists
    email_exists = (
        (await db.execute(select(User).filter(User.email == payload.email)))
        .unique()
        .scalar_one_or_none()
    )
    if email_exists:
        logger.warning(f"Signup attempt with existing email: {payload.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    # Check if phone number exists
    phone_exists = (
        (await db.execute(select(User).filter(User.phone_number == payload.phone_number)))
        .unique()
        .scalar_one_or_none()
    )
    if phone_exists:
        logger.warning(f"Signup attempt with existing phone number: {payload.phone_number}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Phone number already in use"
        )

    # Create new user instance
    new_user = User(
        email=payload.email,
        phone_number=payload.phone_number,
        hashed_password=get_password_hash(payload.password),
        role=payload.role,
        first_name=payload.first_name,
        last_name=payload.last_name,
        is_verified=False,  # Start as unverified
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    logger.info(f"New user registered: {new_user.email} (ID: {new_user.id})")

    # Send verification email
    try:
        token = create_email_verification_token(str(new_user.id))
        await send_email_verification(new_user.email, token)
        logger.info(f"Verification email sent to: {new_user.email}")
    except Exception as e:
        # Log error but don't fail the registration
        logger.error(f"Failed to send verification email to {new_user.email}: {e}")
        # Consider adding user to a retry queue or notifying admin

    return MessageResponse(
        detail="Registration successful. Please check your email to verify your account."
    )


# ------------------------------------------------
# Email Verification (Initial)
# ------------------------------------------------
async def verify_email_token(token: str, db: AsyncSession) -> MessageResponse:
    """Verifies a user's email using the initial verification token."""
    try:
        # Use a generic decode function that validates type
        payload: VerificationTokenPayload = decode_verification_token(
            token, expected_type="email_verification"
        )
        user_id = payload.sub
    except HTTPException as e:
        logger.warning(f"Email verification failed: {e.detail}")
        raise e

    # Fetch user
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.unique().scalar_one_or_none()

    if not user:
        logger.warning(f"Email verification attempt for non-existent user ID: {user_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user.is_verified:
        logger.info(f"Email already verified for user: {user.email}")
        return MessageResponse(detail="Your email has already been verified.")

    # Mark as verified
    user.is_verified = True
    await db.commit()
    logger.info(f"Email successfully verified for user: {user.email}")

    # Send welcome email
    try:
        await send_welcome_email(user.email, user.first_name)
        logger.info(f"Welcome email sent to: {user.email}")
    except Exception as e:
        logger.error(f"Failed to send welcome email to {user.email}: {e}")

    return MessageResponse(detail="Your email has been successfully verified. You may now log in.")


# ------------------------------------------------
# Login (JSON and OAuth2)
# ------------------------------------------------
async def _authenticate_user(email: str, password: str | None, db: AsyncSession) -> User:
    """Helper function to fetch and validate user credentials."""
    user = (
        (await db.execute(select(User).filter(User.email == email))).unique().scalar_one_or_none()
    )

    # Check if user exists and password is correct (if password provided)
    if not user or (password and not verify_password(password, user.hashed_password)):
        logger.warning(f"Failed login attempt for email: {email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if email is verified
    if not user.is_verified:
        logger.warning(f"Login attempt by unverified user: {email}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email before logging in.",
        )

    return user


async def login_user_json(payload: LoginRequest, db: AsyncSession) -> AuthSuccessResponse:
    """Authenticates a user via JSON email/password."""
    user = await _authenticate_user(payload.email, payload.password, db)
    access_token = create_access_token({"sub": str(user.id), "role": user.role.value})
    logger.info(f"User logged in successfully: {user.email}")
    return AuthSuccessResponse(
        access_token=access_token, user=AuthUserResponse.model_validate(user)
    )


async def login_user_oauth(form_data: Any, db: AsyncSession) -> AuthSuccessResponse:
    """Authenticates a user via OAuth2 form data (username=email)."""
    # OAuth2PasswordRequestForm uses 'username' field for the identifier
    user = await _authenticate_user(form_data.username, form_data.password, db)
    access_token = create_access_token({"sub": str(user.id), "role": user.role.value})
    logger.info(f"User logged in successfully (OAuth form): {user.email}")
    return AuthSuccessResponse(
        access_token=access_token, user=AuthUserResponse.model_validate(user)
    )


# ------------------------------------------------
# Logout
# ------------------------------------------------
def logout_user_token(token: str) -> dict[str, str]:
    """Blacklists the provided JWT access token."""
    try:
        # Decode just to get JTI and EXP, validation happens implicitly
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={
                "verify_signature": False,
                "verify_aud": False,
            },  # Don't need full validation here
        )
        jti = payload.get("jti")
        exp = payload.get("exp")

        if jti and exp:
            # Calculate remaining time to live for the blacklist entry
            now = datetime.now(timezone.utc).timestamp()
            ttl = max(0, int(exp - now))  # Ensure TTL is not negative
            if ttl > 0:
                blacklist_token(jti, ttl)
                logger.info(f"Access token blacklisted (JTI: {jti}) for {ttl} seconds.")
            else:
                logger.info(f"Access token already expired (JTI: {jti}). No blacklist needed.")
        else:
            logger.warning("Attempted logout with token missing 'jti' or 'exp'.")

    except JWTError as e:
        # Log the error but proceed with logout response
        logger.warning(f"Error decoding token during logout: {e}")
        # Still return success, as the token is effectively unusable if invalid

    return {"detail": "Logout successful"}


# ------------------------------------------------
# Forgot Password Flow
# ------------------------------------------------
async def request_password_reset(
    payload: ForgotPasswordRequest, db: AsyncSession
) -> MessageResponse:
    """Initiates the password reset process by sending an email."""
    user = (
        (await db.execute(select(User).filter(User.email == payload.email)))
        .unique()
        .scalar_one_or_none()
    )

    # Important: Only proceed if user exists AND is verified
    if user and user.is_verified:
        try:
            token = create_password_reset_token(str(user.id))
            await send_password_reset_email(user.email, token)
            logger.info(f"Password reset email sent to: {user.email}")
        except Exception as e:
            logger.error(f"Failed to send password reset email to {user.email}: {e}")

    # Always return a generic message to prevent email enumeration attacks
    return MessageResponse(
        detail="If an account with that email exists and is verified, a password reset link has been sent."
    )


async def reset_password(payload: ResetPasswordRequest, db: AsyncSession) -> MessageResponse:
    """Resets the user's password using a valid token."""
    try:
        token_payload: VerificationTokenPayload = decode_verification_token(
            token=payload.token, expected_type="password_reset"
        )
        user_id = token_payload.sub
    except HTTPException as e:
        logger.warning(f"Password reset failed: {e.detail}")
        raise e

    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.unique().scalar_one_or_none()

    if not user:
        logger.warning(f"Password reset attempt for non-existent user ID: {user_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Update the password
    user.hashed_password = get_password_hash(payload.new_password)
    await db.commit()
    logger.info(f"Password successfully reset for user: {user.email}")

    try:
        await send_password_reset_confirmation(user.email)
        logger.info(f"Password confirmation email sent to: {user.email}")
    except Exception as e:
        logger.error(f"Failed to send password confirmation email to {user.email}: {e}")

    return MessageResponse(detail="Your password has been successfully reset.")


# ------------------------------------------------
# Secure Email Update Flow
# ------------------------------------------------
async def request_email_update(
    payload: UpdateEmailRequest, current_user: User, db: AsyncSession
) -> MessageResponse:
    """Requests an email update by sending verification to the new address."""
    new_email = payload.new_email
    old_email = current_user.email

    if new_email == old_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New email address cannot be the same as the current one.",
        )

    # Check if the new email is already taken by another *verified* user
    existing_user = (
        (await db.execute(select(User).filter(User.email == new_email, User.is_verified == True)))
        .unique()
        .scalar_one_or_none()
    )
    if existing_user and existing_user.id != current_user.id:
        logger.warning(
            f"User {current_user.id} attempted to change email to existing verified email: {new_email}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This email address is already in use by another verified account.",
        )

    # Generate a verification token specifically for the new email
    try:
        token = create_new_email_verification_token(str(current_user.id), new_email)
        await send_new_email_verification(new_email, token)  # Send to NEW email
        logger.info(f"New email verification sent to {new_email} for user {current_user.id}")

        # Optional: Notify the user at their OLD email address
        try:
            await send_email_change_notification(old_email, new_email)
            logger.info(
                f"Email change notification sent to old email {old_email} for user {current_user.id}"
            )
        except Exception as e_notify:
            logger.error(f"Failed to send email change notification to {old_email}: {e_notify}")

    except Exception as e:
        logger.error(f"Failed to send new email verification to {new_email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not send verification email. Please try again later.",
        )

    return MessageResponse(
        detail=f"A verification link has been sent to {new_email}. Please check that inbox to confirm the change."
    )


async def verify_new_email(token: str, db: AsyncSession) -> MessageResponse:
    """Verifies a new email address using the token and updates the user."""
    try:
        # Decode token, ensuring it's the correct type and contains the new email
        token_payload: VerificationTokenPayload = decode_verification_token(
            token=token, expected_type="new_email_verification"
        )
        user_id = token_payload.sub
        new_email = token_payload.new_email  # Extract the new email from the token payload

        if not new_email:
            logger.error(
                f"New email verification token missing 'new_email' field. Token payload: {token_payload}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification token payload.",
            )

    except HTTPException as e:
        logger.warning(f"New email verification failed: {e.detail}")
        raise e

    # Fetch the user associated with the token
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.unique().scalar_one_or_none()

    if not user:
        logger.warning(f"New email verification attempt for non-existent user ID: {user_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    existing_verified_user = (
        (await db.execute(select(User).filter(User.email == new_email, User.is_verified == True)))
        .unique()
        .scalar_one_or_none()
    )
    if existing_verified_user and existing_verified_user.id != user.id:
        logger.warning(
            f"User {user.id} tried to verify email {new_email}, but it was claimed by user {existing_verified_user.id} in the meantime."
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This email address has recently been verified by another account. Please request the change again.",
        )

    # Update the user's email
    old_email = user.email
    user.email = new_email
    # Ensure user remains verified (or becomes verified if somehow they weren't)
    user.is_verified = True
    await db.commit()
    logger.info(f"User {user.id} successfully updated email from {old_email} to {new_email}")

    try:
        await send_new_email_confirmed(old_email)
        logger.info(f"Confirmation email sent to: {old_email}")
    except Exception as e:
        logger.error(f"Failed to send Confirmation email to {old_email}: {e}")

    return MessageResponse(detail="Your email address has been successfully updated.")


# ------------------------------------------------
# Google OAuth2
# ------------------------------------------------
starlette_config = StarletteConfig(environ=os.environ)
oauth = OAuth(starlette_config)

if settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET:
    oauth.register(
        name="google",
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        client_kwargs={"scope": "openid email profile"},
        api_base_url="https://www.googleapis.com/oauth2/v3/",  # Check if still correct
    )
else:
    logger.warning("Google OAuth2 credentials not configured. Google login disabled.")


async def handle_google_login(request: Request) -> RedirectResponse:
    """Initiates the Google OAuth2 login flow."""
    if not (settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET):
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Google login is not configured."
        )
    redirect_uri = request.url_for("google_callback")
    logger.info(f"Redirecting to Google OAuth2 login: {redirect_uri}")
    return cast(RedirectResponse, await oauth.google.authorize_redirect(request, redirect_uri))


async def handle_google_callback(request: Request, db: AsyncSession) -> RedirectResponse:
    """Handles the callback from Google after OAuth2 authentication."""
    if not (settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET):
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Google login is not configured."
        )
    try:
        token = await oauth.google.authorize_access_token(request)
        resp = await oauth.google.get("userinfo", token=token)
        resp.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        user_info = resp.json()
    except Exception as e:
        logger.error(f"Error during Google OAuth callback: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Could not verify Google account."
        )

    user_email = user_info.get("email")
    if not user_email:
        logger.error("Google OAuth callback response missing email.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email not provided by Google."
        )

    # Find existing user by email
    user = (
        (await db.execute(select(User).filter(User.email == user_email)))
        .unique()
        .scalar_one_or_none()
    )

    if not user:
        # If user doesn't exist, create a new one
        logger.info(f"Creating new user via Google OAuth: {user_email}")
        password = generate_strong_password()  # Generate a secure random password
        hashed_password = get_password_hash(password)
        user_obj = UserCreate.from_google(user_info, hashed_password=hashed_password)

        # Ensure only valid User model fields are passed
        user_fields = {c.key for c in inspect(User).mapper.column_attrs}
        user_data = {k: v for k, v in user_obj.model_dump().items() if k in user_fields}

        user = User(**user_data, is_verified=True)  # Google users are implicitly verified
        db.add(user)
        await db.commit()
        await db.refresh(user)
        logger.info(f"New user created and verified via Google: {user.email} (ID: {user.id})")

        try:
            await send_welcome_email(user.email, user.first_name)
            logger.info(f"Welcome email sent to: {user.email}")
        except Exception as e:
            logger.error(f"Failed to send welcome email to {user.email}: {e}")
    elif not user.is_verified:
        # If user exists but isn't verified, mark them as verified now
        logger.info(f"Existing user {user.email} verified via Google login.")
        user.is_verified = True
        await db.commit()
        await db.refresh(user)

    # User exists (or was just created) and is verified, issue access token
    access_token = create_access_token({"sub": str(user.id), "role": user.role.value})
    logger.info(f"Google login successful for user: {user.email}")

    # Redirect to frontend, passing token
    # Consider using state parameter for better security and redirect flexibility
    frontend_url = settings.FRONTEND_URL or "/"
    redirect_url = f"{frontend_url}?token={access_token}"
    return RedirectResponse(url=redirect_url)
