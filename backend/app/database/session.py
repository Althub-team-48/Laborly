"""
database/session.py

Initializes the SQLAlchemy database engine and session factory.
Provides a dependency-compatible AsyncGenerator for database sessions.
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# --------------------------------------
# SQLAlchemy Async Engine Initialization
# --------------------------------------
engine = create_async_engine(settings.DATABASE_URL, echo=False)

# --------------------------------------
# Session Factory for Async DB Access
# --------------------------------------
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency function for FastAPI to provide an async DB session.
    Yields a single session per request and closes it afterward.
    """
    async with AsyncSessionLocal() as db:
        yield db
