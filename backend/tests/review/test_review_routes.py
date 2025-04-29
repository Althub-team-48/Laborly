"""
tests/review/test_review_routes.py

Test cases for worker review API endpoints.
Covers public review fetching, worker review summary, client submitting reviews, and retrieving own reviews.
"""

import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from fastapi import status, HTTPException

from app.review import schemas as review_schemas
from app.review import services as review_services
from app.review.models import Review
from app.database.models import User

# Public Review Endpoints


@pytest.mark.asyncio
@patch.object(review_services.ReviewService, "get_reviews_for_worker", new_callable=AsyncMock)
async def test_get_public_worker_reviews(
    mock_get_reviews_for_worker: AsyncMock,
    fake_public_review_read: review_schemas.PublicReviewRead,
    async_client: AsyncClient,
    override_get_db: None,
) -> None:
    """Test retrieving public reviews for a worker."""
    worker_id = uuid4()
    reviews_list = [MagicMock(spec=Review, **fake_public_review_read.model_dump())]
    total_count = 1
    mock_get_reviews_for_worker.return_value = (reviews_list, total_count)

    response = await async_client.get(f"/reviews/worker/{worker_id}/public?skip=0&limit=10")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total_count"] == total_count
    assert len(data["items"]) == len(reviews_list)
    assert data["items"][0]["id"] == str(fake_public_review_read.id)
    assert "client_id" not in data["items"][0]
    mock_get_reviews_for_worker.assert_awaited_once_with(worker_id=worker_id, skip=0, limit=10)


@pytest.mark.asyncio
@patch.object(review_services.ReviewService, "get_review_summary", new_callable=AsyncMock)
async def test_get_worker_review_summary(
    mock_get_review_summary: AsyncMock,
    fake_review_summary: review_schemas.WorkerReviewSummary,
    async_client: AsyncClient,
    override_get_db: None,
) -> None:
    """Test retrieving review summary for a worker."""
    worker_id = uuid4()
    mock_get_review_summary.return_value = fake_review_summary

    response = await async_client.get(f"/reviews/summary/{worker_id}")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total_reviews"] == fake_review_summary.total_reviews
    assert data["average_rating"] == fake_review_summary.average_rating
    mock_get_review_summary.assert_awaited_once_with(worker_id=worker_id)


# Authenticated Review Endpoints


@pytest.mark.asyncio
@patch.object(review_services.ReviewService, "submit_review", new_callable=AsyncMock)
async def test_submit_review_success(
    mock_submit_review: AsyncMock,
    fake_review_read: review_schemas.ReviewRead,
    mock_current_client_user: User,
    async_client: AsyncClient,
    override_get_db: None,
) -> None:
    """Test client submitting a review successfully."""
    job_id = uuid4()
    fake_review_read.client_id = mock_current_client_user.id
    fake_review_read.job_id = job_id
    fake_review_read.text = "Excellent job!"
    mock_submit_review.return_value = MagicMock(spec=Review, **fake_review_read.model_dump())

    payload_schema = review_schemas.ReviewWrite(rating=5, text="Excellent job!")
    payload = payload_schema.model_dump(mode='json')

    response = await async_client.post(f"/reviews/{job_id}", json=payload)

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["id"] == str(fake_review_read.id)
    assert data["job_id"] == str(job_id)
    assert data["client_id"] == str(mock_current_client_user.id)
    assert data["rating"] == payload_schema.rating
    assert data["text"] == payload_schema.text

    expected_payload = review_schemas.ReviewWrite(rating=5, text="Excellent job!")
    mock_submit_review.assert_awaited_once_with(
        job_id=job_id,
        reviewer_id=mock_current_client_user.id,
        data=expected_payload,
    )


@pytest.mark.asyncio
@patch.object(review_services.ReviewService, "get_reviews_by_client", new_callable=AsyncMock)
async def test_get_my_reviews(
    mock_get_reviews_by_client: AsyncMock,
    fake_review_read: review_schemas.ReviewRead,
    mock_current_client_user: User,
    async_client: AsyncClient,
    override_get_db: None,
) -> None:
    """Test client retrieving their submitted reviews."""
    reviews_list = [MagicMock(spec=Review, **fake_review_read.model_dump())]
    total_count = 3
    mock_get_reviews_by_client.return_value = (reviews_list, total_count)

    response = await async_client.get("/reviews/my?skip=0&limit=5")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total_count"] == total_count
    assert len(data["items"]) == len(reviews_list)
    assert data["items"][0]["id"] == str(fake_review_read.id)
    assert data["items"][0]["client_id"] == str(mock_current_client_user.id)
    mock_get_reviews_by_client.assert_awaited_once_with(
        client_id=mock_current_client_user.id, skip=0, limit=5
    )


@pytest.mark.asyncio
@patch.object(review_services.ReviewService, "submit_review", new_callable=AsyncMock)
async def test_submit_review_job_not_found(
    mock_submit_review: AsyncMock,
    mock_current_client_user: User,
    async_client: AsyncClient,
    override_get_db: None,
) -> None:
    """Test submitting a review for a non-existent or unauthorized job."""
    job_id = uuid4()
    mock_submit_review.side_effect = HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Job not found or you are not authorized to review it.",
    )

    payload = review_schemas.ReviewWrite(rating=4, text="Good").model_dump(mode='json')

    response = await async_client.post(f"/reviews/{job_id}", json=payload)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Job not found or you are not authorized to review it."
    mock_submit_review.assert_awaited_once()
