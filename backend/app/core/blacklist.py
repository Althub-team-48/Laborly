"""
backend/app/core/blacklist.py

JWT Blacklist Management using Async Redis

Handles JWT token blacklisting using an asynchronous Redis client:
- Stores token `jti` (JWT ID) with expiration
- Allows invalidating tokens on logout or forced expiration
"""

import logging
import redis.asyncio as redis

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
    # Initialize the async client
    redis_client = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        decode_responses=True,
    )
    logger.info(
        f"[REDIS ASYNC] Initialized async Redis client for {settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
    )
except redis.RedisError as e:
    logger.error(f"[REDIS ASYNC] Initialization failed: {e}")
    redis_client = None

# Prefix for all blacklist keys
BLACKLIST_PREFIX = "jwt_blacklist:"


# ---------------------------------------------------
# Blacklist Management Functions
# ---------------------------------------------------
async def blacklist_token(jti: str, expires_in: int) -> None:
    """
    Blacklist a JWT token by storing its `jti` in Redis with TTL (Async).

    Args:
        jti (str): Unique JWT ID from the token payload.
        expires_in (int): Expiration time in seconds (matches token lifetime).
    """
    if not redis_client:
        logger.warning("[BLACKLIST ASYNC] Redis unavailable: Token not blacklisted.")
        return

    try:
        # Use await with the async client's method
        await redis_client.setex(f"{BLACKLIST_PREFIX}{jti}", expires_in, "true")
        logger.debug(f"[BLACKLIST ASYNC] Token blacklisted: jti={jti} for {expires_in}s")
    except redis.RedisError as e:
        logger.error(f"[BLACKLIST ASYNC] Failed to blacklist token: {e}")


async def is_token_blacklisted(jti: str) -> bool:
    """
    Check if a JWT token ID (`jti`) is blacklisted (Async).

    Args:
        jti (str): Token ID to check.

    Returns:
        bool: True if blacklisted, False otherwise.
    """
    if not redis_client:
        logger.warning("[BLACKLIST ASYNC] Redis unavailable: Assuming token is not blacklisted.")
        return False

    try:
        # Use await with the async client's method
        exists = await redis_client.exists(f"{BLACKLIST_PREFIX}{jti}")
        return exists == 1
    except redis.RedisError as e:
        logger.error(f"[BLACKLIST ASYNC] Failed to check token blacklist status: {e}")
        return False
