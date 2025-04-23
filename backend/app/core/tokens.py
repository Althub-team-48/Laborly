"""
core/tokens.py

Token generation utilities:
- JWT access token with expiration and JTI
- Email verification token with short-lived expiration
"""

import uuid
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import jwt

from app.core.config import settings

logger = logging.getLogger(__name__)


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """
    Create a JWT access token with expiration and unique JTI.

    Args:
        data (dict[str, Any]): Payload data to include in the token.
        expires_delta (timedelta | None): Optional custom expiration time.

    Returns:
        str: Encoded JWT token.
    """
    expire: datetime = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    jti: str = str(uuid.uuid4())
    payload: dict[str, Any] = {**data, "exp": expire, "jti": jti}

    logger.info(f"Issuing token for sub={data.get('sub')} exp={expire} jti={jti}")
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return str(token)


def create_email_verification_token(user_id: str) -> str:
    """
    Create a short-lived token for email verification.

    Args:
        user_id (str): The user ID to include as the subject.

    Returns:
        str: Encoded JWT token for email verification.
    """
    expire: datetime = datetime.now(timezone.utc) + timedelta(minutes=5)
    payload: dict[str, str | datetime] = {
        "sub": user_id,
        "type": "email_verification",
        "exp": expire,
    }

    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    logger.info(f"Issuing email verification token for sub={user_id} exp={expire}")
    return str(token)
