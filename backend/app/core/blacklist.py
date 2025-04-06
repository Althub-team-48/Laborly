"""
core/blacklist.py

Handles JWT token blacklisting using Redis:
- Stores token jti (JWT ID) with an expiration
- Used to invalidate tokens on logout or force-expire sessions
"""

import redis
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# ------------------------------------------------------
# Redis Client Initialization from .env Settings
# ------------------------------------------------------
try:
    redis_client = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        decode_responses=True  # Ensures values are strings, not bytes
    )
    # Test connection at startup
    redis_client.ping()
    logger.info(f"Connected to Redis at {settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}")
except redis.RedisError as e:
    logger.error(f"Redis connection failed: {e}")
    redis_client = None  # Fallback — avoid raising at import time

# Prefix for blacklist keys
BLACKLIST_PREFIX = "jwt_blacklist:"


def blacklist_token(jti: str, expires_in: int):
    """
    Add a JWT token ID to Redis blacklist with TTL.

    Args:
        jti (str): Unique JWT ID from payload.
        expires_in (int): TTL in seconds (match token expiration).
    """
    if not redis_client:
        logger.warning("Redis unavailable: token not blacklisted.")
        return

    try:
        redis_client.setex(f"{BLACKLIST_PREFIX}{jti}", expires_in, "true")
        logger.debug(f"Token blacklisted: jti={jti} for {expires_in}s")
    except redis.RedisError as e:
        logger.error(f"Failed to blacklist token: {e}")


def is_token_blacklisted(jti: str) -> bool:
    """
    Check whether a JWT ID is currently blacklisted.

    Args:
        jti (str): Token ID to check.

    Returns:
        bool: True if blacklisted, False otherwise.
    """
    if not redis_client:
        logger.warning("Redis unavailable: assuming token is not blacklisted.")
        return False

    try:
        return redis_client.exists(f"{BLACKLIST_PREFIX}{jti}") == 1
    except redis.RedisError as e:
        logger.error(f"Failed to check blacklist for jti={jti}: {e}")
        return False
