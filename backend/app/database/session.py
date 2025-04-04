"""
database/session.py

Initializes the SQLAlchemy database engine and session factory.
Provides a dependency-compatible generator for database sessions.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from typing import Generator

from app.core.config import settings

# Create the SQLAlchemy engine using the database URL from settings
engine = create_engine(settings.DATABASE_URL)

# Configure a session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Generator:
    """
    Dependency generator to provide a database session.
    Ensures proper closing of the session after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
