# tests/conftest.py

"""
Test fixtures for async database setup, client authentication, and test users.
Used across all test modules in the Laborly backend.
"""

import asyncio
import os
from uuid import uuid4

import pytest
import pytest_asyncio
from dotenv import load_dotenv
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from main import app
from app.database.session import get_db
from app.database.base import Base
from app.database.models import User, UserRole
from app.auth.services import get_password_hash, create_access_token

# Load environment variables
load_dotenv()
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

# Create async engine and session factory
engine = create_async_engine(TEST_DATABASE_URL, echo=True)
TestSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # ✅ important to avoid re-accessing stale state
    autocommit=False,
    autoflush=False,
)


async def drop_all_tables(conn):
    """
    Drop all tables in reverse order of dependencies to avoid issues.
    """
    for table in reversed(Base.metadata.sorted_tables):
        await conn.run_sync(table.drop, checkfirst=True)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def setup_database():
    """Create and tear down the test database schema per test function."""
    async with engine.begin() as conn:
        # Drop tables in order to handle dependencies (instead of using cascade=True)
        await drop_all_tables(conn)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await drop_all_tables(conn)


@pytest_asyncio.fixture
async def db_session(setup_database):
    """Provide a database session for each test."""
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def async_client(setup_database):
    """Provide an async HTTP client with overridden DB dependency."""
    async def override_get_db():
        async with TestSessionLocal() as session:
            yield session
            await session.rollback()

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client_user(db_session):
    """Create a test client user."""
    user = User(
        id=uuid4(),
        email=f"client_{uuid4().hex[:6]}@test.com",
        hashed_password=get_password_hash("testpassword"),
        role=UserRole.CLIENT,
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def worker_user(db_session):
    """Create a test worker user."""
    user = User(
        id=uuid4(),
        email=f"worker_{uuid4().hex[:6]}@test.com",
        hashed_password=get_password_hash("testpassword"),
        role=UserRole.WORKER,
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_user(db_session):
    """Create a test admin user."""
    user = User(
        id=uuid4(),
        email=f"admin_{uuid4().hex[:6]}@test.com",
        hashed_password=get_password_hash("testpassword"),
        role=UserRole.ADMIN,
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
def client_token(client_user):
    """Generate a JWT token for a client user."""
    return create_access_token({"sub": str(client_user.id), "role": "CLIENT"})


@pytest_asyncio.fixture
def worker_token(worker_user):
    """Generate a JWT token for a worker user."""
    return create_access_token({"sub": str(worker_user.id), "role": "WORKER"})


@pytest_asyncio.fixture
def admin_token(admin_user):
    """Generate a JWT token for an admin user."""
    return create_access_token({"sub": str(admin_user.id), "role": "ADMIN"})


