import pytest
from httpx import AsyncClient
from httpx._transports.asgi import ASGITransport
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from fastapi import status, HTTPException
from datetime import datetime, timezone
from main import app
from app.review.services import ReviewService


# ---------------------------
#Submit Review for a Completed Job
# ---------------------------
@patch.object(ReviewService, "submit_review", new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_submit_review_success(mock_submit_review, fake_review_read, override_client, override_get_db, transport):
    mock_submit_review.return_value = fake_review_read
    job_id = uuid4()
    payload = {
        "rating": 5,
        "text": "Suraju did a perfect job"  
    }
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(f"/reviews/{job_id}", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["id"] == str(fake_review_read.id)
    assert response.json()["job_id"] == str(fake_review_read.job_id)

# ---------------------------
#Submit Review for a Completed Job
# ---------------------------
@patch.object(ReviewService, "submit_review", new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_submit_review_success(mock_submit_review, fake_review_read, override_client, override_get_db, transport):
    mock_submit_review.return_value = fake_review_read
    job_id = uuid4()
    payload = {
        "rating": 5,
        "text": "Suraju did a perfect job"  
    }
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(f"/reviews/{job_id}", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["id"] == str(fake_review_read.id)
    assert response.json()["job_id"] == str(fake_review_read.job_id) 

# ---------------------------
# Get Reviews Received by Worker
# ---------------------------
@patch.object(ReviewService, "get_reviews_for_worker", new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_get_worker_reviews(mock_get_reviews_for_worker, fake_review_read, override_worker_user, override_get_db, async_client ):
    mock_get_reviews_for_worker.return_value = [fake_review_read]
    worker = uuid4()
  
    async with async_client as ac:
        response = await ac.get(f"/reviews/worker/{worker}")
    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.json(), list)   

# ---------------------------
# Get Reviews Submitted by Client
# ---------------------------
@patch.object(ReviewService, "get_reviews_by_client", new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_get_my_reviews(mock_get_reviews_by_client, fake_review_read, override_client, override_get_db, async_client ):
    mock_get_reviews_by_client.return_value = [fake_review_read]
  
    async with async_client as ac:
        response = await ac.get(f"/reviews/my")
    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.json(), list)       

# ---------------------------
# Get Review Summary for Worker
# ---------------------------
@patch.object(ReviewService, "get_review_summary", new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_get_worker_review_summary(mock_get_review_summary, fake_review_summary, override_worker_user, override_get_db, async_client ):
    mock_get_review_summary.return_value = fake_review_summary
    worker = uuid4()
    async with async_client as ac:
        response = await ac.get(f"/reviews/summary/{worker}")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["total_reviews"]==fake_review_summary.total_reviews         