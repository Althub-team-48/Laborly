# core/blacklist.py

import redis
from app.core.config import settings

# Connect to Redis (adjust host/port if needed)
redis_client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)

BLACKLIST_PREFIX = "jwt_blacklist:"


def blacklist_token(jti: str, expires_in: int):
    """
    Add token ID to Redis blacklist with expiration.
    """
    redis_client.setex(f"{BLACKLIST_PREFIX}{jti}", expires_in, "true")


def is_token_blacklisted(jti: str) -> bool:
    """
    Check if token ID is in Redis blacklist.
    """
    return redis_client.exists(f"{BLACKLIST_PREFIX}{jti}") == 1
