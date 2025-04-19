import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from fastapi import status, HTTPException
from main import app
from app.service.services import ServiceListingService

# ---------------------------
# Create Service
# ---------------------------
@patch.object(ServiceListingService, "create_service", new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_create_service(mock_create_service, fake_service_read, override_worker_admin_user, override_get_db, async_client ):
    mock_create_service.return_value = fake_service_read
    payload = {
        "title": "plumbing",
        "description": "Everything related to plumbing",
        "location": "Magodo"
    }
  
    async with async_client as ac:
        response = await ac.post("/services",json=payload)
    
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["title"] == fake_service_read.title     