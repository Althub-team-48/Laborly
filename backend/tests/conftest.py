"""
tests/conftest.py

Test fixtures for:
- Fake users (Admin, Client, Worker)
- Dependency overrides (auth, DB)
- AsyncClient for HTTPX tests
"""

import pytest
import pytest_asyncio
from uuid import uuid4
from unittest.mock import AsyncMock
from httpx import AsyncClient, ASGITransport

from app.auth.schemas import AuthSuccessResponse, AuthUserResponse
from main import app
from app.database.enums import UserRole
from app.core.dependencies import get_db
from app.admin.routes import admin_user_dependency
from app.client.routes import client_user_dependency
from app.worker.routes import require_roles


# -----------------------
# Fake Users
# -----------------------

@pytest_asyncio.fixture
def fake_admin_user():
    class FakeAdminUser:
        id = uuid4()
        role = UserRole.ADMIN
    return FakeAdminUser()

@pytest_asyncio.fixture
def fake_client_user():
    class FakeClientUser:
        id = uuid4()
        role = UserRole.CLIENT
    return FakeClientUser()

@pytest_asyncio.fixture
def fake_worker_user():
    class FakeWorkerUser:
        id = uuid4()
        role = UserRole.WORKER
    return FakeWorkerUser()

@pytest.fixture
def fake_user():
    return AuthUserResponse(
        id="f4c7768e-3e5c-4c88-90d0-71a4fd74b127",
        email="user@example.com",
        phone_number="1234567890",
        first_name="John",
        last_name="Doe",
        role="CLIENT",
        created_at="2024-01-01T00:00:00",
        updated_at="2024-01-01T00:00:00"
    )

# -----------------------
# Dependency Overrides
# -----------------------

@pytest_asyncio.fixture
def override_admin_user(fake_admin_user):
    app.dependency_overrides[admin_user_dependency] = lambda: fake_admin_user
    yield
    app.dependency_overrides.clear()

@pytest_asyncio.fixture
def override_client_user(fake_client_user):
    app.dependency_overrides[client_user_dependency] = lambda: fake_client_user
    yield
    app.dependency_overrides.clear()

@pytest_asyncio.fixture
def override_worker_user(fake_worker_user):
    app.dependency_overrides[require_roles] = lambda *roles: fake_worker_user
    yield
    app.dependency_overrides.clear()

@pytest_asyncio.fixture
def override_get_db():
    async def _override():
        yield AsyncMock()
    app.dependency_overrides[get_db] = _override
    yield
    app.dependency_overrides.clear()


# -----------------------
# Async Test Client
# -----------------------

@pytest_asyncio.fixture
def async_client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")

# -----------------------
# Fake Auth
# -----------------------
@pytest.fixture
def fake_token():
    return "fake-jwt-token"


@pytest.fixture
def fake_auth_response(fake_user, fake_token):
    return AuthSuccessResponse(access_token=fake_token, user=fake_user)