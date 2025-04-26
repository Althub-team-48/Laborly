"""
backend/app/database/enums.py

Enumerations

Defines enumerations used across the platform:
- UserRole: Roles assigned to users (Client, Worker, Admin)
- KYCStatus: Status values for Know Your Customer (KYC) verification
"""

from enum import Enum

# ---------------------------------------------------
# User Role Enumeration
# ---------------------------------------------------


class UserRole(str, Enum):
    """
    Enum representing user roles for access control.

    Values:
    - CLIENT
    - WORKER
    - ADMIN
    """

    CLIENT = "CLIENT"
    WORKER = "WORKER"
    ADMIN = "ADMIN"


# ---------------------------------------------------
# KYC Status Enumeration
# ---------------------------------------------------


class KYCStatus(str, Enum):
    """
    Enum representing the status of a user's KYC verification.

    Values:
    - PENDING
    - APPROVED
    - REJECTED
    """

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
