"""
core/validators.py

Password Validator

Validates password strength based on:
- ASCII-only characters
- Minimum length
- At least one uppercase, lowercase, digit, and special character
"""

import string
from typing import Final


# -------------------------------
# Constants
# -------------------------------
MIN_PASSWORD_LENGTH: Final[int] = 8
MAX_PASSWORD_LENGTH: Final[int] = 128


# -------------------------------
# Validator Function
# -------------------------------
def password_validator(password: str) -> str:
    """
    Validates password strength.

    Rules:
    - Must contain only ASCII characters
    - Must include at least one uppercase letter
    - Must include at least one lowercase letter
    - Must include at least one digit
    - Must include at least one special character
    - Length must be between MIN_PASSWORD_LENGTH and MAX_PASSWORD_LENGTH

    Returns:
        str: The valid password (if all checks pass)

    Raises:
        ValueError: If any rule is violated
    """
    if not password.isascii():
        raise ValueError("Password must contain only ASCII characters.")

    if not any(c in string.ascii_uppercase for c in password):
        raise ValueError("Password must contain at least one uppercase letter.")

    if not any(c in string.ascii_lowercase for c in password):
        raise ValueError("Password must contain at least one lowercase letter.")

    if not any(c.isdigit() for c in password):
        raise ValueError("Password must contain at least one digit.")

    if not any(c in string.punctuation for c in password):
        raise ValueError("Password must contain at least one special character.")

    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters long.")

    if len(password) > MAX_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at most {MAX_PASSWORD_LENGTH} characters long.")

    return password
