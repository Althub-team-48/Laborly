"""
backend/app/core/blacklist.py

JWT Blacklist Management

Handles JWT token blacklisting using Redis:
- Stores token `jti` (JWT ID) with expiration
- Allows invalidating tokens on logout or forced expiration
"""

import logging

import redis

from app.core.config import settings

# ---------------------------------------------------
# Logger Configuration
# ---------------------------------------------------
logger = logging.getLogger(__name__)

# ---------------------------------------------------
# Redis Client Initialization
# ---------------------------------------------------
redis_client: redis.Redis | None = None  # type: ignore[type-arg]

try:
    redis_client = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        decode_responses=True,  # Ensure stored values are strings
    )
    # Test Redis connection at startup
    redis_client.ping()
    logger.info(
        f"[REDIS] Connected to Redis at {settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
    )
except redis.RedisError as e:
    logger.error(f"[REDIS] Connection failed: {e}")
    redis_client = None  # Safe fallback to prevent import-time failure

# Prefix for all blacklist keys
BLACKLIST_PREFIX = "jwt_blacklist:"

# ---------------------------------------------------
# Blacklist Management Functions
# ---------------------------------------------------


def blacklist_token(jti: str, expires_in: int) -> None:
    """
    Blacklist a JWT token by storing its `jti` in Redis with TTL.

    Args:
        jti (str): Unique JWT ID from the token payload.
        expires_in (int): Expiration time in seconds (matches token lifetime).
    """
    if not redis_client:
        logger.warning("[BLACKLIST] Redis unavailable: Token not blacklisted.")
        return

    try:
        redis_client.setex(f"{BLACKLIST_PREFIX}{jti}", expires_in, "true")
        logger.debug(f"[BLACKLIST] Token blacklisted: jti={jti} for {expires_in}s")
    except redis.RedisError as e:
        logger.error(f"[BLACKLIST] Failed to blacklist token: {e}")


def is_token_blacklisted(jti: str) -> bool:
    """
    Check if a JWT token ID (`jti`) is blacklisted.

    Args:
        jti (str): Token ID to check.

    Returns:
        bool: True if blacklisted, False otherwise.
    """
    if not redis_client:
        logger.warning("[BLACKLIST] Redis unavailable: Assuming token is not blacklisted.")
        return False

    try:
        return redis_client.exists(f"{BLACKLIST_PREFIX}{jti}") == 1
    except redis.RedisError as e:
        logger.error(f"[BLACKLIST] Failed to check token blacklist status: {e}")
        return False
