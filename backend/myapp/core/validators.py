"""
backend/app/core/validators.py

Password Validation Utility

Provides:
- Strict password strength validation
- Enforces ASCII-only passwords
- Minimum and maximum length restrictions
- Uppercase, lowercase, digit, and special character requirements
"""

import string
from typing import Final

# ---------------------------------------------------
# Constants
# ---------------------------------------------------
MIN_PASSWORD_LENGTH: Final[int] = 8
MAX_PASSWORD_LENGTH: Final[int] = 128

# ---------------------------------------------------
# Password Validator
# ---------------------------------------------------


def password_validator(password: str) -> str:
    """
    Validates password strength according to application rules.

    Validation Rules:
    - ASCII characters only
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character
    - Length between MIN_PASSWORD_LENGTH and MAX_PASSWORD_LENGTH

    Args:
        password (str): Password to validate.

    Returns:
        str: Validated password (if all checks pass).

    Raises:
        ValueError: If any validation rule fails.
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
