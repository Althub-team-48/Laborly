import pytest
from uuid import uuid4
from datetime import datetime, timezone
from unittest.mock import patch, AsyncMock
from fastapi import HTTPException

from main import app
from app.admin.schemas import KYCReviewResponse, UserStatusUpdateResponse, FlaggedReviewRead
from app.admin.routes import AdminDep
from app.database.enums import UserRole
from app.admin.services import AdminService

# ----------------------------
# KYC Endpoints
# ----------------------------


@patch.object(AdminService, 'list_pending_kyc', new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_get_pending_kyc_list(mock_list_pending_kyc, override_admin_user, async_client):
    """Test fetching list of pending KYC submissions."""
    mock_list_pending_kyc.return_value = [
        KYCReviewResponse(user_id=uuid4(), status="pending", reviewed_at=datetime.now(timezone.utc))
    ]
    async with async_client as ac:
        response = await ac.get("/admin/kyc/pending")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@patch.object(AdminService, 'approve_kyc', new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_approve_user_kyc_success(
    mock_approve_kyc, override_admin_user, override_get_db, async_client
):
    """Test successful approval of user KYC."""
    test_user_id = uuid4()
    mock_approve_kyc.return_value = KYCReviewResponse(
        user_id=test_user_id, status="APPROVED", reviewed_at=datetime.now(timezone.utc)
    )
    async with async_client as ac:
        response = await ac.put(f"/admin/kyc/{test_user_id}/approve")
    data = response.json()
    assert response.status_code == 200
    assert data["user_id"] == str(test_user_id)
    assert data["status"] == "APPROVED"


@patch.object(AdminService, 'approve_kyc', new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_kyc_user_not_found(
    mock_approve_kyc, override_admin_user, override_get_db, async_client
):
    """Test KYC approval for non-existent user returns 404."""
    test_user_id = uuid4()
    mock_approve_kyc.side_effect = HTTPException(status_code=404, detail="KYC not found")
    async with async_client as ac:
        response = await ac.put(f"/admin/kyc/{test_user_id}/approve")
    assert response.status_code == 404
    assert response.json()["detail"] == "KYC not found"


@patch.object(AdminService, 'reject_kyc', new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_reject_user_kyc_success(
    mock_reject_kyc, override_admin_user, override_get_db, async_client
):
    """Test successful rejection of user KYC."""
    test_user_id = uuid4()
    mock_reject_kyc.return_value = KYCReviewResponse(
        user_id=test_user_id, status="REJECTED", reviewed_at=datetime.now(timezone.utc)
    )
    async with async_client as ac:
        response = await ac.put(f"/admin/kyc/{test_user_id}/reject")
    data = response.json()
    assert response.status_code == 200
    assert data["user_id"] == str(test_user_id)
    assert data["status"] == "REJECTED"


# ----------------------------
# User Moderation Endpoints
# ----------------------------


@patch.object(AdminService, 'freeze_user', new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_freeze_user_account(
    mock_freeze_user, override_admin_user, override_get_db, async_client
):
    """Test freezing a user account."""
    test_user_id = uuid4()
    mock_freeze_user.return_value = UserStatusUpdateResponse(
        user_id=test_user_id, action="frozen", success=True, timestamp=datetime.now(timezone.utc)
    )
    async with async_client as ac:
        response = await ac.put(f"/admin/users/{test_user_id}/freeze")
    data = response.json()
    assert response.status_code == 200
    assert data["action"] == "frozen"
    assert data["success"] is True


@patch.object(AdminService, 'unfreeze_user', new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_unfreeze_user_account(
    mock_unfreeze_user, override_admin_user, override_get_db, async_client
):
    """Test unfreezing a user account."""
    test_user_id = uuid4()
    mock_unfreeze_user.return_value = UserStatusUpdateResponse(
        user_id=test_user_id, action="unfrozen", success=True, timestamp=datetime.now(timezone.utc)
    )
    async with async_client as ac:
        response = await ac.put(f"/admin/users/{test_user_id}/unfreeze")
    data = response.json()
    assert response.status_code == 200
    assert data["action"] == "unfrozen"


@patch.object(AdminService, 'ban_user', new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_ban_user_account(mock_ban_user, override_admin_user, override_get_db, async_client):
    """Test banning a user account."""
    test_user_id = uuid4()
    mock_ban_user.return_value = UserStatusUpdateResponse(
        user_id=test_user_id, action="banned", success=True, timestamp=datetime.now(timezone.utc)
    )
    async with async_client as ac:
        response = await ac.put(f"/admin/users/{test_user_id}/ban")
    data = response.json()
    assert response.status_code == 200
    assert data["action"] == "banned"


@patch.object(AdminService, 'unban_user', new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_unban_user_account(
    mock_unban_user, override_admin_user, override_get_db, async_client
):
    """Test unbanning a user account."""
    test_user_id = uuid4()
    mock_unban_user.return_value = UserStatusUpdateResponse(
        user_id=test_user_id, action="unbanned", success=True, timestamp=datetime.now(timezone.utc)
    )
    async with async_client as ac:
        response = await ac.put(f"/admin/users/{test_user_id}/unban")
    data = response.json()
    assert response.status_code == 200
    assert data["action"] == "unbanned"


@patch.object(AdminService, 'delete_user', new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_delete_user_account(
    mock_delete_user, override_admin_user, override_get_db, async_client
):
    """Test deleting a user and attempting to delete again (404)."""
    test_user_id = uuid4()
    mock_delete_user.side_effect = [None, HTTPException(status_code=404, detail="User not found")]
    async with async_client as ac:
        response1 = await ac.delete(f"/admin/users/{test_user_id}")
        assert response1.status_code == 200
        assert response1.json()["action"] == "deleted"
        assert response1.json()["success"] is True

        response2 = await ac.delete(f"/admin/users/{test_user_id}")
        assert response2.status_code == 404
        assert response2.json()["detail"] == "User not found"


# ----------------------------
# Review Moderation Endpoints
# ----------------------------


@patch.object(AdminService, 'list_flagged_reviews', new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_get_flagged_reviews(
    mock_list_flagged_reviews, override_admin_user, override_get_db, async_client
):
    """Test retrieving list of flagged reviews."""
    fake_review = FlaggedReviewRead(
        id=uuid4(),
        client_id=uuid4(),
        job_id=uuid4(),
        rating=1,
        review_text="Inappropriate review",
        is_flagged=True,
        created_at=datetime.now(timezone.utc),
    )
    mock_list_flagged_reviews.return_value = [fake_review]
    async with async_client as ac:
        response = await ac.get("/admin/reviews/flagged")
    data = response.json()
    assert response.status_code == 200
    assert data[0]["review_id"] == str(fake_review.id)


@patch.object(AdminService, 'delete_review', new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_delete_flagged_review_twice(
    mock_delete_review, override_admin_user, override_get_db, async_client
):
    """Test deleting flagged review and attempting deletion again (404)."""
    review_id = uuid4()
    mock_delete_review.side_effect = [
        None,
        HTTPException(status_code=404, detail="Review not found"),
    ]
    async with async_client as ac:
        response1 = await ac.delete(f"/admin/reviews/{review_id}")
        assert response1.status_code == 200
        assert response1.json()["detail"] == "Review deleted."
        response2 = await ac.delete(f"/admin/reviews/{review_id}")
        assert response2.status_code == 404
        assert response2.json()["detail"] == "Review not found"


# ----------------------------
# Error handling
# ----------------------------


@pytest.mark.asyncio
async def test_non_admin_access_forbidden(override_get_db, async_client):
    """Test that a non-admin is denied access with 403."""
    app.dependency_overrides[AdminDep] = lambda: (_ for _ in ()).throw(
        HTTPException(status_code=403, detail=f"Access denied for role: {UserRole.CLIENT}")
    )
    async with async_client as ac:
        response = await ac.get("/admin/reviews/flagged")
    assert response.status_code == 403
    assert response.json()["detail"] == f"Access denied for role: {UserRole.CLIENT}"
    app.dependency_overrides.clear()
