"""
database/session.py

Initializes the SQLAlchemy database engine and session factory.
Provides a dependency-compatible AsyncGenerator for database sessions.
"""

from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.core.config import settings

# --------------------------------------
# SQLAlchemy Async Engine Initialization
# --------------------------------------
engine = create_async_engine(settings.db_url, echo=False)

# --------------------------------------
# Session Factory for Async DB Access
# --------------------------------------
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,  # Prevents auto-expiration of objects after commit
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency function for FastAPI to provide an async DB session.
    Yields a single session per request and closes it afterward.
    """
    async with AsyncSessionLocal() as db:
        try:
            yield db
        except Exception as e:
            await db.rollback()
            raise e
