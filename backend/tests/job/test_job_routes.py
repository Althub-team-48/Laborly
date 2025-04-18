import pytest
from httpx import AsyncClient
from httpx._transports.asgi import ASGITransport
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from fastapi import status, HTTPException
from datetime import datetime, timezone

from main import app
from app.job.schemas import JobRead
from app.job.services import JobService

# ---------------------------
# Create Job
# ---------------------------
@patch.object(JobService, "create_job", new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_create_job_success(mock_create_job, fake_job_read, override_current_user, override_get_db, transport):
    mock_create_job.return_value = fake_job_read
    payload = {
        "worker_id": str(uuid4()),
        "service_id": str(uuid4()),
        "thread_id": str(uuid4())
    }
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/jobs/create", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["id"] == str(fake_job_read.id)


# ---------------------------
# Accept Job
# ---------------------------
@patch.object(JobService, "accept_job", new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_accept_job_success(mock_accept_job, fake_job_read, override_current_user, override_get_db, transport):
    mock_accept_job.return_value = fake_job_read
    payload = {
        "job_id": str(uuid4())
    }
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/jobs/accept", json=payload)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == fake_job_read.status


# ---------------------------
# Complete Job
# ---------------------------
@patch.object(JobService, "complete_job", new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_complete_job_success(mock_complete_job, fake_job_read, override_current_user, override_get_db, transport):
    mock_complete_job.return_value = fake_job_read
    job_id = uuid4()
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.put(f"/jobs/{job_id}/complete")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == fake_job_read.status


# ---------------------------
# Cancel Job
# ---------------------------
@patch.object(JobService, "cancel_job", new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_cancel_job_success(mock_cancel_job, fake_job_read, override_current_user, override_get_db, transport):
    mock_cancel_job.return_value = fake_job_read
    job_id = uuid4()
    payload = {"cancel_reason": "Client unavailable"}
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.put(f"/jobs/{job_id}/cancel", json=payload)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == fake_job_read.status


# ---------------------------
# List Jobs for User
# ---------------------------
@patch.object(JobService, "get_all_jobs_for_user", new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_get_jobs_for_user(mock_get_jobs, fake_job_read, override_current_user, override_get_db, transport):
    mock_get_jobs.return_value = [fake_job_read]
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/jobs")
    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.json(), list)


# ---------------------------
# Get Job Detail
# ---------------------------
@patch.object(JobService, "get_job_detail", new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_get_job_detail_success(mock_get_detail, fake_job_read, override_current_user, override_get_db, transport):
    mock_get_detail.return_value = fake_job_read
    job_id = uuid4()
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/jobs/{job_id}")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == str(fake_job_read.id)


# ---------------------------
# Error Handling (404)
# ---------------------------
@patch.object(JobService, "get_job_detail", new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_get_job_detail_not_found(mock_get_detail, override_current_user, override_get_db, transport):
    mock_get_detail.side_effect = HTTPException(status_code=404, detail="Job not found")
    job_id = uuid4()
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/jobs/{job_id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Job not found"
