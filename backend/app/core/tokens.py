"""
core/tokens.py
Token generation utilities:
- JWT access token with expiration and JTI
- Email verification token with short-lived expiration
"""

import uuid
import logging
from typing import Union
from datetime import datetime, timedelta, timezone

from jose import jwt

from app.core.config import settings

logger = logging.getLogger(__name__)


def create_access_token(data: dict, expires_delta: Union[timedelta, None] = None) -> str:
    """
    Create a JWT access token with expiration and unique JTI.
    
    Args:
        data (dict): Payload data to include in the token.
        expires_delta (timedelta | None): Optional custom expiration time.

    Returns:
        str: Encoded JWT token.
    """
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    jti = str(uuid.uuid4())
    payload = {**data, "exp": expire, "jti": jti}

    logger.info(f"Issuing token for sub={data.get('sub')} exp={expire} jti={jti}")
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_email_verification_token(user_id: str) -> str:
    """
    Create a short-lived token for email verification.

    Args:
        user_id (str): The user ID to include as the subject.

    Returns:
        str: Encoded JWT token for email verification.
    """
    expire = datetime.utcnow() + timedelta(minutes=5)
    payload = {
        "sub": user_id,
        "type": "email_verification",
        "exp": expire
    }

    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
