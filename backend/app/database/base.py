"""
database/base.py

Defines the declarative base class for SQLAlchemy ORM models.
Used to ensure all models inherit from the same metadata base.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass
