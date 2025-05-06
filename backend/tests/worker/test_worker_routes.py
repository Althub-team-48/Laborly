# """
# tests/worker/test_worker_routes.py

# Test cases for worker profile, KYC, and job-related API endpoints.
# Covers public profile access, authenticated worker actions, KYC submission, and job history.
# """

# import pytest
# from httpx import AsyncClient
# from unittest.mock import AsyncMock, MagicMock, patch
# from uuid import UUID, uuid4
# from fastapi import status, HTTPException
# from io import BytesIO
# from datetime import datetime, timezone, timedelta

# from app.worker import schemas as worker_schemas
# from app.worker import services as worker_services
# from app.database.models import User, KYC
# from app.database.enums import KYCStatus
# from app.job.models import Job, JobStatus
# from app.core import schemas as core_schema

# # Helper functions


# def create_db_job_for_worker(worker_id: UUID) -> Job:
#     """Create a mock Job DB model instance assigned to a worker."""
#     now = datetime.now(timezone.utc)
#     return Job(
#         id=uuid4(),
#         client_id=uuid4(),
#         worker_id=worker_id,
#         service_id=uuid4(),
#         status=JobStatus.ACCEPTED,
#         created_at=now - timedelta(days=1),
#         updated_at=now,
#         started_at=now - timedelta(hours=12),
#     )


# # Public Profile Endpoints


# @pytest.mark.asyncio
# @patch.object(worker_services.WorkerService, "get_public_worker_profile", new_callable=AsyncMock)
# async def test_get_public_worker_profile(
#     mock_get_public_profile: AsyncMock,
#     fake_public_worker_read: worker_schemas.PublicWorkerRead,
#     async_client: AsyncClient,
#     override_get_db: None,
# ) -> None:
#     """Test retrieving a public worker profile."""
#     test_user_id = fake_public_worker_read.user_id
#     mock_get_public_profile.return_value = fake_public_worker_read

#     response = await async_client.get(f"/worker/{test_user_id}/public")

#     assert response.status_code == status.HTTP_200_OK
#     data = response.json()
#     assert data["user_id"] == str(test_user_id)
#     assert data["first_name"] == fake_public_worker_read.first_name
#     assert data["is_kyc_verified"] == fake_public_worker_read.is_kyc_verified
#     mock_get_public_profile.assert_awaited_once_with(test_user_id)


# @pytest.mark.asyncio
# @patch.object(worker_services.WorkerService, "get_public_worker_profile", new_callable=AsyncMock)
# async def test_get_public_worker_profile_not_found(
#     mock_get_public_profile: AsyncMock,
#     async_client: AsyncClient,
#     override_get_db: None,
# ) -> None:
#     """Test retrieving a public worker profile that does not exist."""
#     test_user_id = uuid4()
#     mock_get_public_profile.side_effect = HTTPException(status_code=404, detail="Worker not found")

#     response = await async_client.get(f"/worker/{test_user_id}/public")

#     assert response.status_code == status.HTTP_404_NOT_FOUND
#     assert response.json()["detail"] == "Worker not found"
#     mock_get_public_profile.assert_awaited_once_with(test_user_id)


# # Authenticated Profile Endpoints


# @pytest.mark.asyncio
# @patch.object(worker_services.WorkerService, "get_profile", new_callable=AsyncMock)
# async def test_get_my_worker_profile(
#     mock_get_profile: AsyncMock,
#     fake_worker_profile_read: worker_schemas.WorkerProfileRead,
#     mock_current_worker_user: User,
#     async_client: AsyncClient,
#     override_get_db: None,
# ) -> None:
#     """Test retrieving the authenticated worker's profile."""
#     fake_worker_profile_read.user_id = mock_current_worker_user.id
#     mock_get_profile.return_value = fake_worker_profile_read

#     response = await async_client.get("/worker/profile")

#     assert response.status_code == status.HTTP_200_OK
#     data = response.json()
#     assert data["user_id"] == str(mock_current_worker_user.id)
#     assert data["email"] == fake_worker_profile_read.email
#     mock_get_profile.assert_awaited_once_with(mock_current_worker_user.id)


# @pytest.mark.asyncio
# @patch.object(worker_services.WorkerService, "update_profile", new_callable=AsyncMock)
# async def test_update_my_worker_profile(
#     mock_update_profile: AsyncMock,
#     fake_worker_profile_read: worker_schemas.WorkerProfileRead,
#     mock_current_worker_user: User,
#     async_client: AsyncClient,
#     override_get_db: None,
# ) -> None:
#     """Test updating the authenticated worker's profile."""
#     fake_worker_profile_read.user_id = mock_current_worker_user.id
#     fake_worker_profile_read.is_available = False
#     mock_update_profile.return_value = fake_worker_profile_read

#     payload_schema = worker_schemas.WorkerProfileUpdate(is_available=False)
#     payload = payload_schema.model_dump(mode='json', exclude_unset=True)

#     response = await async_client.patch("/worker/profile", json=payload)

#     assert response.status_code == status.HTTP_200_OK
#     data = response.json()
#     assert data["user_id"] == str(mock_current_worker_user.id)
#     assert data["is_available"] is False
#     mock_update_profile.assert_awaited_once()
#     call_args, _ = mock_update_profile.call_args
#     assert call_args[0] == mock_current_worker_user.id
#     assert call_args[1].is_available == payload_schema.is_available


# @pytest.mark.asyncio
# @patch("app.worker.routes.upload_file_to_s3", new_callable=AsyncMock)
# @patch.object(worker_services.WorkerService, "update_profile_picture", new_callable=AsyncMock)
# async def test_update_my_worker_profile_picture(
#     mock_update_pic_service: AsyncMock,
#     mock_upload: AsyncMock,
#     mock_current_worker_user: User,
#     async_client: AsyncClient,
#     override_get_db: None,
# ) -> None:
#     """Test updating the worker's profile picture."""
#     fake_s3_url = "https://fake-bucket.s3.amazonaws.com/profile_pictures/fake_worker_pic.png"
#     mock_upload.return_value = fake_s3_url
#     mock_update_pic_service.return_value = core_schema.MessageResponse(
#         detail="Profile picture updated successfully."
#     )

#     files = {"profile_picture": ("worker_pic.png", BytesIO(b"fake data"), "image/png")}
#     response = await async_client.patch("/worker/profile/picture", files=files)

#     assert response.status_code == status.HTTP_200_OK
#     assert response.json()["detail"] == "Profile picture updated successfully."
#     mock_upload.assert_awaited_once()
#     mock_update_pic_service.assert_awaited_once_with(mock_current_worker_user.id, fake_s3_url)


# @pytest.mark.asyncio
# @patch.object(
#     worker_services.WorkerService, "get_profile_picture_presigned_url", new_callable=AsyncMock
# )
# async def test_get_my_worker_profile_picture_url_success(
#     mock_get_url: AsyncMock,
#     mock_current_worker_user: User,
#     async_client: AsyncClient,
#     override_get_db: None,
# ) -> None:
#     """Test getting the presigned URL for profile picture upload."""
#     fake_url = f"https://fake-bucket.s3.amazonaws.com/profile_pictures/worker_{mock_current_worker_user.id}?sig=abc"
#     mock_get_url.return_value = fake_url

#     response = await async_client.get("/worker/profile/picture-url")

#     assert response.status_code == status.HTTP_200_OK
#     data = response.json()
#     assert data["url"] == fake_url
#     mock_get_url.assert_awaited_once_with(mock_current_worker_user.id)


# # KYC Endpoints


# @pytest.mark.asyncio
# @patch.object(worker_services.WorkerService, "get_kyc", new_callable=AsyncMock)
# async def test_get_my_kyc_found(
#     mock_get_kyc: AsyncMock,
#     fake_kyc_read: worker_schemas.KYCRead,
#     mock_current_worker_user: User,
#     async_client: AsyncClient,
#     override_get_db: None,
# ) -> None:
#     """Test retrieving KYC details if found."""
#     fake_kyc_read.user_id = mock_current_worker_user.id
#     mock_get_kyc.return_value = MagicMock(spec=KYC, **fake_kyc_read.model_dump())

#     response = await async_client.get("/worker/kyc")

#     assert response.status_code == status.HTTP_200_OK
#     data = response.json()
#     assert data["id"] == str(fake_kyc_read.id)
#     assert data["status"] == fake_kyc_read.status.value
#     mock_get_kyc.assert_awaited_once_with(mock_current_worker_user.id)


# @pytest.mark.asyncio
# @patch.object(worker_services.WorkerService, "get_kyc", new_callable=AsyncMock)
# async def test_get_my_kyc_not_found(
#     mock_get_kyc: AsyncMock,
#     mock_current_worker_user: User,
#     async_client: AsyncClient,
#     override_get_db: None,
# ) -> None:
#     """Test retrieving KYC details when none exist."""
#     mock_get_kyc.return_value = None

#     response = await async_client.get("/worker/kyc")

#     assert response.status_code == status.HTTP_200_OK
#     assert response.content == b"null"
#     mock_get_kyc.assert_awaited_once_with(mock_current_worker_user.id)


# @pytest.mark.asyncio
# @patch("app.worker.routes.upload_file_to_s3", new_callable=AsyncMock)
# @patch.object(worker_services.WorkerService, "submit_kyc", new_callable=AsyncMock)
# async def test_submit_my_kyc(
#     mock_submit_kyc: AsyncMock,
#     mock_upload: AsyncMock,
#     fake_kyc_read: worker_schemas.KYCRead,
#     mock_current_worker_user: User,
#     async_client: AsyncClient,
#     override_get_db: None,
# ) -> None:
#     """Test submitting KYC details."""
#     doc_url = f"s3://kyc/doc_{uuid4()}.pdf"
#     selfie_url = f"s3://kyc/selfie_{uuid4()}.png"
#     mock_upload.side_effect = [doc_url, selfie_url]

#     fake_kyc_read.user_id = mock_current_worker_user.id
#     fake_kyc_read.status = KYCStatus.PENDING
#     fake_kyc_read.document_path = doc_url
#     fake_kyc_read.selfie_path = selfie_url
#     mock_submit_kyc.return_value = MagicMock(spec=KYC, **fake_kyc_read.model_dump())

#     form_data = {"document_type": "National ID"}
#     files = {
#         "document_file": ("id.pdf", BytesIO(b"fake pdf data"), "application/pdf"),
#         "selfie_file": ("face.png", BytesIO(b"fake png data"), "image/png"),
#     }
#     response = await async_client.post("/worker/kyc", data=form_data, files=files)

#     assert response.status_code == status.HTTP_201_CREATED
#     data = response.json()
#     assert data["user_id"] == str(mock_current_worker_user.id)
#     assert data["status"] == KYCStatus.PENDING.value
#     assert data["document_path"] == doc_url
#     assert data["selfie_path"] == selfie_url

#     mock_submit_kyc.assert_awaited_once_with(
#         user_id=mock_current_worker_user.id,
#         document_type=form_data["document_type"],
#         document_path=doc_url,
#         selfie_path=selfie_url,
#     )
#     assert mock_upload.call_count == 2


# # Job History Endpoints


# @pytest.mark.asyncio
# @patch.object(worker_services.WorkerService, "get_jobs", new_callable=AsyncMock)
# async def test_list_my_worker_jobs(
#     mock_get_jobs: AsyncMock,
#     mock_current_worker_user: User,
#     async_client: AsyncClient,
#     override_get_db: None,
# ) -> None:
#     """Test listing worker jobs."""
#     jobs_list = [create_db_job_for_worker(mock_current_worker_user.id) for _ in range(2)]
#     total_count = 7
#     mock_get_jobs.return_value = (jobs_list, total_count)

#     response = await async_client.get("/worker/jobs?limit=5")

#     assert response.status_code == status.HTTP_200_OK
#     data = response.json()
#     assert data["total_count"] == total_count
#     assert len(data["items"]) == len(jobs_list)
#     assert data["items"][0]["id"] == str(jobs_list[0].id)
#     assert data["items"][0]["worker_id"] == str(mock_current_worker_user.id)
#     mock_get_jobs.assert_awaited_once_with(mock_current_worker_user.id, skip=0, limit=5)


# @pytest.mark.asyncio
# @patch.object(worker_services.WorkerService, "get_job_detail", new_callable=AsyncMock)
# async def test_get_my_worker_job_detail(
#     mock_get_job_detail: AsyncMock,
#     mock_current_worker_user: User,
#     async_client: AsyncClient,
#     override_get_db: None,
# ) -> None:
#     """Test retrieving a specific worker job detail."""
#     job_id = uuid4()
#     fake_job = create_db_job_for_worker(mock_current_worker_user.id)
#     fake_job.id = job_id
#     mock_get_job_detail.return_value = fake_job

#     response = await async_client.get(f"/worker/jobs/{job_id}")

#     assert response.status_code == status.HTTP_200_OK
#     data = response.json()
#     assert data["id"] == str(job_id)
#     assert data["worker_id"] == str(mock_current_worker_user.id)
#     mock_get_job_detail.assert_awaited_once_with(mock_current_worker_user.id, job_id)


# @pytest.mark.asyncio
# @patch.object(worker_services.WorkerService, "get_job_detail", new_callable=AsyncMock)
# async def test_get_my_worker_job_detail_not_found(
#     mock_get_job_detail: AsyncMock,
#     mock_current_worker_user: User,
#     async_client: AsyncClient,
#     override_get_db: None,
# ) -> None:
#     """Test retrieving a non-existent worker job detail."""
#     job_id = uuid4()
#     mock_get_job_detail.side_effect = HTTPException(
#         status_code=404, detail="Job not found or unauthorized"
#     )

#     response = await async_client.get(f"/worker/jobs/{job_id}")

#     assert response.status_code == status.HTTP_404_NOT_FOUND
#     assert response.json()["detail"] == "Job not found or unauthorized"
#     mock_get_job_detail.assert_awaited_once_with(mock_current_worker_user.id, job_id)
