"""
backend/app/core/limiter.py

Rate Limiter Configuration

Initializes and configures the SlowAPI rate limiter using
the remote address as the unique client key.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# ---------------------------------------------------
# Rate Limiter Initialization
# ---------------------------------------------------
limiter = Limiter(key_func=get_remote_address)
