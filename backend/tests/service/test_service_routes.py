# tests/service/test_service_routes.py
import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
from fastapi import status, HTTPException

from app.service import schemas as service_schemas
from app.service import services as service_services
from app.service.models import Service  # Import model if needed
from app.database.models import User
from app.database.enums import UserRole

# --- Public Endpoints ---


@pytest.mark.asyncio
@patch.object(service_services.ServiceListingService, "search_services", new_callable=AsyncMock)
async def test_search_services(
    mock_search_services: AsyncMock,
    fake_service_read: service_schemas.ServiceRead,
    async_client: AsyncClient,
    override_get_db: None,
) -> None:
    services_list = [MagicMock(spec=Service, **fake_service_read.model_dump())]
    total_count = 1
    mock_search_services.return_value = (services_list, total_count)

    response = await async_client.get("/services/search?title=Test&location=Remote&skip=0&limit=10")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total_count"] == total_count
    assert len(data["items"]) == len(services_list)
    assert data["items"][0]["id"] == str(fake_service_read.id)
    # Check mock call signature
    mock_search_services.assert_awaited_once_with(title="Test", location="Remote", skip=0, limit=10)


@pytest.mark.asyncio
@patch.object(
    service_services.ServiceListingService, "get_public_service_detail", new_callable=AsyncMock
)
async def test_get_public_service_detail(
    mock_get_public_detail: AsyncMock,
    fake_service_read: service_schemas.ServiceRead,
    async_client: AsyncClient,
    override_get_db: None,
) -> None:
    service_id = fake_service_read.id
    mock_get_public_detail.return_value = MagicMock(spec=Service, **fake_service_read.model_dump())

    response = await async_client.get(f"/services/{service_id}/public")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == str(service_id)
    assert data["title"] == fake_service_read.title
    mock_get_public_detail.assert_awaited_once_with(service_id)


@pytest.mark.asyncio
@patch.object(
    service_services.ServiceListingService, "get_public_service_detail", new_callable=AsyncMock
)
async def test_get_public_service_detail_not_found(
    mock_get_public_detail: AsyncMock,
    async_client: AsyncClient,
    override_get_db: None,
) -> None:
    service_id = uuid4()
    mock_get_public_detail.side_effect = HTTPException(status_code=404, detail="Service not found")

    response = await async_client.get(f"/services/{service_id}/public")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Service not found"
    mock_get_public_detail.assert_awaited_once_with(service_id)


# --- Authenticated Endpoints (Worker/Admin) ---


@pytest.mark.asyncio
@patch.object(service_services.ServiceListingService, "create_service", new_callable=AsyncMock)
async def test_create_service_as_worker(
    mock_create_service: AsyncMock,
    fake_service_read: service_schemas.ServiceRead,
    mock_current_worker_user: User,  # Use worker user
    async_client: AsyncClient,
    override_get_db: None,
) -> None:
    fake_service_read.worker_id = mock_current_worker_user.id
    fake_service_read.title = "New Test Service"  # Match payload title
    mock_create_service.return_value = MagicMock(spec=Service, **fake_service_read.model_dump())

    payload_schema = service_schemas.ServiceCreate(
        title="New Test Service", description="Description for new service", location="Lagos"
    )
    payload = payload_schema.model_dump(mode='json')

    response = await async_client.post("/services", json=payload)

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["id"] == str(fake_service_read.id)
    assert data["worker_id"] == str(mock_current_worker_user.id)
    assert data["title"] == payload_schema.title
    # Check mock call signature
    mock_create_service.assert_awaited_once()
    call_args, call_kwargs = mock_create_service.call_args
    assert call_args[0] == mock_current_worker_user.id  # worker_id
    assert call_args[1].title == payload_schema.title  # payload


@pytest.mark.asyncio
@patch.object(service_services.ServiceListingService, "update_service", new_callable=AsyncMock)
async def test_update_service_as_admin(
    mock_update_service: AsyncMock,
    fake_service_read: service_schemas.ServiceRead,
    mock_current_admin_user: User,  # Use admin user
    async_client: AsyncClient,
    override_get_db: None,
) -> None:
    service_id = uuid4()
    fake_service_read.id = service_id
    fake_service_read.worker_id = mock_current_admin_user.id  # Route uses current_user.id
    fake_service_read.location = "Abuja"  # Simulate update
    mock_update_service.return_value = MagicMock(spec=Service, **fake_service_read.model_dump())

    # Include required 'title' field, can use the fixture's title
    payload_schema = service_schemas.ServiceUpdate(title=fake_service_read.title, location="Abuja")
    payload = payload_schema.model_dump(mode='json', exclude_unset=True)

    response = await async_client.put(f"/services/{service_id}", json=payload)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == str(service_id)
    assert data["location"] == "Abuja"
    # Check mock call signature
    mock_update_service.assert_awaited_once()
    call_args, call_kwargs = mock_update_service.call_args
    assert call_args[0] == mock_current_admin_user.id  # worker_id (current_user.id)
    assert call_args[1] == service_id  # service_id
    assert call_args[2].location == payload_schema.location  # payload


@pytest.mark.asyncio
@patch.object(service_services.ServiceListingService, "delete_service", new_callable=AsyncMock)
async def test_delete_service_as_worker(
    mock_delete_service: AsyncMock,
    mock_current_worker_user: User,  # Use worker user
    async_client: AsyncClient,
    override_get_db: None,
) -> None:
    service_id = uuid4()
    mock_delete_service.return_value = None

    response = await async_client.delete(f"/services/{service_id}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["detail"] == "Service deleted successfully"
    mock_delete_service.assert_awaited_once_with(mock_current_worker_user.id, service_id)


@pytest.mark.asyncio
@patch.object(service_services.ServiceListingService, "get_my_services", new_callable=AsyncMock)
async def test_list_my_services(
    mock_get_my_services: AsyncMock,
    fake_service_read: service_schemas.ServiceRead,
    mock_current_worker_user: User,  # Needs worker user
    async_client: AsyncClient,
    override_get_db: None,
) -> None:
    services_list = [MagicMock(spec=Service, **fake_service_read.model_dump())]
    total_count = 5
    mock_get_my_services.return_value = (services_list, total_count)

    response = await async_client.get("/services/my?limit=5")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total_count"] == total_count
    assert len(data["items"]) == len(services_list)
    assert data["items"][0]["id"] == str(fake_service_read.id)
    assert data["items"][0]["worker_id"] == str(mock_current_worker_user.id)
    # Check mock call signature
    mock_get_my_services.assert_awaited_once_with(mock_current_worker_user.id, skip=0, limit=5)


@pytest.mark.asyncio
@patch.object(service_services.ServiceListingService, "delete_service", new_callable=AsyncMock)
async def test_delete_service_not_found(
    mock_delete_service: AsyncMock,
    mock_current_worker_user: User,
    async_client: AsyncClient,
    override_get_db: None,
) -> None:
    service_id = uuid4()
    mock_delete_service.side_effect = HTTPException(
        status_code=404, detail="Service not found or unauthorized"
    )

    response = await async_client.delete(f"/services/{service_id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Service not found or unauthorized"
    mock_delete_service.assert_awaited_once_with(mock_current_worker_user.id, service_id)


@pytest.mark.asyncio
@patch.object(service_services.ServiceListingService, "update_service", new_callable=AsyncMock)
async def test_update_service_forbidden(
    mock_update_service: AsyncMock,
    mock_current_client_user: User,  # Use client user (invalid role)
    async_client: AsyncClient,
    override_get_db: None,
) -> None:
    service_id = uuid4()
    # The dependency check should raise 403 before the service is called
    # So, we don't need to mock the service method itself for this test case

    # Include required 'title' field
    payload = service_schemas.ServiceUpdate(
        title="Any Valid Title", location="Abuja"  # Title is needed for validation
    ).model_dump(mode='json')

    response = await async_client.put(f"/services/{service_id}", json=payload)

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["detail"] == f"Access denied for role: {UserRole.CLIENT}"
