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
import asyncio
import secrets
from datetime import datetime, timezone
from typing import Any, cast

from fastapi import HTTPException, Request, status
from fastapi.responses import RedirectResponse
from jose import jwt, JWTError
from passlib.context import CryptContext
from pydantic import EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import load_only
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config as StarletteConfig

from app.auth.schemas import (
    AuthUserResponse,
    AuthSuccessResponse,
    ForgotPasswordRequest,
    GoogleCodeExchangeRequest,
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
    send_final_change_notification_to_old_email,
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
    create_oauth_state_token,
    decode_oauth_state_token,
)
from app.database.enums import UserRole
from app.database.models import User
from app.core.blacklist import blacklist_token, redis_client


logger = logging.getLogger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ------------------------------------------------
# Brute-Force Protection Settings (Redis Keys and Thresholds)
# ------------------------------------------------
# Key prefix for failed login attempts per IP
FAILED_LOGIN_PREFIX = "failed_logins:ip:"
# Key prefix for temporary IP blacklisting/penalty
IP_PENALTY_PREFIX = "ip_penalty:"

MAX_FAILED_ATTEMPTS = settings.MAX_FAILED_ATTEMPTS
IP_PENALTY_DURATION = settings.IP_PENALTY_DURATION
FAILED_ATTEMPTS_WINDOW = settings.FAILED_ATTEMPTS_WINDOW


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
        # Send the personalized verification email
        await send_email_verification(new_user.email, token, first_name=new_user.first_name)
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

    stmt = (
        select(User)
        .filter(User.id == user_id)
        .options(load_only(User.id, User.email, User.is_verified, User.first_name))
    )
    result = await db.execute(stmt)
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
# Request New Verification Email
# ------------------------------------------------
async def request_new_verification_email(email: EmailStr, db: AsyncSession) -> MessageResponse:
    """Sends a new verification email if the user exists and is not verified."""
    user = (
        (await db.execute(select(User).filter(User.email == email))).unique().scalar_one_or_none()
    )

    # Important: Only send if user exists and is NOT verified
    if user and not user.is_verified:
        try:
            # Generate a fresh token
            token = create_email_verification_token(str(user.id))
            # Use the existing email sending function
            await send_email_verification(user.email, token, first_name=user.first_name)
            logger.info(f"New verification email sent to: {user.email}")
        except Exception as e:
            logger.error(f"Failed to send new verification email to {user.email}: {e}")

    return MessageResponse(
        detail="If an account with that email exists and requires verification, a new verification link has been sent."
    )


# ------------------------------------------------
# Login (JSON and OAuth2)
# ------------------------------------------------
async def _authenticate_user(
    email: str, password: str | None, db: AsyncSession, client_ip: str
) -> User:
    """Helper function to fetch and validate user credentials (Async Redis)."""
    # Check for IP penalty first
    penalty_key = f"{IP_PENALTY_PREFIX}{client_ip}"
    if redis_client:  # Check if client exists
        try:
            # Use await with async client method
            is_penalized = await redis_client.exists(penalty_key)
            if is_penalized:
                logger.warning(f"Login attempt from penalized IP: {client_ip}")
                await asyncio.sleep(random.uniform(1, 3))
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many failed login attempts. Please try again later.",
                )
        except Exception as e:
            logger.error(f"[REDIS ASYNC ERROR] Failed checking IP penalty for {client_ip}: {e}")
            # Decide how to handle - fail open or closed? Fail closed for security.
            raise HTTPException(status_code=500, detail="Error checking login status.")

    user = (
        (await db.execute(select(User).filter(User.email == email))).unique().scalar_one_or_none()
    )
    is_password_correct = False
    if user and password:
        is_password_correct = verify_password(password, user.hashed_password)

    if not user or not is_password_correct:
        logger.warning(f"Failed login attempt for email: {email} from IP: {client_ip}")

        if redis_client:
            try:
                failed_attempts_key = f"{FAILED_LOGIN_PREFIX}{client_ip}"
                # Increment failed attempts counter (async)
                await redis_client.incr(failed_attempts_key)
                # Set TTL only if key is newly created or doesn't have one (async)
                ttl_status = await redis_client.ttl(failed_attempts_key)
                if ttl_status == -1:  # -1 means key exists but has no TTL
                    await redis_client.expire(failed_attempts_key, FAILED_ATTEMPTS_WINDOW)

                # Get failed attempts count (async)
                failed_attempts_str = await redis_client.get(failed_attempts_key)
                failed_attempts = int(failed_attempts_str or 0)

                if failed_attempts >= MAX_FAILED_ATTEMPTS:
                    # Apply penalty - set a temporary key for the IP (async)
                    await redis_client.setex(penalty_key, IP_PENALTY_DURATION, "penalized")
                    logger.warning(
                        f"IP address penalized due to too many failed attempts: {client_ip}"
                    )
                    await asyncio.sleep(random.uniform(5, 10))
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="Too many failed login attempts. Please try again later.",
                    )
                else:
                    await asyncio.sleep(random.uniform(0.5, 1.5))
            except Exception as e:
                logger.error(
                    f"[REDIS ASYNC ERROR] Failed processing failed login for {client_ip}: {e}"
                )
                # Fail closed
                raise HTTPException(status_code=500, detail="Error processing login attempt.")

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_verified:
        logger.warning(f"Login attempt by unverified user: {user.email}")
        await asyncio.sleep(random.uniform(0.5, 1.5))
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email before logging in.",
        )

    if redis_client:
        try:
            failed_attempts_key = f"{FAILED_LOGIN_PREFIX}{client_ip}"
            # Delete failed attempts counter (async)
            await redis_client.delete(failed_attempts_key)
            logger.debug(f"Resetting failed login attempts for IP: {client_ip}")
        except Exception as e:
            logger.error(
                f"[REDIS ASYNC ERROR] Failed resetting failed attempts for {client_ip}: {e}"
            )
            # Log error but allow login to proceed

    return user


async def login_user_json(
    payload: LoginRequest, db: AsyncSession, client_ip: str
) -> AuthSuccessResponse:  # Add client_ip parameter
    """Authenticates a user via JSON email/password."""
    user = await _authenticate_user(
        payload.email, payload.password, db, client_ip
    )  # Pass client_ip
    access_token = create_access_token({"sub": str(user.id), "role": user.role.value})
    logger.info(f"User logged in successfully: {user.email} from IP: {client_ip}")
    return AuthSuccessResponse(
        access_token=access_token, user=AuthUserResponse.model_validate(user)
    )


async def login_user_oauth(
    form_data: Any, db: AsyncSession, client_ip: str
) -> AuthSuccessResponse:  # Add client_ip parameter
    """Authenticates a user via OAuth2 form data (username=email)."""
    # OAuth2PasswordRequestForm uses 'username' field for the identifier
    user = await _authenticate_user(
        form_data.username, form_data.password, db, client_ip
    )  # Pass client_ip
    access_token = create_access_token({"sub": str(user.id), "role": user.role.value})
    logger.info(f"User logged in successfully (OAuth form): {user.email} from IP: {client_ip}")
    return AuthSuccessResponse(
        access_token=access_token, user=AuthUserResponse.model_validate(user)
    )


# ------------------------------------------------
# Logout
# ------------------------------------------------
async def logout_user_token(token: str) -> dict[str, str]:
    """Blacklists the provided JWT access token (Async)."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={
                "verify_signature": False,
                "verify_aud": False,
            },
        )
        jti = payload.get("jti")
        exp = payload.get("exp")

        if jti and exp:
            now = datetime.now(timezone.utc).timestamp()
            ttl = max(0, int(exp - now))
            if ttl > 0:
                # Call the async blacklist function
                await blacklist_token(jti, ttl)
                logger.info(f"Access token blacklisted (JTI: {jti}) for {ttl} seconds.")
            else:
                logger.info(f"Access token already expired (JTI: {jti}). No blacklist needed.")
        else:
            logger.warning("Attempted logout with token missing 'jti' or 'exp'.")

    except JWTError as e:
        logger.warning(f"Error decoding token during logout: {e}")

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
            await send_password_reset_email(user.email, token, first_name=user.first_name)
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
        await send_password_reset_confirmation(user.email, first_name=user.first_name)
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
        await send_new_email_verification(
            new_email, token, first_name=current_user.first_name
        )  # Send to NEW email
        logger.info(f"New email verification sent to {new_email} for user {current_user.id}")

        # Optional: Notify the user at their OLD email address
        try:
            await send_email_change_notification(
                old_email, new_email, first_name=current_user.first_name
            )
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
        token_payload: VerificationTokenPayload = decode_verification_token(
            token=token, expected_type="new_email_verification"
        )
        user_id = token_payload.sub
        new_email = token_payload.new_email

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
    user.is_verified = True
    await db.commit()
    logger.info(f"User {user.id} successfully updated email from {old_email} to {new_email}")

    try:
        await send_new_email_confirmed(new_email, first_name=user.first_name)
        logger.info(f"Confirmation email sent to: {new_email}")
    except Exception as e:
        logger.error(f"Failed to send Confirmation email to {new_email}: {e}")

    try:
        await send_final_change_notification_to_old_email(
            old_email=old_email, new_email=new_email, first_name=user.first_name
        )
    except Exception as e:
        logger.error(f"Failed to send final change notification to old email {old_email}: {e}")

    return MessageResponse(detail="Your email address has been successfully updated.")


# ------------------------------------------------
# Google OAuth2 Setup
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
    )
else:
    logger.warning("Google OAuth2 credentials not configured. Google login disabled.")


def is_google_oauth_configured() -> bool:
    return bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)


async def handle_google_login(request: Request, role: UserRole | None) -> RedirectResponse:
    """Initiates the Google OAuth2 login flow, encoding role in state."""
    if not is_google_oauth_configured():
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Google login is not configured."
        )

    # This MUST match the URI registered in Google Cloud Console and used in the callback route
    redirect_uri = str(request.url_for("google_callback"))
    nonce = secrets.token_hex(16)
    request.session["oauth_nonce"] = nonce

    logger.debug(f"Stored nonce {nonce} in session for Google OAuth")

    state_jwt = create_oauth_state_token(role=role, nonce=nonce)
    logger.info(f"Redirecting to Google OAuth2. State includes role: {role}")

    return cast(
        RedirectResponse,
        await oauth.google.authorize_redirect(request, redirect_uri, state=state_jwt),
    )


async def handle_google_callback(request: Request, db: AsyncSession) -> RedirectResponse:
    """
    Handles the callback from Google.
    Validates state, extracts authorization code, and redirects to frontend with the code and state.
    """
    if not is_google_oauth_configured():
        logger.error("Google OAuth callback attempted but not configured.")
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Google login is not configured."
        )

    returned_state_jwt = request.query_params.get("state")
    session_nonce = request.session.pop("oauth_nonce", None)

    if not returned_state_jwt or not session_nonce:
        logger.error("Missing state or nonce during Google callback.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Missing state or nonce."
        )

    try:
        state_payload = decode_oauth_state_token(returned_state_jwt)
        if state_payload.nonce != session_nonce:
            logger.error("OAuth nonce mismatch. Potential CSRF.")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid nonce.")
        logger.info("Google callback state validated.")
    except HTTPException as e:
        logger.error(f"Failed to decode state JWT: {e.detail}")
        raise e
    except Exception as e:
        logger.error(f"Unexpected error validating state: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal server error: {e}"
        )

    code = request.query_params.get("code")
    if not code:
        logger.error("Authorization code missing in Google callback.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Missing authorization code."
        )

    # --- Redirect to Frontend with Code and State ---
    # !! IMPORTANT: Replace '/auth/google/handle' with actual frontend route that is designed to receive this code and state, and call the exchange endpoint.
    frontend_redirect = (
        f"{settings.BASE_URL.rstrip('/')}/auth/google/handle?code={code}&state={returned_state_jwt}"
    )
    logger.debug(f"Redirecting to frontend: {frontend_redirect}")
    return RedirectResponse(url=frontend_redirect)


async def exchange_google_code(
    payload: GoogleCodeExchangeRequest, db: AsyncSession, request: Request
) -> AuthSuccessResponse:
    """
    Exchanges the Google authorization code (received from frontend) for tokens,
    fetches user info, finds/creates the user using role from state, and returns the application JWT.
    """
    if not is_google_oauth_configured():
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Google login is not configured."
        )

    requested_role = UserRole.CLIENT
    try:
        if payload.state:
            state_payload = decode_oauth_state_token(payload.state)
            requested_role = state_payload.role or UserRole.CLIENT
            logger.info(f"Using role from state: {requested_role}")
        else:
            logger.warning("State not provided. Using default role.")
    except HTTPException as e:
        logger.warning(f"Invalid state JWT: {e.detail}. Using default role.")
    except Exception as e:
        logger.error(f"Error decoding state JWT: {e}", exc_info=True)

    # --- Perform Code Exchange with Google ---
    try:
        redirect_uri = str(request.url_for("google_callback"))
        token = await oauth.google.fetch_token(
            code=payload.code, redirect_uri=redirect_uri, grant_type='authorization_code'
        )

        if not token or 'access_token' not in token:
            raise ValueError("Invalid access token received from Google.")

        resp = await oauth.google.get('userinfo', token=token)
        resp.raise_for_status()
        user_info = resp.json()
    except Exception as e:
        logger.error(f"OAuth exchange failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Could not verify Google account: {e}"
        )

    user_email = user_info.get("email")
    if not user_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email not provided by Google."
        )

    # --- User Lookup / Creation ---
    result = await db.execute(select(User).filter(User.email == user_email))
    user = result.unique().scalar_one_or_none()
    is_new_user = False

    if not user:
        logger.info(f"Creating new user: {user_email} with role {requested_role}")
        password = generate_strong_password()
        hashed_password = get_password_hash(password)
        user_obj = UserCreate.from_google(
            user_info, hashed_password=hashed_password, assigned_role=requested_role
        )

        user_data = {
            k: v
            for k, v in user_obj.model_dump().items()
            if k in {c.key for c in inspect(User).mapper.column_attrs}
        }
        user = User(**user_data, is_verified=True)

        db.add(user)
        await db.commit()
        await db.refresh(user)
        is_new_user = True

        try:
            await send_welcome_email(user.email, user.first_name)
        except Exception as e:
            logger.error(f"Failed to send welcome email to {user.email}: {e}")

    elif not user.is_verified:
        user.is_verified = True
        await db.commit()
        await db.refresh(user)
        logger.info(f"Verified existing user: {user.email}")

    if is_new_user:
        try:
            reset_token = create_password_reset_token(str(user.id))
            await send_password_reset_email(user.email, reset_token, user.first_name)
        except Exception as e:
            logger.error(f"Failed to send password setup email to {user.email}: {e}")

    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    logger.info(f"User authenticated: {user.email}, Role: {user.role}")

    return AuthSuccessResponse(
        access_token=token, user=AuthUserResponse.model_validate(user, from_attributes=True)
    )
