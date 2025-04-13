"""
enums.py

Defines enumerations used throughout the platform:
- UserRole: Defines roles for access control (Client, Worker, Admin)
- KYCStatus: Represents status of user identity verification
"""

from enum import Enum


# -------------------------
# USER ROLE ENUM
# -------------------------
class UserRole(str, Enum):
    CLIENT = "CLIENT"
    WORKER = "WORKER"
    ADMIN = "ADMIN"


# -------------------------
# KYC STATUS ENUM
# -------------------------
class KYCStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
