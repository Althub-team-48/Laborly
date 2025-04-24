"""
core/limiter.py

Rate Limiter Configuration
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# -----------------------------
# Rate Limiter Initialization
# -----------------------------
limiter = Limiter(key_func=get_remote_address)
