"""
backend/app/core/tokens.py

Token Management Utilities

Handles:
- JWT access token creation with expiration and unique JTI
- Email verification, password reset, and new email verification tokens
- Secure decoding and validation of verification/reset tokens
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, status
from jose import JWTError, ExpiredSignatureError, jwt
from pydantic import EmailStr, ValidationError

from myapp.auth.schemas import VerificationTokenPayload, OAuthStatePayload
from myapp.database.enums import UserRole
from myapp.core.config import settings


# ---------------------------------------------------
# Logger Configuration
# ---------------------------------------------------
logger = logging.getLogger(__name__)


# ---------------------------------------------------
# Access Token Creation
# ---------------------------------------------------
def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a JWT access token with expiration and unique JTI.

    Args:
        data (dict[str, Any]): Payload data containing 'sub' (user ID) and 'role'.
        expires_delta (timedelta | None): Optional expiration override.

    Returns:
        str: Encoded JWT access token.
    """
    if "sub" not in data or "role" not in data:
        logger.error("[TOKEN] 'sub' or 'role' missing in access token payload.")
        raise ValueError("Access token payload must include 'sub' and 'role'.")

    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    jti = str(uuid.uuid4())  # Unique token identifier

    payload = {**data, "exp": expire, "jti": jti}
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    logger.info(f"[TOKEN] Issued access token for sub={data['sub']} exp={expire} jti={jti}")
    return str(token)


# ---------------------------------------------------
# Verification/Reset Token Creation (Internal Helper)
# ---------------------------------------------------
def _create_verification_token(
    user_id: str,
    token_type: str,
    expires_in_minutes: int,
    additional_data: dict[str, Any] | None = None,
) -> str:
    """
    Internal helper to create short-lived verification or reset tokens.
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_in_minutes)
    payload = {
        "sub": user_id,
        "type": token_type,
        "exp": expire,
    }
    if additional_data:
        payload.update(additional_data)

    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    logger.info(f"[TOKEN] Issued '{token_type}' token for sub={user_id} exp={expire}")
    return str(token)


# ---------------------------------------------------
# Public Token Creation Functions
# ---------------------------------------------------
def create_email_verification_token(user_id: str) -> str:
    """
    Create a token for initial email address verification.
    """
    return _create_verification_token(
        user_id=user_id,
        token_type="email_verification",
        expires_in_minutes=settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES or 30,
    )


def create_password_reset_token(user_id: str) -> str:
    """
    Create a token for password reset.
    """
    return _create_verification_token(
        user_id=user_id,
        token_type="password_reset",
        expires_in_minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES or 60,
    )


def create_new_email_verification_token(user_id: str, new_email: EmailStr) -> str:
    """
    Create a token for verifying a user's new email address.
    """
    return _create_verification_token(
        user_id=user_id,
        token_type="new_email_verification",
        expires_in_minutes=settings.NEW_EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES or 1440,
        additional_data={"new_email": new_email},
    )


# ---------------------------------------------------
# OAuth State Token Creation
# ---------------------------------------------------
def create_oauth_state_token(role: UserRole | None, nonce: str) -> str:
    """
    Create a short-lived JWT to be used as the OAuth state parameter.
    Args:
        role (UserRole | None): The intended role for signup.
        nonce (str): A unique nonce for CSRF protection.
    Returns:
        str: Encoded state JWT.
    """
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.OAUTH_STATE_TOKEN_EXPIRE_MINUTES
    )
    payload = OAuthStatePayload(role=role, nonce=nonce)
    full_payload = {**payload.model_dump(exclude_none=True), "exp": expire}

    token = jwt.encode(full_payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    logger.debug(f"[TOKEN] Issued OAuth state token with nonce {nonce} and role {role}")
    return str(token)


# ---------------------------------------------------
# OAuth State Token Decoding
# ---------------------------------------------------
def decode_oauth_state_token(token: str) -> OAuthStatePayload:
    """
    Decode and validate the OAuth state JWT.
    Args:
        token (str): The state JWT received from the callback.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid or expired state parameter.",
    )
    try:
        payload_dict = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        payload = OAuthStatePayload(**payload_dict)
        logger.debug(f"[TOKEN] Successfully decoded OAuth state token for nonce {payload.nonce}")
        return payload

    except ExpiredSignatureError:
        logger.warning("[TOKEN] Expired OAuth state token received.")
        raise credentials_exception
    except JWTError as e:
        logger.warning(f"[TOKEN] Invalid OAuth state JWT: {e}")
        raise credentials_exception
    except ValidationError as e:
        logger.warning(f"[TOKEN] OAuth state payload validation error: {e}")
        raise credentials_exception
    except Exception as e:
        logger.error(f"[TOKEN] Unexpected error decoding OAuth state token: {e}", exc_info=True)
        raise credentials_exception


# ---------------------------------------------------
# Token Decoding and Validation
# ---------------------------------------------------
def decode_verification_token(
    token: str,
    expected_type: str,
) -> VerificationTokenPayload:
    """
    Decode and validate a verification/reset token.

    Args:
        token (str): The encoded JWT token.
        expected_type (str): Expected token type (e.g., 'email_verification').

    Raises:
        HTTPException 400: If token is expired, invalid, or type mismatch.

    Returns:
        VerificationTokenPayload: The validated token payload.
    """
    try:
        payload_dict = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        payload = VerificationTokenPayload(**payload_dict)

        if payload.type != expected_type:
            logger.warning(
                f"[TOKEN] Token type mismatch: expected '{expected_type}', got '{payload.type}'."
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid token type. Expected '{expected_type}'.",
            )

        logger.info(f"[TOKEN] Successfully decoded '{payload.type}' token for sub={payload.sub}")
        return payload

    except ExpiredSignatureError:
        logger.warning(f"[TOKEN] Expired '{expected_type}' token received.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token has expired.",
        )
    except JWTError as e:
        logger.warning(f"[TOKEN] Invalid JWT token for '{expected_type}': {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token.",
        )
    except Exception as e:
        logger.error(
            f"[TOKEN] Unexpected error decoding '{expected_type}' token: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token.",
        )
