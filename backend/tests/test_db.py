import pytest
import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text

# Load environment variables
load_dotenv()

# Fixture to create database engine
@pytest.fixture
async def db_engine():
    # Get the TEST_DATABASE_URL from .env
    db_url = os.getenv("TEST_DATABASE_URL")
    if not db_url:
        pytest.fail("TEST_DATABASE_URL not found in .env file")
    
    # Create async engine
    engine = create_async_engine(db_url, echo=False)
    yield engine
    
    # Cleanup
    await engine.dispose()

# Test database connection
@pytest.mark.asyncio
async def test_database_connection(db_engine):
    async with AsyncSession(db_engine) as session:
        try:
            # Execute a simple query to test connection
            result = await session.execute(text("SELECT 1"))
            assert result.scalar() == 1
        except Exception as e:
            pytest.fail(f"Database connection failed: {str(e)}")

# Test database version
@pytest.mark.asyncio
async def test_postgres_version(db_engine):
    async with AsyncSession(db_engine) as session:
        result = await session.execute(text("SELECT version()"))
        version = result.scalar()
        assert "PostgreSQL" in version