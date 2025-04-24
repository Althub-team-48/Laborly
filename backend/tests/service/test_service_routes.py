# import pprint
# import pytest
# from unittest.mock import AsyncMock, patch
# from uuid import uuid4
# from fastapi import status, HTTPException
# from main import app
# from app.service.services import ServiceListingService

# # ---------------------------
# # Create Service
# # ---------------------------
# @patch.object(ServiceListingService, "create_service", new_callable=AsyncMock)
# @pytest.mark.asyncio
# async def test_create_service(mock_create_service, fake_service_read, override_worker_admin_user, async_client):
#     mock_create_service.return_value = fake_service_read
#     payload = {
#         "title": "plumbing",
#         "description": "Everything related to plumbing",
#         "location": "Magodo"
#     }

#     async with async_client as ac:
#         response = await ac.post("/services",json=payload)

#     assert response.status_code == status.HTTP_201_CREATED
#     assert response.json()["title"] == fake_service_read.title

# # ---------------------------
# # Update Service
# # ---------------------------
# @patch.object(ServiceListingService, "update_service", new_callable=AsyncMock)
# @pytest.mark.asyncio
# async def test_update_service(mock_update_service, fake_service_read, override_worker_admin_user, async_client):
#     service_id=uuid4()
#     mock_update_service.return_value = fake_service_read
#     payload = {
#         "title": "plumbing",
#         "description": "Everything related to plumbing",
#         "location": "Magodo"
#     }

#     async with async_client as ac:
#         response = await ac.put(f"/services/{service_id}",json=payload)

#     assert response.status_code == status.HTTP_200_OK
#     assert response.json()["id"] == str(fake_service_read.id)


# # ---------------------------
# # Delete Service
# # ---------------------------
# @patch.object(ServiceListingService, "delete_service", new_callable=AsyncMock)
# @pytest.mark.asyncio
# async def test_delete_service(mock_delete_service, override_worker_admin_user, async_client):
#     service_id=(uuid4())
#     mock_delete_service.return_value = None
#     async with async_client as ac:
#         response = await ac.delete(f"/services/{service_id}")

#     assert response.status_code == status.HTTP_200_OK
#     assert response.json()["detail"] == "Service deleted successfully"


# # ---------------------------
# # List My Services
# # ---------------------------
# @patch.object(ServiceListingService, "get_my_services", new_callable=AsyncMock)
# @pytest.mark.asyncio
# async def test_list_my_services(mock_get_my_services, fake_service_read, override_worker_admin_user, async_client):
#     mock_get_my_services.return_value = [fake_service_read]
#     async with async_client as ac:
#         response = await ac.get(f"/services/my")

#     assert response.status_code == status.HTTP_200_OK
#     assert isinstance (response.json(), list)

# # ---------------------------
# # Search Public Services
# # ---------------------------
# @patch.object(ServiceListingService, "search_services", new_callable=AsyncMock)
# @pytest.mark.asyncio
# async def test_search_services(mock_search_services, fake_service_read, override_worker_admin_user, async_client):
#     mock_search_services.return_value = [fake_service_read]
#     async with async_client as ac:
#         response = await ac.get("/services/search")

#     assert response.status_code == status.HTTP_200_OK
#     assert isinstance (response.json(), list)

# # ---------------------------
# # Error Handling
# # ---------------------------
# @patch.object(ServiceListingService, "delete_service", new_callable=AsyncMock)
# @pytest.mark.asyncio
# async def test_delete_service_failed(mock_delete_service, override_worker_admin_user, async_client):
#     service_id=(uuid4())
#     mock_delete_service.side_effect = HTTPException(status_code=404, detail="Service not found")
#     async with async_client as ac:
#         response = await ac.delete(f"/services/{service_id}")

#     assert response.status_code == 404
#     assert response.json()["detail"] == "Service not found"

# @patch.object(ServiceListingService, "update_service", new_callable=AsyncMock)
# @pytest.mark.asyncio
# async def test_update_service_failed(mock_update_service, fake_service_read, override_worker_admin_user, async_client):
#     service_id=(uuid4())
#     mock_update_service.side_effect = HTTPException(status_code=404, detail="unauthorized")
#     payload = {
#         "title": "plumbing",
#         "description": "Everything related to plumbing",
#         "location": "Magodo"
#     }

#     async with async_client as ac:
#         response = await ac.put(f"/services/{service_id}",json=payload)

#     assert response.status_code == 404
#     assert response.json()["detail"] == "unauthorized"
