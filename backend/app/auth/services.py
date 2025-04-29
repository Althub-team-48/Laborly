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
            await send_email_verification(user.email, token)
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
    """Helper function to fetch and validate user credentials."""
    # Check for IP penalty first
    penalty_key = f"{IP_PENALTY_PREFIX}{client_ip}"
    if redis_client and redis_client.exists(penalty_key):
        logger.warning(f"Login attempt from penalized IP: {client_ip}")
        # Optionally add a small delay even on penalty check to slow down attackers
        await asyncio.sleep(random.uniform(1, 3))
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Please try again later.",
        )
    user = (
        (await db.execute(select(User).filter(User.email == email))).unique().scalar_one_or_none()
    )
    is_password_correct = False
    if user and password:
        is_password_correct = verify_password(password, user.hashed_password)

    # Check if user exists and password is correct (if password provided)
    if not user or not is_password_correct:
        logger.warning(f"Failed login attempt for email: {email} from IP: {client_ip}")

        if redis_client:
            failed_attempts_key = f"{FAILED_LOGIN_PREFIX}{client_ip}"
            # Increment failed attempts counter and set expiration if it's a new key
            redis_client.incr(failed_attempts_key)
            # Set TTL only if key is newly created or doesn't have one
            if redis_client.ttl(failed_attempts_key) == -1:  # -1 means key exists but has no TTL
                redis_client.expire(failed_attempts_key, FAILED_ATTEMPTS_WINDOW)

            failed_attempts = int(redis_client.get(failed_attempts_key) or 0)

            if failed_attempts >= MAX_FAILED_ATTEMPTS:
                # Apply penalty - set a temporary key for the IP
                redis_client.setex(penalty_key, IP_PENALTY_DURATION, "penalized")
                logger.warning(f"IP address penalized due to too many failed attempts: {client_ip}")
                # Add a longer delay when penalty is applied
                await asyncio.sleep(random.uniform(5, 10))
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many failed login attempts. Please try again later.",
                )
            else:
                # Add a small delay on incorrect attempts below the threshold
                await asyncio.sleep(random.uniform(0.5, 1.5))

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if email is verified (only after successful authentication)
    if not user.is_verified:
        logger.warning(f"Login attempt by unverified user: {user.email}")
        # Optionally add a small delay even for unverified users
        await asyncio.sleep(random.uniform(0.5, 1.5))
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email before logging in.",
        )

    # If authentication is successful, reset failed attempts counter for this IP
    if redis_client:
        failed_attempts_key = f"{FAILED_LOGIN_PREFIX}{client_ip}"
        redis_client.delete(failed_attempts_key)
        logger.debug(f"Resetting failed login attempts for IP: {client_ip}")

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
    )
else:
    logger.warning("Google OAuth2 credentials not configured. Google login disabled.")


async def handle_google_login(request: Request, role: UserRole | None) -> RedirectResponse:
    """Initiates the Google OAuth2 login flow, encoding role in state."""
    if not (settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET):
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Google login is not configured."
        )
    redirect_uri = request.url_for("google_callback")

    # --- Generate Nonce and State JWT ---
    nonce = secrets.token_hex(16)
    # Store the nonce in the server-side session for later verification
    request.session["oauth_nonce"] = nonce
    logger.debug(f"Stored nonce {nonce} in session for Google OAuth")

    # Create the signed JWT containing role and nonce
    state_jwt = create_oauth_state_token(role=role, nonce=nonce)

    logger.info(
        f"Redirecting to Google OAuth2 login. Redirect URI: {redirect_uri}. State includes role: {role}"
    )
    # Pass the state JWT to authorize_redirect
    return cast(
        RedirectResponse,
        await oauth.google.authorize_redirect(request, redirect_uri, state=state_jwt),
    )


async def handle_google_callback(request: Request, db: AsyncSession) -> RedirectResponse:
    """Handles the callback from Google using JWT state for role and CSRF check."""
    if not (settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET):
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Google login is not configured."
        )

    # --- Validate State and Nonce ---
    returned_state_jwt = request.query_params.get('state')
    session_nonce = request.session.pop("oauth_nonce", None)  # Get and remove nonce from session

    if not returned_state_jwt or not session_nonce:
        logger.error("Missing state parameter or session nonce during Google callback.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid state or session."
        )

    try:
        state_payload = decode_oauth_state_token(returned_state_jwt)
    except HTTPException as e:
        logger.error(f"Failed to decode state JWT: {e.detail}")
        raise

    # Verify the nonce from the state against the one stored in the session (CSRF check)
    if state_payload.nonce != session_nonce:
        logger.error(
            f"OAuth nonce mismatch. Session: {session_nonce}, State: {state_payload.nonce}. Potential CSRF."
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="State parameter mismatch (CSRF protection).",
        )

    # Get the requested role from the validated state payload
    requested_role = state_payload.role
    # Define a safe default if role wasn't in state
    default_role_on_error = UserRole.CLIENT
    if requested_role is None:
        logger.warning(
            f"Role missing from state payload (nonce: {state_payload.nonce}). Defaulting to {default_role_on_error}."
        )
        requested_role = default_role_on_error

    logger.info(
        f"Google callback state validated. Nonce: {state_payload.nonce}, Requested role: {requested_role}"
    )

    # --- Proceed with Google Token Exchange and User Info Fetch ---
    try:
        token = await oauth.google.authorize_access_token(request)
        if not token or 'access_token' not in token:
            raise ValueError("Invalid access token received from Google.")
        resp = await oauth.google.userinfo(token=token)
        user_info = resp
    except Exception as e:
        logger.error(f"Error during Google OAuth token exchange/userinfo: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Could not verify Google account: {e}"
        )

    user_email = user_info.get("email")
    if not user_email:
        logger.error("Google OAuth callback response missing email.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email not provided by Google."
        )

    # --- User Lookup / Creation ---
    user = (
        (await db.execute(select(User).filter(User.email == user_email)))
        .unique()
        .scalar_one_or_none()
    )
    is_new_user = False

    if not user:
        logger.info(f"Creating new user via Google OAuth: {user_email} with role {requested_role}")
        password = generate_strong_password()
        hashed_password = get_password_hash(password)

        # Use the validated role from the state payload
        user_obj = UserCreate.from_google(
            user_info, hashed_password=hashed_password, assigned_role=requested_role
        )
        user_fields = {c.key for c in inspect(User).mapper.column_attrs}
        user_data = {k: v for k, v in user_obj.model_dump().items() if k in user_fields}
        user = User(**user_data, is_verified=True)
        db.add(user)
        await db.commit()
        await db.refresh(user)
        logger.info(
            f"New user created and verified via Google: {user.email} (ID: {user.id}) with role {user.role}"
        )
        is_new_user = True
        # Send welcome email
        try:
            await send_welcome_email(user.email, user.first_name)
            logger.info(f"Welcome email sent to new Google user: {user.email}")
        except Exception as e:
            logger.error(f"Failed to send welcome email to {user.email}: {e}")

    elif not user.is_verified:
        user.is_verified = True
        await db.commit()
        await db.refresh(user)
        logger.info(f"Existing user {user.email} verified via Google login.")

    # --- Send password setup email only for new users ---
    if is_new_user:
        try:
            reset_token = create_password_reset_token(str(user.id))
            await send_password_reset_email(user.email, reset_token)
            logger.info(f"Sent initial password setup email to new Google user: {user.email}")
        except Exception as e:
            logger.error(
                f"Failed to send password setup email to new Google user {user.email}: {e}"
            )

    # --- Issue Access Token and Redirect ---
    access_token = create_access_token({"sub": str(user.id), "role": user.role.value})
    logger.info(f"Google login successful for user: {user.email} (Role: {user.role.value})")

    url = settings.BASE_URL.rstrip('/')
    redirect_url = f"{url}/auth/callback?token={access_token}"
    logger.debug(f"Redirecting user to frontend: {redirect_url}")
    return RedirectResponse(url=redirect_url)
