"""
tests/admin/test_admin_routes.py

Unit tests for admin/routes.py covering:
- KYC approvals/rejections
- User account management (freeze, ban, delete)
- Review moderation
- Admin-only restricted access
"""

import pytest
from uuid import uuid4
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, AsyncMock
from fastapi import HTTPException, status
from httpx import AsyncClient

from app.database.models import User, KYC
from app.review.models import Review
from app.database.enums import KYCStatus
from app.admin import services as admin_services


def create_fake_kyc(status: KYCStatus = KYCStatus.PENDING) -> KYC:
    user_id = uuid4()
    return KYC(
        id=uuid4(),
        user_id=user_id,
        document_type="Passport",
        document_path=f"s3://kyc/{user_id}_doc.jpg",
        selfie_path=f"s3://kyc/{user_id}_selfie.jpg",
        status=status,
        submitted_at=datetime.now(timezone.utc) - timedelta(days=1),
        reviewed_at=datetime.now(timezone.utc) if status != KYCStatus.PENDING else None,
    )


def create_fake_review(flagged: bool = True) -> Review:
    return Review(
        id=uuid4(),
        client_id=uuid4(),
        worker_id=uuid4(),
        job_id=uuid4(),
        rating=1 if flagged else 4,
        review_text="Flagged text" if flagged else "Good job",
        is_flagged=flagged,
        created_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )


# --- KYC Endpoints Tests ---
@pytest.mark.asyncio
@patch.object(admin_services.AdminService, "list_pending_kyc", new_callable=AsyncMock)
async def test_get_pending_kyc_list(
    mock_list_pending: AsyncMock,
    mock_current_admin_user: User,
    async_client: AsyncClient,
    override_get_db: None,
) -> None:
    fake_kyc_list = [create_fake_kyc(KYCStatus.PENDING) for _ in range(3)]
    total_count = 10
    mock_list_pending.return_value = (fake_kyc_list, total_count)
    response = await async_client.get("/admin/kyc/pending?skip=0&limit=5")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total_count"] == total_count
    assert len(data["items"]) == len(fake_kyc_list)
    assert data["items"][0]["user_id"] == str(fake_kyc_list[0].user_id)
    assert "submitted_at" in data["items"][0]
    mock_list_pending.assert_awaited_once_with(skip=0, limit=5)


@pytest.mark.asyncio
@patch.object(admin_services.AdminService, "get_kyc_details_for_admin", new_callable=AsyncMock)
async def test_get_kyc_details(
    mock_get_details: AsyncMock,
    mock_current_admin_user: User,
    async_client: AsyncClient,
    override_get_db: None,
) -> None:
    test_user_id = uuid4()
    fake_kyc = create_fake_kyc(KYCStatus.PENDING)
    fake_kyc.user_id = test_user_id
    mock_get_details.return_value = fake_kyc
    response = await async_client.get(f"/admin/kyc/{test_user_id}")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["user_id"] == str(test_user_id)
    assert data["status"] == KYCStatus.PENDING.value
    mock_get_details.assert_awaited_once_with(test_user_id)


@pytest.mark.asyncio
@patch.object(admin_services.AdminService, "approve_kyc", new_callable=AsyncMock)
async def test_approve_user_kyc_success(
    mock_approve_kyc: AsyncMock,
    mock_current_admin_user: User,
    async_client: AsyncClient,
    override_get_db: None,
) -> None:
    test_user_id = uuid4()
    fake_kyc_approved = create_fake_kyc(KYCStatus.APPROVED)
    fake_kyc_approved.user_id = test_user_id
    fake_kyc_approved.reviewed_at = datetime.now(timezone.utc)
    mock_approve_kyc.return_value = fake_kyc_approved
    response = await async_client.put(f"/admin/kyc/{test_user_id}/approve")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["user_id"] == str(test_user_id)
    assert data["status"] == KYCStatus.APPROVED.value
    assert "reviewed_at" in data
    mock_approve_kyc.assert_awaited_once_with(test_user_id)


@pytest.mark.asyncio
@patch.object(admin_services.AdminService, "approve_kyc", new_callable=AsyncMock)
async def test_approve_kyc_not_found(
    mock_approve_kyc: AsyncMock,
    mock_current_admin_user: User,
    async_client: AsyncClient,
    override_get_db: None,
) -> None:
    test_user_id = uuid4()
    mock_approve_kyc.side_effect = HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="KYC record not found."
    )
    response = await async_client.put(f"/admin/kyc/{test_user_id}/approve")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "KYC record not found."
    mock_approve_kyc.assert_awaited_once_with(test_user_id)


@pytest.mark.asyncio
@patch.object(admin_services.AdminService, "reject_kyc", new_callable=AsyncMock)
async def test_reject_user_kyc_success(
    mock_reject_kyc: AsyncMock,
    mock_current_admin_user: User,
    async_client: AsyncClient,
    override_get_db: None,
) -> None:
    test_user_id = uuid4()
    fake_kyc_rejected = create_fake_kyc(KYCStatus.REJECTED)
    fake_kyc_rejected.user_id = test_user_id
    fake_kyc_rejected.reviewed_at = datetime.now(timezone.utc)
    mock_reject_kyc.return_value = fake_kyc_rejected
    response = await async_client.put(f"/admin/kyc/{test_user_id}/reject")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["user_id"] == str(test_user_id)
    assert data["status"] == KYCStatus.REJECTED.value
    assert "reviewed_at" in data
    mock_reject_kyc.assert_awaited_once_with(test_user_id)


@pytest.mark.asyncio
@patch.object(admin_services.AdminService, "get_kyc_presigned_url", new_callable=AsyncMock)
async def test_get_kyc_presigned_url_success(
    mock_get_url: AsyncMock,
    mock_current_admin_user: User,
    async_client: AsyncClient,
    override_get_db: None,
) -> None:
    test_user_id = uuid4()
    doc_type = "document"
    fake_url = f"https://fake-bucket.s3.amazonaws.com/kyc/doc_{test_user_id}?sig=123"
    mock_get_url.return_value = fake_url
    response = await async_client.get(f"/admin/kyc/{test_user_id}/presigned-url/{doc_type}")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["url"] == fake_url
    mock_get_url.assert_awaited_once_with(user_id=test_user_id, doc_type=doc_type)


@pytest.mark.asyncio
@patch.object(admin_services.AdminService, "get_kyc_presigned_url", new_callable=AsyncMock)
async def test_get_kyc_presigned_url_not_found(
    mock_get_url: AsyncMock,
    mock_current_admin_user: User,
    async_client: AsyncClient,
    override_get_db: None,
) -> None:
    test_user_id = uuid4()
    doc_type = "selfie"
    mock_get_url.side_effect = HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"S3 path for '{doc_type}' not found in KYC record.",
    )
    response = await async_client.get(f"/admin/kyc/{test_user_id}/presigned-url/{doc_type}")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == f"S3 path for '{doc_type}' not found in KYC record."
    mock_get_url.assert_awaited_once_with(user_id=test_user_id, doc_type=doc_type)


# --- User Management Endpoints Tests ---
@pytest.mark.asyncio
@patch.object(admin_services.AdminService, "freeze_user", new_callable=AsyncMock)
async def test_freeze_user_account(
    mock_freeze_user: AsyncMock,
    mock_current_admin_user: User,
    async_client: AsyncClient,
    override_get_db: None,
) -> None:
    test_user_id = uuid4()
    mock_freeze_user.return_value = User(id=test_user_id, is_frozen=True, is_active=False)
    response = await async_client.put(f"/admin/users/{test_user_id}/freeze")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["user_id"] == str(test_user_id)
    assert data["action"] == "frozen"
    assert data["success"] is True
    assert "timestamp" in data
    mock_freeze_user.assert_awaited_once_with(test_user_id)


@pytest.mark.asyncio
@patch.object(admin_services.AdminService, "unfreeze_user", new_callable=AsyncMock)
async def test_unfreeze_user_account(
    mock_unfreeze_user: AsyncMock,
    mock_current_admin_user: User,
    async_client: AsyncClient,
    override_get_db: None,
) -> None:
    test_user_id = uuid4()
    mock_unfreeze_user.return_value = User(id=test_user_id, is_frozen=False, is_active=True)
    response = await async_client.put(f"/admin/users/{test_user_id}/unfreeze")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["action"] == "unfrozen"
    assert data["success"] is True
    mock_unfreeze_user.assert_awaited_once_with(test_user_id)


@pytest.mark.asyncio
@patch.object(admin_services.AdminService, "ban_user", new_callable=AsyncMock)
async def test_ban_user_account(
    mock_ban_user: AsyncMock,
    mock_current_admin_user: User,
    async_client: AsyncClient,
    override_get_db: None,
) -> None:
    test_user_id = uuid4()
    mock_ban_user.return_value = User(id=test_user_id, is_banned=True, is_active=False)
    response = await async_client.put(f"/admin/users/{test_user_id}/ban")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["action"] == "banned"
    assert data["success"] is True
    mock_ban_user.assert_awaited_once_with(test_user_id)


@pytest.mark.asyncio
@patch.object(admin_services.AdminService, "unban_user", new_callable=AsyncMock)
async def test_unban_user_account(
    mock_unban_user: AsyncMock,
    mock_current_admin_user: User,
    async_client: AsyncClient,
    override_get_db: None,
) -> None:
    test_user_id = uuid4()
    mock_unban_user.return_value = User(id=test_user_id, is_banned=False, is_active=True)
    response = await async_client.put(f"/admin/users/{test_user_id}/unban")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["action"] == "unbanned"
    assert data["success"] is True
    mock_unban_user.assert_awaited_once_with(test_user_id)


@pytest.mark.asyncio
@patch.object(admin_services.AdminService, "delete_user", new_callable=AsyncMock)
async def test_delete_user_account(
    mock_delete_user: AsyncMock,
    mock_current_admin_user: User,
    async_client: AsyncClient,
    override_get_db: None,
) -> None:
    test_user_id = uuid4()
    mock_delete_user.return_value = None
    response = await async_client.delete(f"/admin/users/{test_user_id}")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["action"] == "deleted"
    assert data["success"] is True
    mock_delete_user.assert_awaited_once_with(test_user_id)


@pytest.mark.asyncio
@patch.object(admin_services.UserService, "list_all_users", new_callable=AsyncMock)
async def test_list_all_users(
    mock_list_users: AsyncMock,
    mock_current_admin_user: User,
    fake_admin_user: User,
    fake_client_user: User,
    async_client: AsyncClient,
    override_get_db: None,
) -> None:
    fake_users_list = [mock_current_admin_user, fake_admin_user, fake_client_user]
    mock_list_users.return_value = fake_users_list
    response = await async_client.get("/admin/users?skip=0&limit=10")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == len(fake_users_list)
    assert data[0]["id"] == str(mock_current_admin_user.id)
    assert data[0]["role"] == mock_current_admin_user.role.value
    assert isinstance(data[0]["is_active"], bool)
    assert data[2]["id"] == str(fake_client_user.id)
    mock_list_users.assert_awaited_once_with(
        skip=0, limit=10, role=None, is_active=None, is_banned=None, is_deleted=None
    )


@pytest.mark.asyncio
@patch.object(admin_services.UserService, "get_user_details", new_callable=AsyncMock)
async def test_get_user_details(
    mock_get_user: AsyncMock,
    mock_current_admin_user: User,
    fake_client_user: User,
    async_client: AsyncClient,
    override_get_db: None,
) -> None:
    target_user = fake_client_user
    mock_get_user.return_value = target_user
    response = await async_client.get(f"/admin/users/{target_user.id}")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == str(target_user.id)
    assert data["email"] == target_user.email
    assert data["role"] == target_user.role.value
    assert isinstance(data["is_banned"], bool)
    mock_get_user.assert_awaited_once_with(user_id=target_user.id)


# --- Review Moderation Endpoints Tests ---
@pytest.mark.asyncio
@patch.object(admin_services.AdminService, "list_flagged_reviews", new_callable=AsyncMock)
async def test_get_flagged_reviews(
    mock_list_flagged: AsyncMock,
    mock_current_admin_user: User,
    async_client: AsyncClient,
    override_get_db: None,
) -> None:
    fake_reviews = [create_fake_review(flagged=True) for _ in range(2)]
    total_count = 5
    mock_list_flagged.return_value = (fake_reviews, total_count)
    response = await async_client.get("/admin/reviews/flagged?skip=0&limit=10")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total_count"] == total_count
    assert len(data["items"]) == len(fake_reviews)
    assert data["items"][0]["review_id"] == str(fake_reviews[0].id)
    assert data["items"][0]["is_flagged"] is True
    mock_list_flagged.assert_awaited_once_with(skip=0, limit=10)


@pytest.mark.asyncio
@patch.object(admin_services.AdminService, "delete_review", new_callable=AsyncMock)
async def test_delete_flagged_review(
    mock_delete_review: AsyncMock,
    mock_current_admin_user: User,
    async_client: AsyncClient,
    override_get_db: None,
) -> None:
    review_id = uuid4()
    mock_delete_review.return_value = None
    response = await async_client.delete(f"/admin/reviews/{review_id}")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["detail"] == "Review deleted."
    mock_delete_review.assert_awaited_once_with(review_id)


@pytest.mark.asyncio
@patch.object(admin_services.AdminService, "delete_review", new_callable=AsyncMock)
async def test_delete_flagged_review_not_found(
    mock_delete_review: AsyncMock,
    mock_current_admin_user: User,
    async_client: AsyncClient,
    override_get_db: None,
) -> None:
    review_id = uuid4()
    mock_delete_review.side_effect = HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="Review not found."
    )
    response = await async_client.delete(f"/admin/reviews/{review_id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Review not found."
    mock_delete_review.assert_awaited_once_with(review_id)


# --- Authorization Test ---
@pytest.mark.asyncio
async def test_non_admin_access_forbidden(
    mock_current_client_user: User, async_client: AsyncClient, override_get_db: None
) -> None:
    response = await async_client.get("/admin/reviews/flagged")
    assert response.status_code == status.HTTP_403_FORBIDDEN
    # Corrected Assertion: Match the actual error detail format
    assert response.json()["detail"] == f"Access denied for role: {mock_current_client_user.role}"
