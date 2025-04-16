
"""

client test file. This tests all the endpoints in the client router:
- Profile management
- Favorite worker handling
- Client job history and job details
"""

from datetime import datetime, timezone
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from app.database.enums import UserRole
from backend.app.core.dependencies import get_db
from main import *
from app.client.routes import client_user_dependency
from app.client.services import *
from app.client.schemas import *
from httpx import AsyncClient, ASGITransport
from uuid import uuid4
import pytest
import pytest_asyncio


client = TestClient(app)


# ---------------------------
# Test the get_client_profile endpoint
# ---------------------------  
 

@pytest.mark.asyncio
@patch.object(ClientService, 'get_profile', new_callable=AsyncMock)
async def test_get_client_profile(mock_get_profile):
    """Mock Data"""
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
        updated_at=datetime.now(timezone.utc)
    )    

    mock_get_profile.return_value =  fake_response
    """Override the client/admin_user_dependency to return a fake client/admin"""
    async def override_require_roles():
        class FakeClient:
            id = uuid4()
            role = UserRole.CLIENT
        return FakeClient()

    app.dependency_overrides[client_user_dependency] = override_require_roles

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:  
        response = await ac.get("/client/get/profile")

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == fake_response.email
    assert data["phone_number"] == fake_response.phone_number
    assert data["first_name"] == fake_response.first_name
    assert data["last_name"] == fake_response.last_name
    assert data["location"] == fake_response.location
    assert data["profile_picture"] == fake_response.profile_picture
    assert data["user_id"] == str(fake_response.user_id)
    assert data["id"] == str(fake_response.id)
    assert "created_at" in data
    assert "updated_at" in data

    """Clean up overrides after the test"""
    app.dependency_overrides = {}

# ---------------------------
# Test the get_update_profile endpoint
# ---------------------------  
 

@pytest.mark.asyncio
@patch.object(ClientService, 'update_profile', new_callable=AsyncMock)
async def test_update_client_profile(mock_update_profile):
    """Mock Data"""
    fake_profile_update = ClientProfileUpdate(
        email="client@yahoo.com",
        phone_number="+23480000000",
        first_name="john",
        last_name="Doe",
        location="lagos",
        profile_picture="dogimage"
    )
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
        updated_at=datetime.now(timezone.utc)
    )    

    mock_update_profile.return_value =  fake_response
    """Override the client/admin_user_dependency to return a fake client/admin"""
    async def override_require_roles():
        class FakeClient:
            id = uuid4()
            role = UserRole.CLIENT
        return FakeClient()

    app.dependency_overrides[client_user_dependency] = override_require_roles

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:  
        response = await ac.patch("/client/update/profile", json=fake_profile_update.model_dump())

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == fake_response.email
    assert data["phone_number"] == fake_response.phone_number
    assert data["first_name"] == fake_response.first_name
    assert data["last_name"] == fake_response.last_name
    assert data["location"] == fake_response.location
    assert data["profile_picture"] == fake_response.profile_picture
    assert data["user_id"] == str(fake_response.user_id)
    assert data["id"] == str(fake_response.id)
    assert "created_at" in data
    assert "updated_at" in data

    """Clean up overrides after the test"""
    app.dependency_overrides.clear()


# ---------------------------
# Test the list_favorite_workers endpoint
# ---------------------------  
 

@pytest.mark.asyncio
@patch.object(ClientService, 'list_favorites', new_callable=AsyncMock)
async def test_list_favorite_workers(mock_list_favorites):
    """Mock Data"""
    favorite_1 = FavoriteRead(
        id=uuid4(),
        worker_id=uuid4(),
        client_id=uuid4(),
        created_at=datetime.now(timezone.utc)
    )
    favorite_2 = FavoriteRead(
        id=uuid4(),
        worker_id=uuid4(),
        client_id=uuid4(),
        created_at=datetime.now(timezone.utc)
    )
    fake_response = [favorite_1, favorite_2]

    mock_list_favorites.return_value =  fake_response
    """Override the client/admin_user_dependency to return a fake client/admin"""
    async def override_require_roles():
        class FakeClient:
            id = uuid4()
            role = UserRole.CLIENT
        return FakeClient()

    app.dependency_overrides[client_user_dependency] = override_require_roles

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:  
        response = await ac.get("/client/get/favorites")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]["id"] == str(favorite_1.id)
    assert data[0]["worker_id"] == str(favorite_1.worker_id)
    assert data[0]["client_id"] == str(favorite_1.client_id)
    assert "created_at" in data[0]
    assert data[0]["created_at"] is not None

    assert data[1]["id"] == str(favorite_2.id)
    assert data[1]["worker_id"] == str(favorite_2.worker_id)
    assert data[1]["client_id"] == str(favorite_2.client_id)
    assert "created_at" in data[1]
    assert data[1]["created_at"] is not None
   
    """Clean up overrides after the test"""
    app.dependency_overrides.clear()

# ---------------------------
# Test the add_favorite_workers endpoint
# ---------------------------      

@pytest.mark.asyncio
@patch.object(ClientService, 'add_favorite', new_callable=AsyncMock)
async def test_add_favorite_worker(mock_add_favorite):
    """Mock Data"""
    test_worker_id=uuid4()
    fake_response = FavoriteRead(
        id=uuid4(),
        worker_id=test_worker_id,
        client_id=uuid4(),
        created_at=datetime.now(timezone.utc)
    )
     
    mock_add_favorite.return_value =  fake_response

    """Override the client/admin_user_dependency to return a fake client/admin"""
    async def override_require_roles():
        class FakeClient:
            id = uuid4()
            role = UserRole.CLIENT
        return FakeClient()

    app.dependency_overrides[client_user_dependency] = override_require_roles

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:  
        response = await ac.post(f"/client/add/favorites/{test_worker_id}")

    assert response.status_code == 201

    data = response.json()

    assert data["id"] == str(fake_response.id)
    assert data["worker_id"] == str(fake_response.worker_id)
    assert data["client_id"] == str(fake_response.client_id)
    assert "created_at" in data
    assert data["created_at"] is not None

    """Clean up overrides after the test"""
    app.dependency_overrides = {}


# ---------------------------
# Test the remove_favorite_worker endpoint
# ---------------------------        

@pytest.mark.asyncio
@patch.object(ClientService, 'remove_favorite', new_callable=AsyncMock)
async def test_remove_favorite_worker(mock_remove_favorite):
    """Mock Data"""
    test_worker_id=uuid4()
    
    """First call returns success, second raises 404"""
    mock_remove_favorite.side_effect = [
        None,  # First call: review deleted
        HTTPException(status_code=404, detail="Favorite not found")  # Second call to test that a deleted user: not found
    ]

    """Override the client/admin_user_dependency to return a fake client/admin"""
    async def override_require_roles():
        class FakeClient:
            id = uuid4()
            role = UserRole.CLIENT
        return FakeClient()

    app.dependency_overrides[client_user_dependency] = override_require_roles

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:  

    # First delete
        response1 = await ac.delete(f"/client/delete/favorites/{test_worker_id}")
        assert response1.status_code == 204
      

        # Second delete
        response2 = await ac.delete(f"/client/delete/favorites/{test_worker_id}")
        assert response2.status_code == 404
        assert response2.json()["detail"] == "Favorite not found"

    # Clean up overrides after the test
    app.dependency_overrides = {} 

# ---------------------------
# Test the list_client_jobs endpoint
# ---------------------------  
 

@pytest.mark.asyncio
@patch.object(ClientService, 'get_jobs', new_callable=AsyncMock)
async def test_list_client_jobs(mock_get_jobs):
    """Mock Data"""
    job_1 = ClientJobRead(
        id=uuid4(),
        service_id=uuid4(),
        worker_id=uuid4(),
        status="completed",
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc)

    )
    job_2 = ClientJobRead(
        id=uuid4(),
        service_id=uuid4(),
        worker_id=uuid4(),
        status="cancelled",
        started_at=datetime.now(timezone.utc),
        cancelled_at=datetime.now(timezone.utc),
        cancel_reason="exorbitant pricing"
    )
    fake_response = [job_1, job_2]

    mock_get_jobs.return_value =  fake_response

    """Override the client/admin_user_dependency to return a fake client/admin"""
    async def override_require_roles():
        class FakeClient:
            id = uuid4()
            role = UserRole.CLIENT
        return FakeClient()

    app.dependency_overrides[client_user_dependency] = override_require_roles

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:  
        response = await ac.get("/client/list/jobs")

    assert response.status_code == 200
    data = response.json()

    assert isinstance(data, list)
    assert len(data) == 2

    # Assertions for job_1 (completed)
    assert data[0]["id"] == str(job_1.id)
    assert data[0]["service_id"] == str(job_1.service_id)
    assert data[0]["worker_id"] == str(job_1.worker_id)
    assert data[0]["status"] == job_1.status
    assert data[0]["started_at"] is not None
    assert data[0]["completed_at"] is not None
    

    # Assertions for job_2 (cancelled)
    assert data[1]["id"] == str(job_2.id)
    assert data[1]["service_id"] == str(job_2.service_id)
    assert data[1]["worker_id"] == str(job_2.worker_id)
    assert data[1]["status"] == job_2.status
    assert data[1]["started_at"] is not None
    assert data[1]["cancelled_at"] is not None
    assert data[1]["cancel_reason"] == job_2.cancel_reason
    

    """Clean up overrides after the test"""
    app.dependency_overrides.clear()    

# ---------------------------
# Test the list_client_jobs endpoint
# ---------------------------  
 

@pytest.mark.asyncio
@patch.object(ClientService, 'get_jobs', new_callable=AsyncMock)
async def test_list_client_jobs(mock_get_jobs):
    """Mock Data"""
    job_1 = ClientJobRead(
        id=uuid4(),
        service_id=uuid4(),
        worker_id=uuid4(),
        status="completed",
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc)

    )
    job_2 = ClientJobRead(
        id=uuid4(),
        service_id=uuid4(),
        worker_id=uuid4(),
        status="cancelled",
        started_at=datetime.now(timezone.utc),
        cancelled_at=datetime.now(timezone.utc),
        cancel_reason="exorbitant pricing"
    )
    fake_response = [job_1, job_2]

    mock_get_jobs.return_value =  fake_response

    """Override the client/admin_user_dependency to return a fake client/admin"""
    async def override_require_roles():
        class FakeClient:
            id = uuid4()
            role = UserRole.CLIENT
        return FakeClient()

    app.dependency_overrides[client_user_dependency] = override_require_roles

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:  
        response = await ac.get("/client/list/jobs")

    assert response.status_code == 200
    data = response.json()

    assert isinstance(data, list)
    assert len(data) == 2

    # Assertions for job_1 (completed)
    assert data[0]["id"] == str(job_1.id)
    assert data[0]["service_id"] == str(job_1.service_id)
    assert data[0]["worker_id"] == str(job_1.worker_id)
    assert data[0]["status"] == job_1.status
    assert data[0]["started_at"] is not None
    assert data[0]["completed_at"] is not None
    

    # Assertions for job_2 (cancelled)
    assert data[1]["id"] == str(job_2.id)
    assert data[1]["service_id"] == str(job_2.service_id)
    assert data[1]["worker_id"] == str(job_2.worker_id)
    assert data[1]["status"] == job_2.status
    assert data[1]["started_at"] is not None
    assert data[1]["cancelled_at"] is not None
    assert data[1]["cancel_reason"] == job_2.cancel_reason
    

    """Clean up overrides after the test"""
    app.dependency_overrides.clear()

# ---------------------------
# Test the get_client_job_detail
# ---------------------------  
 

@pytest.mark.asyncio
@patch.object(ClientService, 'get_job_detail', new_callable=AsyncMock)
async def test_get_client_job_detail(mock_get_job_detail):
    """Mock Data"""
    test_job_id=uuid4()
    fake_response = ClientJobRead(
        id=test_job_id,
        service_id=uuid4(),
        worker_id=uuid4(),
        status="completed",
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc)
    )    

    mock_get_job_detail.return_value =  fake_response

    """Override the client/admin_user_dependency to return a fake client/admin"""
    async def override_require_roles():
        class FakeClient:
            id = uuid4()
            role = UserRole.CLIENT
        return FakeClient()

    app.dependency_overrides[client_user_dependency] = override_require_roles

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:  
        response = await ac.get(f"/client/get/jobs/{test_job_id}")

    assert response.status_code == 200
    data = response.json()

    assert data["id"] == str(fake_response.id)
    assert data["service_id"] == str(fake_response.service_id)
    assert data["worker_id"] == str(fake_response.worker_id)
    assert data["status"] == fake_response.status
    assert data["started_at"] is not None
    assert data["completed_at"] is not None

    """Clean up overrides after the test"""
    app.dependency_overrides.clear()        



  



        


           
       

       
    