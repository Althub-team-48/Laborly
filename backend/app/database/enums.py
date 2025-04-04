from enum import Enum


class UserRole(str, Enum):
    CLIENT = "CLIENT"
    WORKER = "WORKER"
    ADMIN = "ADMIN"


class KYCStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
