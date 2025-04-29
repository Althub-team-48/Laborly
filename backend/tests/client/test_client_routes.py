"""
tests/client/test_client_routes.py

Test cases for client profile, favorite workers, and client job history API endpoints.
Covers public profile access, authenticated profile management, favorite actions, and job listings.
"""

import pytest
from uuid import UUID, uuid4
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException, status
from httpx import AsyncClient
from io import BytesIO

from myapp.database.models import User
from myapp.client.models import FavoriteWorker
from myapp.job.models import Job, JobStatus
from myapp.client import schemas as client_schemas
from myapp.client import services as client_services

# Helper function


def create_fake_job(client_id: UUID, worker_id: UUID, service_id: UUID | None = None) -> Job:
    """Create a fake Job instance for testing."""
    return Job(
        id=uuid4(),
        client_id=client_id,
        worker_id=worker_id,
        service_id=service_id or uuid4(),
        status=JobStatus.COMPLETED,
        created_at=datetime.now(timezone.utc) - timedelta(days=2),
        updated_at=datetime.now(timezone.utc) - timedelta(days=1),
        started_at=datetime.now(timezone.utc) - timedelta(days=1, hours=2),
        completed_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )


# Public Profile Endpoints


@pytest.mark.asyncio
@patch.object(client_services.ClientService, "get_public_client_profile", new_callable=AsyncMock)
async def test_get_public_client_profile(
    mock_get_public_profile: AsyncMock,
    fake_public_client_read: client_schemas.PublicClientRead,
    async_client: AsyncClient,
    override_get_db: None,
) -> None:
    """Test retrieving a public client profile."""
    test_user_id = fake_public_client_read.user_id
    mock_get_public_profile.return_value = fake_public_client_read

    response = await async_client.get(f"/client/{test_user_id}/public")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["user_id"] == str(fake_public_client_read.user_id)
    assert data["first_name"] == fake_public_client_read.first_name
    mock_get_public_profile.assert_awaited_once_with(test_user_id)


@pytest.mark.asyncio
@patch.object(client_services.ClientService, "get_public_client_profile", new_callable=AsyncMock)
async def test_get_public_client_profile_not_found(
    mock_get_public_profile: AsyncMock,
    async_client: AsyncClient,
    override_get_db: None,
) -> None:
    """Test retrieving a non-existent public client profile."""
    test_user_id = uuid4()
    mock_get_public_profile.side_effect = HTTPException(status_code=404, detail="Client not found")

    response = await async_client.get(f"/client/{test_user_id}/public")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Client not found"
    mock_get_public_profile.assert_awaited_once_with(test_user_id)


# Authenticated Client Profile Endpoints


@pytest.mark.asyncio
@patch.object(client_services.ClientService, "get_profile", new_callable=AsyncMock)
async def test_get_my_client_profile(
    mock_get_profile: AsyncMock,
    fake_client_profile_read: client_schemas.ClientProfileRead,
    mock_current_client_user: User,
    async_client: AsyncClient,
    override_get_db: None,
) -> None:
    """Test retrieving the authenticated client's profile."""
    mock_get_profile.return_value = fake_client_profile_read

    response = await async_client.get("/client/profile")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["user_id"] == str(mock_current_client_user.id)
    assert data["email"] == fake_client_profile_read.email
    mock_get_profile.assert_awaited_once_with(mock_current_client_user.id)


@pytest.mark.asyncio
@patch.object(client_services.ClientService, "update_profile", new_callable=AsyncMock)
async def test_update_my_client_profile(
    mock_update_profile: AsyncMock,
    mock_current_client_user: User,
    async_client: AsyncClient,
    override_get_db: None,
) -> None:
    """Test updating the authenticated client's profile."""
    update_payload_dict = {
        "location": "Ibadan",
        "profile_description": "Updated description.",
    }
    mock_response_profile = client_schemas.ClientProfileRead(
        id=uuid4(),
        user_id=mock_current_client_user.id,
        email=mock_current_client_user.email,
        phone_number="08022220000",
        first_name="Client",
        last_name="Test",
        location="Ibadan",
        profile_description="Updated description.",
        address="123 Test Street, Lagos",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    mock_update_profile.return_value = mock_response_profile

    response = await async_client.patch("/client/profile", json=update_payload_dict)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["location"] == update_payload_dict["location"]
    assert data["profile_description"] == update_payload_dict["profile_description"]
    mock_update_profile.assert_awaited_once()
    call_args, _ = mock_update_profile.call_args
    assert call_args[0] == mock_current_client_user.id
    assert isinstance(call_args[1], client_schemas.ClientProfileUpdate)


@pytest.mark.asyncio
@patch("app.client.routes.upload_file_to_s3", new_callable=AsyncMock)
@patch.object(client_services.ClientService, "update_profile_picture", new_callable=AsyncMock)
async def test_update_my_client_profile_picture(
    mock_update_pic_service: AsyncMock,
    mock_upload: AsyncMock,
    mock_current_client_user: User,
    async_client: AsyncClient,
    override_get_db: None,
) -> None:
    """Test updating client's profile picture."""
    fake_s3_url = "https://fake-bucket.s3.amazonaws.com/profile_pictures/fake_pic.png"
    mock_upload.return_value = fake_s3_url
    mock_update_pic_service.return_value = client_schemas.MessageResponse(
        detail="Profile picture updated successfully."
    )

    files = {"profile_picture": ("test.png", BytesIO(b"fake image data"), "image/png")}
    response = await async_client.patch("/client/profile/picture", files=files)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["detail"] == "Profile picture updated successfully."
    mock_upload.assert_awaited_once()
    mock_update_pic_service.assert_awaited_once_with(mock_current_client_user.id, fake_s3_url)


@pytest.mark.asyncio
@patch.object(
    client_services.ClientService, "get_profile_picture_presigned_url", new_callable=AsyncMock
)
async def test_get_my_client_profile_picture_url_success(
    mock_get_url: AsyncMock,
    mock_current_client_user: User,
    async_client: AsyncClient,
    override_get_db: None,
) -> None:
    """Test getting client's profile picture presigned URL."""
    fake_url = f"https://fake-bucket.s3.amazonaws.com/profile_pictures/client_{mock_current_client_user.id}?sig=xyz"
    mock_get_url.return_value = fake_url

    response = await async_client.get("/client/profile/picture-url")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["url"] == fake_url
    mock_get_url.assert_awaited_once_with(mock_current_client_user.id)


@pytest.mark.asyncio
@patch.object(
    client_services.ClientService, "get_profile_picture_presigned_url", new_callable=AsyncMock
)
async def test_get_my_client_profile_picture_url_none(
    mock_get_url: AsyncMock,
    mock_current_client_user: User,
    async_client: AsyncClient,
    override_get_db: None,
) -> None:
    """Test getting profile picture URL when none is set."""
    mock_get_url.return_value = None

    response = await async_client.get("/client/profile/picture-url")

    assert response.status_code == status.HTTP_200_OK
    assert response.content == b"null"
    mock_get_url.assert_awaited_once_with(mock_current_client_user.id)


# Favorite Workers Endpoints (listing, adding, removing)


@pytest.mark.asyncio
@patch.object(client_services.ClientService, "list_favorites", new_callable=AsyncMock)
async def test_list_my_favorite_workers(
    mock_list_favorites: AsyncMock,
    fake_favorite_read: client_schemas.FavoriteRead,
    mock_current_client_user: User,
    async_client: AsyncClient,
    override_get_db: None,
) -> None:
    """Test listing favorite workers for a client."""
    favorites_list = [
        fake_favorite_read,
        client_schemas.FavoriteRead(
            id=uuid4(),
            worker_id=uuid4(),
            client_id=mock_current_client_user.id,
            created_at=datetime.now(timezone.utc),
        ),
    ]
    total_count = 20
    mock_list_favorites.return_value = (favorites_list, total_count)

    response = await async_client.get("/client/favorites?skip=0&limit=10")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total_count"] == total_count
    assert len(data["items"]) == len(favorites_list)
    mock_list_favorites.assert_awaited_once_with(mock_current_client_user.id, skip=0, limit=10)


@pytest.mark.asyncio
@patch.object(client_services.ClientService, "add_favorite", new_callable=AsyncMock)
async def test_add_my_favorite_worker(
    mock_add_favorite: AsyncMock,
    fake_favorite_read: client_schemas.FavoriteRead,
    mock_current_client_user: User,
    async_client: AsyncClient,
    override_get_db: None,
) -> None:
    """Test adding a favorite worker."""
    test_worker_id = fake_favorite_read.worker_id
    mock_add_favorite.return_value = MagicMock(
        spec=FavoriteWorker, **fake_favorite_read.model_dump()
    )

    response = await async_client.post(f"/client/favorites/{test_worker_id}")

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["worker_id"] == str(test_worker_id)
    mock_add_favorite.assert_awaited_once_with(mock_current_client_user.id, test_worker_id)


@pytest.mark.asyncio
@patch.object(client_services.ClientService, "remove_favorite", new_callable=AsyncMock)
async def test_remove_my_favorite_worker(
    mock_remove_favorite: AsyncMock,
    mock_current_client_user: User,
    async_client: AsyncClient,
    override_get_db: None,
) -> None:
    """Test removing a favorite worker."""
    worker_id = uuid4()
    mock_remove_favorite.return_value = None

    response = await async_client.delete(f"/client/favorites/{worker_id}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["detail"] == "Favorite worker removed successfully."
    mock_remove_favorite.assert_awaited_once_with(mock_current_client_user.id, worker_id)


@pytest.mark.asyncio
@patch.object(client_services.ClientService, "remove_favorite", new_callable=AsyncMock)
async def test_remove_my_favorite_worker_not_found(
    mock_remove_favorite: AsyncMock,
    mock_current_client_user: User,
    async_client: AsyncClient,
    override_get_db: None,
) -> None:
    """Test removing a non-existent favorite worker."""
    worker_id = uuid4()
    mock_remove_favorite.side_effect = HTTPException(status_code=404, detail="Favorite not found.")

    response = await async_client.delete(f"/client/favorites/{worker_id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Favorite not found."
    mock_remove_favorite.assert_awaited_once_with(mock_current_client_user.id, worker_id)


# Client Job History Endpoints


@pytest.mark.asyncio
@patch.object(client_services.ClientService, "get_jobs", new_callable=AsyncMock)
async def test_list_my_client_jobs(
    mock_get_jobs: AsyncMock,
    mock_current_client_user: User,
    async_client: AsyncClient,
    override_get_db: None,
) -> None:
    """Test listing client's jobs."""
    jobs_list = [create_fake_job(mock_current_client_user.id, uuid4()) for _ in range(2)]
    total_count = 15
    mock_get_jobs.return_value = (jobs_list, total_count)

    response = await async_client.get("/client/jobs?skip=5&limit=5")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total_count"] == total_count
    assert len(data["items"]) == len(jobs_list)
    mock_get_jobs.assert_awaited_once_with(mock_current_client_user.id, skip=5, limit=5)


@pytest.mark.asyncio
@patch.object(client_services.ClientService, "get_job_detail", new_callable=AsyncMock)
async def test_get_my_client_job_detail(
    mock_get_job_detail: AsyncMock,
    mock_current_client_user: User,
    async_client: AsyncClient,
    override_get_db: None,
) -> None:
    """Test retrieving a specific client's job detail."""
    job_id = uuid4()
    fake_job_model = create_fake_job(mock_current_client_user.id, uuid4())
    fake_job_model.id = job_id
    mock_get_job_detail.return_value = fake_job_model

    response = await async_client.get(f"/client/jobs/{job_id}")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == str(job_id)
    assert data["status"] == fake_job_model.status.value
    mock_get_job_detail.assert_awaited_once_with(mock_current_client_user.id, job_id)


@pytest.mark.asyncio
@patch.object(client_services.ClientService, "get_job_detail", new_callable=AsyncMock)
async def test_get_my_client_job_detail_not_found(
    mock_get_job_detail: AsyncMock,
    mock_current_client_user: User,
    async_client: AsyncClient,
    override_get_db: None,
) -> None:
    """Test retrieving a job detail when not found."""
    job_id = uuid4()
    mock_get_job_detail.side_effect = HTTPException(
        status_code=404, detail="Job not found or unauthorized"
    )

    response = await async_client.get(f"/client/jobs/{job_id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Job not found or unauthorized"
    mock_get_job_detail.assert_awaited_once_with(mock_current_client_user.id, job_id)
