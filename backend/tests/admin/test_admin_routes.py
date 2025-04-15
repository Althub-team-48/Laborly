"""
tests/test_kyc.py

Admin test file. This tests all the endpoints in the admin router:
1. endpoint for retrieving pending KYC submissions.
2. endpoint for approving KYC submissions
3. endpoint for rejecting KYC submissions
4. endpoint for Freezing, unfreezing, banning, unbanning, and deleting users
5. endpoint for Reviewing and moderating flagged reviews
"""

from datetime import datetime, timezone
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from app.database.enums import UserRole
from backend.app.core.dependencies import get_db
from main import *
from app.admin.routes import admin_user_dependency
from app.admin.services import *
from app.admin.schemas import FlaggedReviewRead, KYCReviewResponse,UserStatusUpdateResponse
from httpx import AsyncClient, ASGITransport
from uuid import uuid4
import pytest
import pytest_asyncio


client = TestClient(app)

# ---------------------------
# Test for get_pending_kyc_list
# --------------------------- 

@pytest.mark.asyncio
@patch.object(AdminService, 'list_pending_kyc', new_callable=AsyncMock)
async def test_get_pending_kyc_list(mock_list_pending_kyc):
    # --- Mock Data ---
    fake_kyc_response = [
        KYCReviewResponse(
            user_id=uuid4(),
            status="pending",
            reviewed_at=datetime.now(timezone.utc)
        )
]
    mock_list_pending_kyc.return_value = fake_kyc_response
    # Override the admin_user_dependency to return a fake admin
    async def override_get_current_user():
        class FakeAdminUser:
            id = uuid4()
            role = UserRole.ADMIN
        return FakeAdminUser()

    app.dependency_overrides[admin_user_dependency] = override_get_current_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:  
        response = await ac.get("/admin/kyc/pending")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert "user_id" in data[0]
    assert "status" in data[0]
    assert "reviewed_at" in data[0]

    # Clean up overrides after the test
    app.dependency_overrides = {}


# ---------------------------
# Test for approve_user_kyc
# ---------------------------  

@pytest.mark.asyncio
@patch.object(AdminService, 'approve_kyc', new_callable=AsyncMock)
async def test_approve_user_kyc_success(mock_approve_kyc):
     # Create a fake user ID and response
    test_user_id = uuid4()
    fake_response = KYCReviewResponse(
        user_id=test_user_id,
        status="approved",
        reviewed_at=datetime.now(timezone.utc)
    )

    mock_approve_kyc.return_value = fake_response

    # Override the admin_user_dependency to return a fake admin
    async def override_get_current_user():
        class FakeAdminUser:
            id = uuid4()
            role = UserRole.ADMIN
        return FakeAdminUser()

    app.dependency_overrides[admin_user_dependency] = override_get_current_user

    # Override the get_db dependency to return a mock session
    async def override_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:  
        response = await ac.put(f"/admin/kyc/{test_user_id}/approve")

    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == str(test_user_id)
    assert data["status"] == "approved"
    assert "reviewed_at" in data

    # Clean up overrides after the test
    app.dependency_overrides = {}

# ---------------------------
# Test for kyc_not_found
# ---------------------------  
@pytest.mark.asyncio
@patch.object(AdminService, 'approve_kyc', new_callable=AsyncMock)
async def test_approve_kyc_user_not_found(mock_approve_kyc):
    test_user_id = uuid4()
    mock_approve_kyc.side_effect = HTTPException(status_code=404, detail="KYC not found")

    async def override_get_current_user():
        class FakeAdminUser:
            id = uuid4()
            role = UserRole.ADMIN
        return FakeAdminUser()
    
    app.dependency_overrides[admin_user_dependency] = override_get_current_user

    async def override_get_db():
        yield AsyncMock()
    
    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.put(f"/admin/kyc/{test_user_id}/approve")

    assert response.status_code == 404
    assert response.json()["detail"] == "KYC not found"

    app.dependency_overrides = {}    

# ---------------------------
# Test for reject_user_kyc
# ---------------------------  

@pytest.mark.asyncio
@patch.object(AdminService, 'reject_kyc', new_callable=AsyncMock)
async def test_reject_user_kyc_success(mock_reject_kyc):
     # Create a fake user ID and response
    test_user_id = uuid4()
    fake_response = KYCReviewResponse(
        user_id=test_user_id,
        status="rejected",
        reviewed_at=datetime.now(timezone.utc)
    )

    mock_reject_kyc.return_value = fake_response

    # Override the admin_user_dependency to return a fake admin
    async def override_get_current_user():
        class FakeAdminUser:
            id = uuid4()
            role = UserRole.ADMIN
        return FakeAdminUser()

    app.dependency_overrides[admin_user_dependency] = override_get_current_user

    # Override the get_db dependency to return a mock session
    async def override_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:  
        response = await ac.put(f"/admin/kyc/{test_user_id}/reject")

    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == str(test_user_id)
    assert data["status"] == "rejected"
    assert "reviewed_at" in data

    # Clean up overrides after the test
    app.dependency_overrides = {}

# ---------------------------
# Test for freeze_user_account
# ---------------------------    

@pytest.mark.asyncio
@patch.object(AdminService, 'freeze_user', new_callable=AsyncMock)
async def test_freeze_user_account(mock_freeze_user):
     # Create a fake user ID and response
    test_user_id = uuid4()
    fake_response = UserStatusUpdateResponse(
        user_id=test_user_id,
        action='frozen',
        success=True,
        timestamp=datetime.now(timezone.utc)
    )

    mock_freeze_user.return_value = fake_response

    async def override_get_current_user():
        class FakeAdminUser:
            id = uuid4()
            role = UserRole.ADMIN
        return FakeAdminUser()

    app.dependency_overrides[admin_user_dependency] = override_get_current_user

    # Override the get_db dependency to return a mock session
    async def override_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:  
        response = await ac.put(f"/admin/users/{test_user_id}/freeze")

    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == str(test_user_id)
    assert data["action"] == "frozen"
    assert data["success"] is True
    assert "timestamp" in data

    # Clean up overrides after the test
    app.dependency_overrides = {}

# ---------------------------
# Test for unfreeze_user_account
# ---------------------------    

@pytest.mark.asyncio
@patch.object(AdminService, 'unfreeze_user', new_callable=AsyncMock)
async def test_unfreeze_user_account(mock_unfreeze_user):
     # Create a fake user ID and response
    test_user_id = uuid4()
    fake_response = UserStatusUpdateResponse(
        user_id=test_user_id,
        action='unfrozen',
        success=True,
        timestamp=datetime.now(timezone.utc)
    )

    mock_unfreeze_user.return_value = fake_response

    async def override_get_current_user():
        class FakeAdminUser:
            id = uuid4()
            role = UserRole.ADMIN
        return FakeAdminUser()

    app.dependency_overrides[admin_user_dependency] = override_get_current_user

    # Override the get_db dependency to return a mock session
    async def override_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:  
        response = await ac.put(f"/admin/users/{test_user_id}/unfreeze")

    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == str(test_user_id)
    assert data["action"] == "unfrozen"
    assert data["success"] is True
    assert "timestamp" in data

    # Clean up overrides after the test
    app.dependency_overrides = {}

# ---------------------------
# Test for unfreeze_user_account
# ---------------------------    

@pytest.mark.asyncio
@patch.object(AdminService, 'unfreeze_user', new_callable=AsyncMock)
async def test_unfreeze_user_account(mock_unfreeze_user):
     # Create a fake user ID and response
    test_user_id = uuid4()
    fake_response = UserStatusUpdateResponse(
        user_id=test_user_id,
        action='unfrozen',
        success=True,
        timestamp=datetime.now(timezone.utc)
    )

    mock_unfreeze_user.return_value = fake_response

    async def override_get_current_user():
        class FakeAdminUser:
            id = uuid4()
            role = UserRole.ADMIN
        return FakeAdminUser()

    app.dependency_overrides[admin_user_dependency] = override_get_current_user

    # Override the get_db dependency to return a mock session
    async def override_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:  
        response = await ac.put(f"/admin/users/{test_user_id}/unfreeze")

    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == str(test_user_id)
    assert data["action"] == "unfrozen"
    assert data["success"] is True
    assert "timestamp" in data

    # Clean up overrides after the test
    app.dependency_overrides = {}
# ---------------------------
# Test for ban_user_account
# ---------------------------    

@pytest.mark.asyncio
@patch.object(AdminService, 'ban_user', new_callable=AsyncMock)
async def test_ban_user_account(mock_ban_user):
     # Create a fake user ID and response
    test_user_id = uuid4()
    fake_response = UserStatusUpdateResponse(
        user_id=test_user_id,
        action='banned',
        success=True,
        timestamp=datetime.now(timezone.utc)
    )

    mock_ban_user.return_value = fake_response

    async def override_get_current_user():
        class FakeAdminUser:
            id = uuid4()
            role = UserRole.ADMIN
        return FakeAdminUser()

    app.dependency_overrides[admin_user_dependency] = override_get_current_user

    # Override the get_db dependency to return a mock session
    async def override_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:  
        response = await ac.put(f"/admin/users/{test_user_id}/ban")

    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == str(test_user_id)
    assert data["action"] == "banned"
    assert data["success"] is True
    assert "timestamp" in data

    # Clean up overrides after the test
    app.dependency_overrides = {}

# ---------------------------
# Test for unban_user_account
# ---------------------------    

@pytest.mark.asyncio
@patch.object(AdminService, 'unban_user', new_callable=AsyncMock)
async def test_unban_user_account(mock_unban_user):
     # Create a fake user ID and response
    test_user_id = uuid4()
    fake_response = UserStatusUpdateResponse(
        user_id=test_user_id,
        action='unbanned',
        success=True,
        timestamp=datetime.now(timezone.utc)
    )

    mock_unban_user.return_value = fake_response

    async def override_get_current_user():
        class FakeAdminUser:
            id = uuid4()
            role = UserRole.ADMIN
        return FakeAdminUser()

    app.dependency_overrides[admin_user_dependency] = override_get_current_user

    # Override the get_db dependency to return a mock session
    async def override_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:  
        response = await ac.put(f"/admin/users/{test_user_id}/unban")

    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == str(test_user_id)
    assert data["action"] == "unbanned"
    assert data["success"] is True
    assert "timestamp" in data

    # Clean up overrides after the test
    app.dependency_overrides = {}

# ---------------------------
# Test for unfreeze_user_account
# ---------------------------    

@pytest.mark.asyncio
@patch.object(AdminService, 'unfreeze_user', new_callable=AsyncMock)
async def test_unfreeze_user_account(mock_unfreeze_user):
     # Create a fake user ID and response
    test_user_id = uuid4()
    fake_response = UserStatusUpdateResponse(
        user_id=test_user_id,
        action='unfrozen',
        success=True,
        timestamp=datetime.now(timezone.utc)
    )

    mock_unfreeze_user.return_value = fake_response

    async def override_get_current_user():
        class FakeAdminUser:
            id = uuid4()
            role = UserRole.ADMIN
        return FakeAdminUser()

    app.dependency_overrides[admin_user_dependency] = override_get_current_user

    # Override the get_db dependency to return a mock session
    async def override_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:  
        response = await ac.put(f"/admin/users/{test_user_id}/unfreeze")

    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == str(test_user_id)
    assert data["action"] == "unfrozen"
    assert data["success"] is True
    assert "timestamp" in data

    # Clean up overrides after the test
    app.dependency_overrides = {}

# ---------------------------
# Test for delete_user_account and user not found (by trying to find a deleted user)
# ---------------------------    

@pytest.mark.asyncio
@patch.object(AdminService, 'delete_user', new_callable=AsyncMock)
async def test_delete_user_account(mock_delete_user):
     # Create a fake user ID and response
    test_user_id = uuid4()
    

    # First call returns success, second raises 404
    mock_delete_user.side_effect = [
        None,  # First call: review deleted
        HTTPException(status_code=404, detail="User not found")  # Second call: not found
    ]

    async def override_get_current_user():
        class FakeAdminUser:
            id = uuid4()
            role = UserRole.ADMIN
        return FakeAdminUser()

    app.dependency_overrides[admin_user_dependency] = override_get_current_user

    # Override the get_db dependency to return a mock session
    async def override_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:  
    # First delete
        response1 = await ac.delete(f"/admin/users/{test_user_id}")
        assert response1.status_code == 200
        assert response1.json()["detail"] == "User deleted successfully."

        # Second delete
        response2 = await ac.delete(f"/admin/users/{test_user_id}")
        assert response2.status_code == 404
        assert response2.json()["detail"] == "User not found"

    # Clean up overrides after the test
    app.dependency_overrides = {}

# ---------------------------
# Test for get_flagged_reviews
# ---------------------------    


@pytest.mark.asyncio
@patch.object(AdminService, 'list_flagged_reviews', new_callable=AsyncMock)
async def test_get_flagged_reviews(mock_list_flagged_reviews):
        # --- Mock Data ---
    fake_reviews = [
        FlaggedReviewRead(
            review_id=uuid4(),
            user_id=uuid4(),
            job_id=uuid4(),
            content="Inappropriate review content",
            is_flagged=True,
            created_at=datetime.now(timezone.utc)
        )
]
    
    mock_list_flagged_reviews.return_value = fake_reviews

    async def override_get_current_user():
        class FakeAdminUser:
            id = uuid4()
            role = UserRole.ADMIN
        return FakeAdminUser()

    app.dependency_overrides[admin_user_dependency] = override_get_current_user

    # Override the get_db dependency to return a mock session
    async def override_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:  
        response = await ac.get(f"/admin/reviews/flagged")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1

    review_data = data[0]
    assert review_data["review_id"] == str(fake_reviews[0].review_id)
    assert review_data["user_id"] == str(fake_reviews[0].user_id)
    assert review_data["job_id"] == str(fake_reviews[0].job_id)
    assert review_data["content"] == fake_reviews[0].content
    assert review_data["is_flagged"] is True
    assert "created_at" in review_data

    # Clean up overrides after the test
    app.dependency_overrides = {}

# ---------------------------
# Test for delete_flagged_review and review not found i.e trying to find a deleted review
# ---------------------------  

@pytest.mark.asyncio
@patch.object(AdminService, 'delete_review', new_callable=AsyncMock)
async def test_delete_flagged_review_twice(mock_delete_review):
     # Create a fake review ID and response
    test_review_id = uuid4()
    
        # First call returns success, second raises 404
    mock_delete_review.side_effect = [
        None,  # First call: review deleted
        HTTPException(status_code=404, detail="Review not found")  # Second call: not found
    ]

    async def override_get_current_user():
        class FakeAdminUser:
            id = uuid4()
            role = UserRole.ADMIN
        return FakeAdminUser()

    app.dependency_overrides[admin_user_dependency] = override_get_current_user

    # Override the get_db dependency to return a mock session
    async def override_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:  
    # First delete
        response1 = await ac.delete(f"/admin/reviews/{test_review_id}")
        assert response1.status_code == 200
        assert response1.json()["detail"] == "Review deleted."

        # Second delete
        response2 = await ac.delete(f"/admin/reviews/{test_review_id}")
        assert response2.status_code == 404
        assert response2.json()["detail"] == "Review not found"
    
   
    # Clean up overrides after the test
    app.dependency_overrides = {}

# ---------------------------
# Test for unauthourized access when user != Admin
# ---------------------------      

@pytest.mark.asyncio
async def test_non_admin_access_forbidden():
    # Force admin_user_dependency to raise 403 error immediately
    app.dependency_overrides[admin_user_dependency] = lambda: (_ for _ in ()).throw(
        HTTPException(status_code=403, detail=f"Access denied for role: {UserRole.CLIENT}")
    )

    async def override_get_db():
        yield AsyncMock()
    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/admin/reviews/flagged")

    assert response.status_code == 403
    assert response.json()["detail"] == f"Access denied for role: {UserRole.CLIENT}"

    app.dependency_overrides.clear()



   