from datetime import datetime, timezone
from io import BytesIO
import pprint
import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from fastapi import status, HTTPException
from main import app
from app.worker.services import WorkerService

# ---------------------------
# Profile Endpoints
# ---------------------------
@patch.object(WorkerService, "get_profile", new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_get_worker_profile(mock_get_profile, fake_worker_profile_read, override_worker_admin_user, async_client):
    mock_get_profile.return_value = fake_worker_profile_read
    
    async with async_client as ac:
        response = await ac.get("/worker/profile")
    
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == str(fake_worker_profile_read.id)

    
@patch.object(WorkerService, "update_profile", new_callable=AsyncMock)
@pytest.mark.asyncio
async def update_worker_profile(mock_update_profile, fake_worker_profile_read, override_worker_admin_user, async_client):
    mock_update_profile.return_value = fake_worker_profile_read 
    payload = {
        "is_available" : True
    }
    async with async_client as ac:
        response = await ac.patch("/worker/profile", json = payload)
    
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["is_available"] == fake_worker_profile_read.is_available   

# ---------------------------
# KYC Endpoints
# ---------------------------
@patch.object(WorkerService, "get_kyc", new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_get_worker_kyc(mock_get_kyc, override_worker_admin_user, async_client):
    mock_get_kyc.return_value = {
        "status": "approved",
        "submitted_at": str(datetime.now(timezone.utc))
    }
    async with async_client as ac:
        response = await ac.get("/worker/kyc")
    
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "approved"
    assert "submitted_at" in response.json()

@patch("app.worker.routes.upload_file_to_s3")
@patch.object(WorkerService, "submit_kyc", new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_submit_worker_kyc(
    mock_submit_kyc,
    mock_upload_to_s3,
    override_worker_admin_user,
    async_client
):
    """ Mock file upload path"""
    mock_upload_to_s3.side_effect = [
        "s3://bucket/kyc/document.pdf",
        "s3://bucket/kyc/selfie.jpg"
    ]

    """ Mock return value of service method"""
    mock_submit_kyc.return_value = {
        "status": "submitted",
        "submitted_at": "2025-04-20T14:33:12.123456+00:00"
    }

    """Create fake file-like content"""
    files = {
        "document_type": (None, "passport"),
        "document_file": ("document.pdf", BytesIO(b"fake-pdf-content"), "application/pdf"),
        "selfie_file": ("selfie.jpg", BytesIO(b"fake-jpg-content"), "image/jpeg")
    }

    async with async_client as ac:
        response = await ac.post("/worker/kyc", files=files)

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["status"] == "submitted"
    assert "submitted_at" in response.json()

# ----------------------------------------------------
# Job History Endpoints
# ----------------------------------------------------   
@pytest.mark.asyncio
@patch.object(WorkerService, "get_jobs", new_callable=AsyncMock)
async def test_list_worker_jobs(mock_get_jobs, fake_job_read, override_worker_admin_user, async_client):
    mock_get_jobs.return_value = [fake_job_read]

    async with async_client as ac:
        response = await ac.get("/worker/jobs")

    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.json(), list)

@pytest.mark.asyncio
@patch.object(WorkerService, "get_jobs", new_callable=AsyncMock)
async def test_list_worker_job_details(mock_get_jobs, fake_job_read, override_worker_admin_user, async_client):
    mock_get_jobs.return_value = fake_job_read

    async with async_client as ac:
        response = await ac.get("/worker/jobs")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == str(fake_job_read.id)    
    

# ---------------------------
# Error Handling
# ---------------------------

@pytest.mark.asyncio
@patch.object(WorkerService, "get_jobs", new_callable=AsyncMock)
async def test_list_worker_job_details_failed(mock_get_jobs, fake_job_read, override_worker_admin_user, async_client):
    mock_get_jobs.side_effect = HTTPException(status_code=404, detail="unauthorized")

    async with async_client as ac:
        response = await ac.get("/worker/jobs")

    assert response.status_code == 404
    assert response.json()["detail"] == "unauthorized"    
    
        
    




