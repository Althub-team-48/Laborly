"""
database/session.py

Initializes the SQLAlchemy asynchronous engine and session factory.
Provides an AsyncGenerator for database session dependency injection.
"""

from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.core.config import settings

# -----------------------------------------------------
# SQLAlchemy Async Engine Initialization
# -----------------------------------------------------
engine = create_async_engine(
    settings.db_url,
    echo=False,  # Set to True for SQL debugging output
)

# -----------------------------------------------------
# Session Factory for Async Database Access
# -----------------------------------------------------
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,  # Prevents auto-expiration of ORM objects after commit
)


# -----------------------------------------------------
# Dependency: Get Async DB Session
# -----------------------------------------------------
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency function for FastAPI endpoints to provide an async DB session.
    Yields a single session per request, rolls back on exceptions, and closes cleanly.
    """
    async with AsyncSessionLocal() as db:
        try:
            yield db
        except Exception:
            await db.rollback()
            raise
