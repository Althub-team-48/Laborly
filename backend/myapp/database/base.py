"""
backend/app/database/base.py

Declarative Base for SQLAlchemy ORM

Defines the shared base class for all database models.
Ensures consistent metadata inheritance across the entire ORM layer.
"""

from sqlalchemy.orm import DeclarativeBase

# ---------------------------------------------------
# Base Model Class
# ---------------------------------------------------


class Base(DeclarativeBase):
    """
    Base class for all ORM models.

    All models should inherit from this to ensure
    consistent metadata management and session operations.
    """

    pass
