# tests/conftest.py
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os
from main import app
from app.database.session import get_db
from app.database.base import Base
from app.database.models import User, UserRole
from app.auth.services import get_password_hash, create_access_token
from httpx import AsyncClient, ASGITransport
from uuid import uuid4

load_dotenv()
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

# Create engine globally, but we'll manage its lifecycle per test
engine = create_async_engine(TEST_DATABASE_URL, echo=True)
TestSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, autocommit=False, autoflush=False)

@pytest_asyncio.fixture(scope="function")
async def db_session():
    # Setup: Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Provide session
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()
    
    # Teardown: Drop tables and dispose engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest_asyncio.fixture
async def async_client(db_session):
    async def override_get_db():
        yield db_session
    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()

@pytest_asyncio.fixture
async def client_user(db_session):
    user = User(
        id=uuid4(),
        email=f"client_{uuid4().hex[:6]}@test.com",
        phone_number="1234567890",
        hashed_password=get_password_hash("testpassword"),
        role=UserRole.CLIENT,
        is_active=True,
        is_frozen=False,
        is_banned=False,
        is_deleted=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user

@pytest_asyncio.fixture
async def worker_user(db_session):
    user = User(
        id=uuid4(),
        email=f"worker_{uuid4().hex[:6]}@test.com",
        phone_number="9876543210",
        hashed_password=get_password_hash("testpassword"),
        role=UserRole.WORKER,
        is_active=True,
        is_frozen=False,
        is_banned=False,
        is_deleted=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user

@pytest_asyncio.fixture
async def admin_user(db_session):
    user = User(
        id=uuid4(),
        email=f"admin_{uuid4().hex[:6]}@test.com",
        phone_number="5555555555",
        hashed_password=get_password_hash("testpassword"),
        role=UserRole.ADMIN,
        is_active=True,
        is_frozen=False,
        is_banned=False,
        is_deleted=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user

@pytest_asyncio.fixture
async def client_token(client_user):
    return create_access_token({"sub": str(client_user.id), "role": "CLIENT"})

@pytest_asyncio.fixture
async def worker_token(worker_user):
    return create_access_token({"sub": str(worker_user.id), "role": "WORKER"})

@pytest_asyncio.fixture
async def admin_token(admin_user):
    return create_access_token({"sub": str(admin_user.id), "role": "ADMIN"})