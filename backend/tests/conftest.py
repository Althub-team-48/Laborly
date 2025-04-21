"""
tests/conftest.py

Fixtures for:
- Fake users (Admin, Client, Worker)
- Dependency overrides (auth, DB, role-based)
- Auth response and token mock
- HTTPX AsyncClient for integration tests
- Sample JobRead object for tests
"""

from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.messaging.schemas import MessageRead, ThreadParticipantRead,ThreadRead
from app.review.schemas import ReviewRead, WorkerReviewSummary
from app.service.schemas import ServiceRead
from backend.app.client.schemas import ClientJobRead
from backend.app.worker.schemas import WorkerProfileRead
from main import app
from app.database.enums import UserRole
from app.core.dependencies import get_current_user, get_db
from app.admin.routes import admin_user_dependency
from app.client.routes import client_user_dependency
from app.review.routes import client_dependency
from app.service.routes import require_worker_admin_roles
from app.worker.routes import require_roles
from app.auth.schemas import AuthSuccessResponse, AuthUserResponse
from app.job.schemas import JobRead


# ----------------------------------------------------------------------
# Fake Users
# ----------------------------------------------------------------------

@pytest.fixture
def fake_admin_user():
    class FakeAdminUser:
        id = uuid4()
        role = UserRole.ADMIN
    return FakeAdminUser()

@pytest.fixture
def fake_client_user():
    class FakeClientUser:
        id = uuid4()
        role = UserRole.CLIENT
    return FakeClientUser()

@pytest.fixture
def fake_worker_user():
    class FakeWorkerUser:
        id = uuid4()
        role = UserRole.WORKER
    return FakeWorkerUser()


# ----------------------------------------------------------------------
# Dependency Overrides (Role-based and DB)
# ----------------------------------------------------------------------

@pytest.fixture
def override_admin_user(fake_admin_user):
    app.dependency_overrides[admin_user_dependency] = lambda: fake_admin_user
    yield
    app.dependency_overrides.clear()

@pytest.fixture
def override_client_user(fake_client_user):
    app.dependency_overrides[client_user_dependency] = lambda: fake_client_user
    yield
    app.dependency_overrides.clear()

@pytest.fixture
def override_client(fake_client_user):
    app.dependency_overrides[client_dependency] = lambda: fake_client_user
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def override_worker_user(fake_worker_user):
    app.dependency_overrides[require_roles] = lambda *roles: fake_worker_user
    yield
    app.dependency_overrides.clear()

@pytest.fixture
def override_worker_admin_user(fake_worker_user):
    app.dependency_overrides[require_worker_admin_roles] = lambda: fake_worker_user
    yield
    app.dependency_overrides.clear()
  
       
@pytest.fixture
def override_current_user(fake_client_user):  # Override as needed
    app.dependency_overrides[get_current_user] = lambda: fake_client_user
    yield
    app.dependency_overrides.clear()

@pytest.fixture
def override_get_db():
    async def _override():
        yield AsyncMock()
    app.dependency_overrides[get_db] = _override
    yield
    app.dependency_overrides.clear()


# ----------------------------------------------------------------------
# Fake Auth and Token Response
# ----------------------------------------------------------------------

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

@pytest.fixture
def fake_token():
    return "fake-jwt-token"

@pytest.fixture
def fake_auth_response(fake_user, fake_token):
    return AuthSuccessResponse(
        access_token=fake_token,
        user=fake_user
    )

# ----------------------------------------------------------------------
# Fake Client Object
# ----------------------------------------------------------------------

@pytest.fixture
def fake_client_job_read():
    return ClientJobRead(
        id=uuid4(),
        service_id=uuid4(),
        worker_id=uuid4(),
        status="completed",
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc)
    )

# ----------------------------------------------------------------------
# Fake Job Object
# ----------------------------------------------------------------------

@pytest.fixture
def fake_job_read():
    return JobRead(
        id=uuid4(),
        client_id=uuid4(),
        worker_id=uuid4(),
        service_id=uuid4(),
        status="NEGOTIATING",
        cancel_reason=None,
        started_at=None,
        completed_at=None,
        cancelled_at=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

# ----------------------------------------------------------------------
# Fake Message Objects
# ----------------------------------------------------------------------

@pytest.fixture
def fake_thread_read():
    participants = [
        ThreadParticipantRead(user_id=uuid4()),
        ThreadParticipantRead(user_id=uuid4())
    ]

    messages = [
        MessageRead(
            id=uuid4(),
            content="Hello, this is a test message",
            sender_id=uuid4(),
            thread_id=uuid4(),
            timestamp=datetime.now(timezone.utc)
        ),
        MessageRead(
            id=uuid4(),
            content="Another message",
            sender_id=uuid4(),
            thread_id=uuid4(),
            timestamp=datetime.now(timezone.utc)
        ),
    ]
    return ThreadRead(
        id=uuid4(),
        created_at=datetime.now(timezone.utc),
        job_id=uuid4(),
        is_closed=False,
        participants=participants,
        messages=messages    
    )

@pytest.fixture
def fake_message_read():
    return MessageRead(
        id=uuid4(),
        sender_id=uuid4(),
        thread_id=uuid4(),
        timestamp=datetime.now(timezone.utc),
        content="Hi,can you fix my dishwasher?"
    )

# ----------------------------------------------------------------------
# Fake Review Object
# ----------------------------------------------------------------------

@pytest.fixture
def fake_review_read():
    return ReviewRead(
        id=uuid4(),
        reviewer_id=uuid4(),
        worker_id=uuid4(),
        job_id=uuid4(),
        rating=5,
        text="Suraju did a perfect job",
        is_flagged=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

@pytest.fixture
def fake_review_summary():
    return WorkerReviewSummary(
       average_rating=4.8,
       total_reviews=3
    )   

# ----------------------------------------------------------------------
# Fake Service Object
# ----------------------------------------------------------------------

@pytest.fixture
def fake_service_read():
    return ServiceRead(
        id=uuid4(),
        worker_id=uuid4(),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        title= "plumbing",
        description= "Everything related to plumbing",
        location= "Magodo"
    )
# ----------------------------------------------------------------------
# Fake Worker Object
# ----------------------------------------------------------------------

@pytest.fixture
def fake_worker_profile_read():
    return WorkerProfileRead(
        id=uuid4(),
        user_id=uuid4(),
        is_available=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        is_verified=True,
        professional_skills="Plumbing, Electrical, Carpentry",
        work_experience="Over 10 years in home maintenance services",
        email="worker@example.com",
        first_name="John",
        last_name="Doe",
        phone_number="+2348012345678",
        location="Ikeja, Lagos",
        profile_picture="https://example.com/images/profile.jpg",
        bio="Passionate about improving homes with quality workmanship.",
        years_experience=12,
        availability_note="Available weekdays from 9am to 5pm."
    )
# ----------------------------------------------------------------------
# HTTPX Async Client (ASGI)
# ----------------------------------------------------------------------

@pytest.fixture(scope="module")
def transport():
    return ASGITransport(app=app)

@pytest_asyncio.fixture
def async_client(transport):
    return AsyncClient(transport=transport, base_url="http://test")
