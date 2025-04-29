"""
tests/conftest.py

Test fixtures for API integration and unit tests.
Includes async clients, fake users, schema mock data, and dependency overrides.
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
    
# --- Imports ---
from collections.abc import Generator, AsyncGenerator
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
import pytest_asyncio

from main import app
from app.database.enums import UserRole, KYCStatus
from app.job.models import JobStatus
from app.database.session import get_db
from app.database.models import User
from app.core.dependencies import get_current_user
from app.auth.schemas import AuthSuccessResponse, AuthUserResponse
from app.job.schemas import JobRead
from app.client.schemas import ClientProfileRead, ClientJobRead, FavoriteRead, PublicClientRead
from app.worker.schemas import WorkerProfileRead, PublicWorkerRead, KYCRead
from app.service.schemas import ServiceRead
from app.review.schemas import ReviewRead, PublicReviewRead, WorkerReviewSummary
from app.messaging.schemas import MessageRead, ThreadRead, ParticipantInfo, ThreadParticipantRead


# --- Core Test Fixtures ---


@pytest.fixture(scope="session")
def transport() -> ASGITransport:
    """Fixture for ASGI transport."""
    return ASGITransport(app=app)


@pytest_asyncio.fixture(scope="function")
async def async_client(transport: ASGITransport) -> AsyncGenerator[AsyncClient, None]:
    """Fixture for HTTP async client."""
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


# --- Fake User Fixtures ---


@pytest.fixture
def fake_admin_user() -> User:
    """Fixture for a fake admin user."""
    return User(
        id=uuid4(),
        email="admin.test@example.com",
        role=UserRole.ADMIN,
        first_name="Admin",
        last_name="Test",
        hashed_password="fakehashedpassword",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        phone_number="08011110000",
        is_active=True,
        is_frozen=False,
        is_banned=False,
        is_deleted=False,
        is_verified=True,
        location="Admin Location",
    )


@pytest.fixture
def fake_client_user() -> User:
    """Fixture for a fake client user."""
    return User(
        id=uuid4(),
        email="client.test@example.com",
        role=UserRole.CLIENT,
        first_name="Client",
        last_name="Test",
        hashed_password="fakehashedpassword",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        phone_number="08022220000",
        is_active=True,
        is_frozen=False,
        is_banned=False,
        is_deleted=False,
        is_verified=True,
        location="Client Location",
    )


@pytest.fixture
def fake_worker_user() -> User:
    """Fixture for a fake worker user."""
    return User(
        id=uuid4(),
        email="worker.test@example.com",
        role=UserRole.WORKER,
        first_name="Worker",
        last_name="Test",
        hashed_password="fakehashedpassword",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        phone_number="08033330000",
        is_active=True,
        is_frozen=False,
        is_banned=False,
        is_deleted=False,
        is_verified=True,
        location="Worker Location",
    )


# --- Dependency Override Fixtures ---


@pytest_asyncio.fixture
async def override_get_db() -> AsyncGenerator[None, None]:
    """Override for the database dependency."""

    async def _override() -> AsyncGenerator[AsyncMock, None]:
        yield AsyncMock()

    app.dependency_overrides[get_db] = _override
    yield
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def override_get_current_user(fake_client_user: User) -> Generator[None, None, None]:
    """Override for getting the current user as a client."""
    app.dependency_overrides[get_current_user] = lambda: fake_client_user
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest_asyncio.fixture
async def mock_current_admin_user(fake_admin_user: User) -> AsyncGenerator[User, None]:
    """Mock the current user as an admin."""
    app.dependency_overrides[get_current_user] = lambda: fake_admin_user
    yield fake_admin_user
    app.dependency_overrides.pop(get_current_user, None)


@pytest_asyncio.fixture
async def mock_current_client_user(fake_client_user: User) -> AsyncGenerator[User, None]:
    """Mock the current user as a client."""
    app.dependency_overrides[get_current_user] = lambda: fake_client_user
    yield fake_client_user
    app.dependency_overrides.pop(get_current_user, None)


@pytest_asyncio.fixture
async def mock_current_worker_user(fake_worker_user: User) -> AsyncGenerator[User, None]:
    """Mock the current user as a worker."""
    app.dependency_overrides[get_current_user] = lambda: fake_worker_user
    yield fake_worker_user
    app.dependency_overrides.pop(get_current_user, None)


# --- Fake Data Fixtures (Schema Instances) ---


@pytest.fixture
def fake_auth_user_response(fake_client_user: User) -> AuthUserResponse:
    """Fixture for fake AuthUserResponse."""
    return AuthUserResponse(
        id=fake_client_user.id,
        email=fake_client_user.email,
        phone_number=fake_client_user.phone_number,
        first_name=fake_client_user.first_name,
        last_name=fake_client_user.last_name,
        role=fake_client_user.role,
        is_verified=fake_client_user.is_verified,
        created_at=fake_client_user.created_at,
        updated_at=fake_client_user.updated_at,
    )


@pytest.fixture
def fake_token() -> str:
    """Fixture for a fake JWT token."""
    return "fake-jwt-token"


@pytest.fixture
def fake_auth_success_response(
    fake_auth_user_response: AuthUserResponse, fake_token: str
) -> AuthSuccessResponse:
    """Fixture for a fake successful auth response."""
    return AuthSuccessResponse(access_token=fake_token, user=fake_auth_user_response)


@pytest.fixture
def fake_job_read() -> JobRead:
    """Fixture for a fake JobRead."""
    return JobRead(
        id=uuid4(),
        client_id=uuid4(),
        worker_id=uuid4(),
        service_id=uuid4(),
        status=JobStatus.NEGOTIATING,
        cancel_reason=None,
        started_at=None,
        completed_at=None,
        cancelled_at=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def fake_client_profile_read(fake_client_user: User) -> ClientProfileRead:
    """Fixture for a fake ClientProfileRead."""
    return ClientProfileRead(
        id=uuid4(),
        user_id=fake_client_user.id,
        email=fake_client_user.email,
        phone_number=fake_client_user.phone_number or "08012345678",
        first_name=fake_client_user.first_name,
        last_name=fake_client_user.last_name,
        location=fake_client_user.location or "Lagos",
        profile_description="A test client profile.",
        address="123 Test Street, Lagos",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def fake_public_client_read(fake_client_user: User) -> PublicClientRead:
    """Fixture for a fake PublicClientRead."""
    return PublicClientRead(
        user_id=fake_client_user.id,
        first_name=fake_client_user.first_name,
        last_name=fake_client_user.last_name,
        location=fake_client_user.location or "Lagos",
    )


@pytest.fixture
def fake_favorite_read(fake_client_user: User, fake_worker_user: User) -> FavoriteRead:
    """Fixture for a fake FavoriteRead."""
    return FavoriteRead(
        id=uuid4(),
        worker_id=fake_worker_user.id,
        client_id=fake_client_user.id,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def fake_client_job_read(fake_client_user: User, fake_worker_user: User) -> ClientJobRead:
    """Fixture for a fake ClientJobRead."""
    return ClientJobRead(
        id=uuid4(),
        service_id=uuid4(),
        worker_id=fake_worker_user.id,
        status=JobStatus.COMPLETED.value,
        started_at=datetime.now(timezone.utc) - timedelta(days=1),
        completed_at=datetime.now(timezone.utc),
        cancelled_at=None,
        cancel_reason=None,
    )


@pytest.fixture
def fake_worker_profile_read(fake_worker_user: User) -> WorkerProfileRead:
    """Fixture for a fake WorkerProfileRead."""
    return WorkerProfileRead(
        id=uuid4(),
        user_id=fake_worker_user.id,
        is_available=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        is_kyc_verified=True,
        professional_skills="Plumbing, Testing",
        work_experience="5 years testing fixtures.",
        email=fake_worker_user.email,
        first_name=fake_worker_user.first_name,
        last_name=fake_worker_user.last_name,
        phone_number=fake_worker_user.phone_number or "09087654321",
        location=fake_worker_user.location or "Abuja",
        bio="Dedicated test worker.",
        years_experience=5,
        availability_note="Ready to test.",
    )


@pytest.fixture
def fake_public_worker_read(fake_worker_user: User) -> PublicWorkerRead:
    """Fixture for a fake PublicWorkerRead."""
    return PublicWorkerRead(
        user_id=fake_worker_user.id,
        first_name=fake_worker_user.first_name,
        last_name=fake_worker_user.last_name,
        location=fake_worker_user.location or "Abuja",
        professional_skills="Plumbing, Testing",
        work_experience="5 years testing fixtures.",
        years_experience=5,
        bio="Dedicated test worker.",
        is_available=True,
        is_kyc_verified=True,
    )


@pytest.fixture
def fake_kyc_read(fake_worker_user: User) -> KYCRead:
    """Fixture for a fake KYCRead."""
    return KYCRead(
        id=uuid4(),
        user_id=fake_worker_user.id,
        document_type="Passport",
        document_path="s3://bucket/kyc/doc.pdf",
        selfie_path="s3://bucket/kyc/selfie.jpg",
        status=KYCStatus.APPROVED,
        submitted_at=datetime.now(timezone.utc) - timedelta(days=2),
        reviewed_at=datetime.now(timezone.utc) - timedelta(days=1),
    )


@pytest.fixture
def fake_service_read(fake_worker_user: User) -> ServiceRead:
    """Fixture for a fake ServiceRead."""
    return ServiceRead(
        id=uuid4(),
        worker_id=fake_worker_user.id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        title="Testing Service",
        description="Provides high-quality testing.",
        location="Remote",
    )


@pytest.fixture
def fake_review_read(fake_client_user: User, fake_worker_user: User) -> ReviewRead:
    """Fixture for a fake ReviewRead."""
    return ReviewRead(
        id=uuid4(),
        client_id=fake_client_user.id,
        worker_id=fake_worker_user.id,
        job_id=uuid4(),
        rating=5,
        text="Excellent testing work!",
        is_flagged=False,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def fake_public_review_read(fake_worker_user: User) -> PublicReviewRead:
    """Fixture for a fake PublicReviewRead."""
    return PublicReviewRead(
        id=uuid4(),
        worker_id=fake_worker_user.id,
        job_id=uuid4(),
        rating=4,
        text="Good job.",
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def fake_review_summary() -> WorkerReviewSummary:
    """Fixture for a fake WorkerReviewSummary."""
    return WorkerReviewSummary(average_rating=4.5, total_reviews=10)


@pytest.fixture
def fake_participant_info(fake_client_user: User) -> ParticipantInfo:
    """Fixture for a fake ParticipantInfo."""
    return ParticipantInfo(
        id=fake_client_user.id,
        first_name=fake_client_user.first_name,
        last_name=fake_client_user.last_name,
        profile_picture=None,
    )


@pytest.fixture
def fake_message_read(fake_participant_info: ParticipantInfo) -> MessageRead:
    """Fixture for a fake MessageRead."""
    return MessageRead(
        id=uuid4(),
        sender=fake_participant_info,
        thread_id=uuid4(),
        timestamp=datetime.now(timezone.utc),
        content="This is a test message.",
    )


@pytest.fixture
def fake_thread_read(
    fake_participant_info: ParticipantInfo, fake_message_read: MessageRead
) -> ThreadRead:
    """Fixture for a fake ThreadRead."""
    participant1 = fake_participant_info
    participant2_user = User(
        id=uuid4(),
        first_name="Worker",
        last_name="Bee",
        email="workerb@e.com",
        role=UserRole.WORKER,
        hashed_password="pw",
    )
    participant2 = ParticipantInfo(
        id=participant2_user.id,
        first_name=participant2_user.first_name,
        last_name=participant2_user.last_name,
        profile_picture=None,
    )

    thread_participants = [
        ThreadParticipantRead(user=participant1),
        ThreadParticipantRead(user=participant2),
    ]

    return ThreadRead(
        id=uuid4(),
        created_at=datetime.now(timezone.utc),
        job_id=uuid4(),
        is_closed=False,
        participants=thread_participants,
        messages=[fake_message_read],
    )
