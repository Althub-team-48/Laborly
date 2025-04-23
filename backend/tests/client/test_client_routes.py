import pytest
from uuid import uuid4
from datetime import datetime, timezone
from unittest.mock import patch, AsyncMock
from fastapi import HTTPException

from app.client.schemas import ClientProfileRead, ClientProfileUpdate, FavoriteRead, ClientJobRead
from app.client.services import ClientService

# ----------------------------
# Client Profile
# ----------------------------


@patch.object(ClientService, 'get_profile', new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_get_client_profile(mock_get_profile, override_client_user, async_client):
    fake_response = ClientProfileRead(
        id=uuid4(),
        user_id=uuid4(),
        email="client@yahoo.com",
        phone_number="+23480000000",
        first_name="john",
        last_name="Doe",
        location="ibadan",
        profile_picture="cat image",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    mock_get_profile.return_value = fake_response
    async with async_client as ac:
        response = await ac.get("/client/get/profile")
    data = response.json()
    assert response.status_code == 200
    assert data["email"] == fake_response.email
    assert data["first_name"] == fake_response.first_name


@patch.object(ClientService, 'update_profile', new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_update_client_profile(mock_update_profile, override_client_user, async_client):
    update_data = ClientProfileUpdate(
        email="client@yahoo.com",
        phone_number="+23480000000",
        first_name="john",
        last_name="Doe",
        location="lagos",
        profile_picture="dogimage",
    )
    fake_response = ClientProfileRead(
        id=uuid4(),
        user_id=uuid4(),
        email="client@yahoo.com",
        phone_number="+23480000000",
        first_name="john",
        last_name="Doe",
        location="lagos",
        profile_picture="dogimage",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    mock_update_profile.return_value = fake_response
    async with async_client as ac:
        response = await ac.patch("/client/update/profile", json=update_data.model_dump())
    data = response.json()
    assert response.status_code == 200
    assert data["location"] == update_data.location
    assert data["profile_picture"] == update_data.profile_picture


# ----------------------------
# Favorite Workers
# ----------------------------


@patch.object(ClientService, 'list_favorites', new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_list_favorite_workers(mock_list_favorites, override_client_user, async_client):
    favorites = [
        FavoriteRead(
            id=uuid4(), worker_id=uuid4(), client_id=uuid4(), created_at=datetime.now(timezone.utc)
        ),
        FavoriteRead(
            id=uuid4(), worker_id=uuid4(), client_id=uuid4(), created_at=datetime.now(timezone.utc)
        ),
    ]
    mock_list_favorites.return_value = favorites
    async with async_client as ac:
        response = await ac.get("/client/get/favorites")
    data = response.json()
    assert response.status_code == 200
    assert isinstance(data, list)
    assert len(data) == 2


@patch.object(ClientService, 'add_favorite', new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_add_favorite_worker(mock_add_favorite, override_client_user, async_client):
    test_worker_id = uuid4()
    fake_response = FavoriteRead(
        id=uuid4(),
        worker_id=test_worker_id,
        client_id=uuid4(),
        created_at=datetime.now(timezone.utc),
    )
    mock_add_favorite.return_value = fake_response
    async with async_client as ac:
        response = await ac.post(f"/client/add/favorites/{test_worker_id}")
    data = response.json()
    assert response.status_code == 201
    assert data["worker_id"] == str(fake_response.worker_id)


@patch.object(ClientService, 'remove_favorite', new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_remove_favorite_worker(mock_remove_favorite, override_client_user, async_client):
    worker_id = uuid4()
    mock_remove_favorite.side_effect = [
        None,
        HTTPException(status_code=404, detail="Favorite not found"),
    ]
    async with async_client as ac:
        res1 = await ac.delete(f"/client/delete/favorites/{worker_id}")
        assert res1.status_code == 204
        res2 = await ac.delete(f"/client/delete/favorites/{worker_id}")
        assert res2.status_code == 404
        assert res2.json()["detail"] == "Favorite not found"


# ----------------------------
# Job History
# ----------------------------


@patch.object(ClientService, 'get_jobs', new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_list_client_jobs(mock_get_jobs, override_client_user, async_client):
    jobs = [
        ClientJobRead(
            id=uuid4(),
            service_id=uuid4(),
            worker_id=uuid4(),
            status="completed",
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        ),
        ClientJobRead(
            id=uuid4(),
            service_id=uuid4(),
            worker_id=uuid4(),
            status="cancelled",
            started_at=datetime.now(timezone.utc),
            cancelled_at=datetime.now(timezone.utc),
            cancel_reason="exorbitant pricing",
        ),
    ]
    mock_get_jobs.return_value = jobs
    async with async_client as ac:
        response = await ac.get("/client/list/jobs")
    data = response.json()
    assert response.status_code == 200
    assert len(data) == 2
    assert data[1]["cancel_reason"] == jobs[1].cancel_reason


@patch.object(ClientService, 'get_job_detail', new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_get_client_job_detail(
    mock_get_job_detail, fake_client_job_read, override_client_user, async_client
):
    job_id = uuid4()
    mock_get_job_detail.return_value = fake_client_job_read
    async with async_client as ac:
        response = await ac.get(f"/client/get/jobs/{job_id}")
    data = response.json()
    assert response.status_code == 200
    assert data["id"] == str(fake_client_job_read.id)
    assert data["status"] == fake_client_job_read.status


# ---------------------------
# Error Handling
# ---------------------------
@patch.object(ClientService, 'get_job_detail', new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_get_client_job_detail_failed(
    mock_get_job_detail, fake_client_job_read, override_client_user, async_client
):
    job_id = uuid4()
    mock_get_job_detail.side_effect = HTTPException(status_code=404, detail="unauthorized access")
    async with async_client as ac:
        response = await ac.get(f"/client/get/jobs/{job_id}")
    data = response.json()
    assert response.status_code == 404
    assert data["detail"] == "unauthorized access"
