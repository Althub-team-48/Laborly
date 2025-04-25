"""
core/tokens.py

Token generation and decoding utilities:
- JWT access token with expiration and JTI
- Email verification, password reset, and new email verification tokens
- Generic verification token decoder
"""

import uuid
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, status
from jose import jwt, JWTError, ExpiredSignatureError
from pydantic import EmailStr

from app.core.config import settings

from app.auth.schemas import VerificationTokenPayload

logger = logging.getLogger(__name__)


# ------------------------------------------------------
# --- Access Token ---
# ------------------------------------------------------
def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """
    Create a JWT access token with expiration and unique JTI.

    Args:
        data (dict[str, Any]): Payload data to include in the token (must contain 'sub' and 'role').
        expires_delta (timedelta | None): Optional custom expiration time. Defaults to settings.

    Returns:
        str: Encoded JWT access token.
    """
    expire: datetime = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    jti: str = str(uuid.uuid4())  # Unique token identifier for blacklisting
    payload: dict[str, Any] = {**data, "exp": expire, "jti": jti}

    if "sub" not in data or "role" not in data:
        logger.error("Access token creation attempt missing 'sub' or 'role' in data.")
        raise ValueError("Access token payload must include 'sub' and 'role'.")

    logger.info(f"Issuing access token for sub={data.get('sub')} exp={expire} jti={jti}")
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return str(token)


# ------------------------------------------------------
# --- Verification/Reset Token Creation ---
# ------------------------------------------------------
def _create_verification_token(
    user_id: str,
    token_type: str,
    expires_in_minutes: int,
    additional_data: dict[str, Any] | None = None,
) -> str:
    """Internal helper to create various verification/reset tokens."""
    expire: datetime = datetime.now(timezone.utc) + timedelta(minutes=expires_in_minutes)
    payload: dict[str, Any] = {
        "sub": user_id,
        "type": token_type,
        "exp": expire,
    }
    if additional_data:
        payload.update(additional_data)

    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    logger.info(f"Issuing '{token_type}' token for sub={user_id} exp={expire}")
    return str(token)


def create_email_verification_token(user_id: str) -> str:
    """
    Create a short-lived token for initial email verification.

    Args:
        user_id (str): The user ID to include as the subject.

    Returns:
        str: Encoded JWT token for email verification.
    """
    # Keep short expiry for initial verification
    return _create_verification_token(
        user_id=user_id,
        token_type="email_verification",
        expires_in_minutes=settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES or 30,
    )


def create_password_reset_token(user_id: str) -> str:
    """
    Create a token for password reset requests.

    Args:
        user_id (str): The user ID to include as the subject.

    Returns:
        str: Encoded JWT token for password reset.
    """
    return _create_verification_token(
        user_id=user_id,
        token_type="password_reset",
        expires_in_minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES or 60,
    )


def create_new_email_verification_token(user_id: str, new_email: EmailStr) -> str:
    """
    Create a token to verify a new email address during an update.

    Args:
        user_id (str): The user ID to include as the subject.
        new_email (EmailStr): The new email address being verified.

    Returns:
        str: Encoded JWT token for new email verification.
    """
    return _create_verification_token(
        user_id=user_id,
        token_type="new_email_verification",
        expires_in_minutes=settings.NEW_EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES or 1440,
        additional_data={"new_email": new_email},  # Include new email in payload
    )


# ------------------------------------------------------
# --- Verification/Reset Token Decoding ---
# ------------------------------------------------------
def decode_verification_token(token: str, expected_type: str) -> VerificationTokenPayload:
    """
    Decodes and validates a verification/reset token.

    Args:
        token (str): The JWT token string.
        expected_type (str): The expected value for the 'type' claim.

    Raises:
        HTTPException 400: If the token is invalid, expired, or has the wrong type.

    Returns:
        VerificationTokenPayload: The validated and decoded token payload.
    """
    try:
        payload_dict = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        # Validate core fields and type using the Pydantic model
        payload = VerificationTokenPayload(**payload_dict)

        # Explicitly check the token type
        if payload.type != expected_type:
            logger.warning(
                f"Token type mismatch. Expected '{expected_type}', got '{payload.type}'."
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid token type. Expected '{expected_type}'.",
            )

        logger.info(f"Successfully decoded '{payload.type}' token for sub={payload.sub}")
        return payload

    except ExpiredSignatureError:
        logger.warning(f"Expired '{expected_type}' token received.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token has expired.",
        )
    except JWTError as e:
        logger.warning(f"Invalid JWT token received for '{expected_type}': {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token.",
        )
    except Exception as e:
        logger.error(f"Unexpected error decoding '{expected_type}' token: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token.",
        )
