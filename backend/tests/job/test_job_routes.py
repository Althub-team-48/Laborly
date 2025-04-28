"""
tests/job/test_job_routes.py

Test cases for job management API endpoints.
Covers job creation, acceptance, rejection, completion, cancellation, listing, and detail retrieval.
"""

from datetime import datetime, timedelta, timezone
import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4
from fastapi import status, HTTPException

from app.job import schemas as job_schemas
from app.job import services as job_services
from app.job.models import Job, JobStatus
from app.database.models import User

# Helper function


def create_db_job(
    client_id: UUID, worker_id: UUID, status: JobStatus, service_id: UUID | None = None
) -> Job:
    """Create a mock Job DB model instance."""
    now = datetime.now(timezone.utc)
    job = Job(
        id=uuid4(),
        client_id=client_id,
        worker_id=worker_id,
        service_id=service_id,
        status=status,
        created_at=now - timedelta(days=1),
        updated_at=now,
    )
    if status in [
        JobStatus.ACCEPTED,
        JobStatus.COMPLETED,
        JobStatus.FINALIZED,
        JobStatus.CANCELLED,
        JobStatus.REJECTED,
    ]:
        job.started_at = now - timedelta(hours=12)
    if status in [JobStatus.COMPLETED, JobStatus.FINALIZED]:
        job.completed_at = now - timedelta(hours=1)
    if status in [JobStatus.CANCELLED, JobStatus.REJECTED]:
        job.cancelled_at = now - timedelta(hours=1)
        job.cancel_reason = "Test reason" if status == JobStatus.CANCELLED else "Rejected by worker"
    return job


# Job Creation and Management Tests


@pytest.mark.asyncio
@patch.object(job_services.JobService, "create_job", new_callable=AsyncMock)
async def test_create_job_success(
    mock_create_job: AsyncMock,
    fake_job_read: job_schemas.JobRead,
    mock_current_client_user: User,
    async_client: AsyncClient,
    override_get_db: None,
) -> None:
    """Test creating a job successfully."""
    fake_job_read.client_id = mock_current_client_user.id
    mock_create_job.return_value = MagicMock(spec=Job, **fake_job_read.model_dump())

    payload = job_schemas.JobCreate(service_id=uuid4(), thread_id=uuid4()).model_dump(mode='json')

    response = await async_client.post("/jobs/create", json=payload)

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["id"] is not None
    assert data["client_id"] == str(mock_current_client_user.id)
    assert data["status"] == JobStatus.NEGOTIATING.value

    expected_payload = job_schemas.JobCreate(
        service_id=UUID(payload["service_id"]), thread_id=UUID(payload["thread_id"])
    )
    mock_create_job.assert_awaited_once_with(
        client_id=mock_current_client_user.id,
        payload=expected_payload,
    )


@pytest.mark.asyncio
@patch.object(job_services.JobService, "accept_job", new_callable=AsyncMock)
async def test_accept_job_success(
    mock_accept_job: AsyncMock,
    fake_job_read: job_schemas.JobRead,
    mock_current_worker_user: User,
    async_client: AsyncClient,
    override_get_db: None,
) -> None:
    """Test accepting a job successfully."""
    job_id_to_accept = uuid4()
    fake_job_read.id = job_id_to_accept
    fake_job_read.worker_id = mock_current_worker_user.id
    fake_job_read.status = JobStatus.ACCEPTED
    mock_accept_job.return_value = MagicMock(spec=Job, **fake_job_read.model_dump())

    payload = job_schemas.JobAccept(job_id=job_id_to_accept).model_dump(mode='json')

    response = await async_client.post("/jobs/accept", json=payload)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == str(job_id_to_accept)
    assert data["status"] == JobStatus.ACCEPTED.value
    assert data["worker_id"] == str(mock_current_worker_user.id)

    mock_accept_job.assert_awaited_once_with(
        worker_id=mock_current_worker_user.id,
        job_id=job_id_to_accept,
    )


@pytest.mark.asyncio
@patch.object(job_services.JobService, "reject_job", new_callable=AsyncMock)
async def test_reject_job_success(
    mock_reject_job: AsyncMock,
    fake_job_read: job_schemas.JobRead,
    mock_current_worker_user: User,
    async_client: AsyncClient,
    override_get_db: None,
) -> None:
    """Test rejecting a job successfully."""
    job_id_to_reject = uuid4()
    rejection_reason = "Not available"
    fake_job_read.id = job_id_to_reject
    fake_job_read.worker_id = mock_current_worker_user.id
    fake_job_read.status = JobStatus.REJECTED
    fake_job_read.cancel_reason = rejection_reason
    mock_reject_job.return_value = MagicMock(spec=Job, **fake_job_read.model_dump())

    payload = job_schemas.JobReject(reject_reason=rejection_reason).model_dump()

    response = await async_client.put(f"/jobs/{job_id_to_reject}/reject", json=payload)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == str(job_id_to_reject)
    assert data["status"] == JobStatus.REJECTED.value
    assert data["cancel_reason"] == rejection_reason
    assert data["worker_id"] == str(mock_current_worker_user.id)

    actual_payload = job_schemas.JobReject(reject_reason=rejection_reason)
    mock_reject_job.assert_awaited_once_with(
        worker_id=mock_current_worker_user.id,
        job_id=job_id_to_reject,
        payload=actual_payload,
    )


@pytest.mark.asyncio
@patch.object(job_services.JobService, "complete_job", new_callable=AsyncMock)
async def test_complete_job_success(
    mock_complete_job: AsyncMock,
    fake_job_read: job_schemas.JobRead,
    mock_current_worker_user: User,
    async_client: AsyncClient,
    override_get_db: None,
) -> None:
    """Test completing a job successfully."""
    job_id_to_complete = uuid4()
    fake_job_read.id = job_id_to_complete
    fake_job_read.worker_id = mock_current_worker_user.id
    fake_job_read.status = JobStatus.COMPLETED
    mock_complete_job.return_value = MagicMock(spec=Job, **fake_job_read.model_dump())

    response = await async_client.put(f"/jobs/{job_id_to_complete}/complete")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == str(job_id_to_complete)
    assert data["status"] == JobStatus.COMPLETED.value
    assert data["worker_id"] == str(mock_current_worker_user.id)

    mock_complete_job.assert_awaited_once_with(
        worker_id=mock_current_worker_user.id,
        job_id=job_id_to_complete,
    )


@pytest.mark.asyncio
@patch.object(job_services.JobService, "cancel_job", new_callable=AsyncMock)
async def test_cancel_job_success(
    mock_cancel_job: AsyncMock,
    fake_job_read: job_schemas.JobRead,
    mock_current_client_user: User,
    async_client: AsyncClient,
    override_get_db: None,
) -> None:
    """Test cancelling a job successfully."""
    job_id_to_cancel = uuid4()
    cancel_reason = "Client unavailable"
    fake_job_read.id = job_id_to_cancel
    fake_job_read.client_id = mock_current_client_user.id
    fake_job_read.status = JobStatus.CANCELLED
    fake_job_read.cancel_reason = cancel_reason
    mock_cancel_job.return_value = MagicMock(spec=Job, **fake_job_read.model_dump())

    payload = job_schemas.CancelJobRequest(cancel_reason=cancel_reason).model_dump()

    response = await async_client.put(f"/jobs/{job_id_to_cancel}/cancel", json=payload)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == str(job_id_to_cancel)
    assert data["status"] == JobStatus.CANCELLED.value
    assert data["cancel_reason"] == cancel_reason
    assert data["client_id"] == str(mock_current_client_user.id)

    mock_cancel_job.assert_awaited_once_with(
        user_id=mock_current_client_user.id,
        job_id=job_id_to_cancel,
        cancel_reason=cancel_reason,
    )


# Job Listing and Detail Endpoints


@pytest.mark.asyncio
@patch.object(job_services.JobService, "get_all_jobs_for_user", new_callable=AsyncMock)
async def test_get_jobs_for_user(
    mock_get_jobs: AsyncMock,
    fake_job_read: job_schemas.JobRead,
    mock_current_client_user: User,
    async_client: AsyncClient,
    override_get_db: None,
) -> None:
    """Test retrieving jobs for a user."""
    jobs_list = [MagicMock(spec=Job, **fake_job_read.model_dump()) for _ in range(3)]
    total_count = 10
    mock_get_jobs.return_value = (jobs_list, total_count)

    response = await async_client.get("/jobs?skip=0&limit=5")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total_count"] == total_count
    assert len(data["items"]) == len(jobs_list)
    assert data["items"][0]["id"] == str(jobs_list[0].id)

    mock_get_jobs.assert_awaited_once_with(
        mock_current_client_user.id,
        skip=0,
        limit=5,
    )


@pytest.mark.asyncio
@patch.object(job_services.JobService, "get_job_detail", new_callable=AsyncMock)
async def test_get_job_detail_success(
    mock_get_detail: AsyncMock,
    fake_job_read: job_schemas.JobRead,
    mock_current_worker_user: User,
    async_client: AsyncClient,
    override_get_db: None,
) -> None:
    """Test retrieving job detail successfully."""
    job_id = uuid4()
    fake_job_read.id = job_id
    mock_get_detail.return_value = MagicMock(spec=Job, **fake_job_read.model_dump())

    response = await async_client.get(f"/jobs/{job_id}")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == str(job_id)

    mock_get_detail.assert_awaited_once_with(
        user_id=mock_current_worker_user.id,
        job_id=job_id,
    )


@pytest.mark.asyncio
@patch.object(job_services.JobService, "get_job_detail", new_callable=AsyncMock)
async def test_get_job_detail_not_found(
    mock_get_detail: AsyncMock,
    mock_current_client_user: User,
    async_client: AsyncClient,
    override_get_db: None,
) -> None:
    """Test retrieving job detail when job is not found."""
    job_id = uuid4()
    mock_get_detail.side_effect = HTTPException(status_code=404, detail="Job not found")

    response = await async_client.get(f"/jobs/{job_id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Job not found"

    mock_get_detail.assert_awaited_once_with(
        user_id=mock_current_client_user.id,
        job_id=job_id,
    )
