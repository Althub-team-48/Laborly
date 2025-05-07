"""
backend/app/job/services.py

Job Service Layer
Handles all job-related operations such as creation, acceptance, rejection,
completion, cancellation, and retrieval. Implements cache invalidation
and cross-service cache coordination (e.g., with client and worker job lists).
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.blacklist import redis_client
from app.database.enums import UserRole
from app.database.models import User
from app.job import models, schemas
from app.job.models import JobStatus
from app.messaging.models import MessageThread
from app.service.models import Service as ServiceModel

# Import new partial schemas
from app.job.schemas import JobClientInfo, JobWorkerInfo, JobServiceInfo

from app.worker.services import (
    _cache_key,
    CACHE_PREFIX,
)

logger = logging.getLogger(__name__)

# ------------------------
# --- Cache Namespaces ---
# ------------------------
JOB_DETAIL_NS = "job:detail"
JOB_LIST_USER_NS = "job:list"
CLIENT_JOBS_NS = "client_jobs"
WORKER_JOBS_NS = "worker_jobs"


# -------------------------------------------------
# --- Utility: Pattern-based Cache Invalidation ---
# -------------------------------------------------
async def _invalidate_pattern(cache: Any, pattern: str) -> None:
    """Delete Redis keys matching the given pattern."""
    if not cache:
        return
    logger.debug(f"[CACHE ASYNC JOB] Scanning pattern: {pattern}")
    deleted = 0
    try:
        if not redis_client:
            logger.warning("[CACHE ASYNC JOB] Redis client not available for pattern invalidation.")
            return
        async for key in redis_client.scan_iter(match=pattern):
            await redis_client.delete(key)
            deleted += 1
        logger.info(f"[CACHE ASYNC JOB] Deleted {deleted} keys matching pattern {pattern}")
    except Exception as e:
        logger.error(f"[CACHE ASYNC JOB ERROR] Failed pattern deletion for {pattern}: {e}")


class JobService:
    """Service class for job-related business logic with caching."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.cache = redis_client
        if not self.cache:
            logger.warning("[CACHE ASYNC JOB] Redis client not configured, caching disabled.")

    async def _get_user_or_404(self, user_id: UUID) -> User:
        """Helper to retrieve a user or raise 404 if not found."""
        user = await self.db.get(
            User,
            user_id,
            options=[selectinload(User.client_profile), selectinload(User.worker_profile)],
        )
        if not user:
            logger.warning(f"User not found: user_id={user_id}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return user

    async def _get_job_with_relations_or_404(self, job_id: UUID) -> models.Job:
        """Helper to retrieve a job with its relations or raise 404."""
        stmt = (
            select(models.Job)
            .options(
                selectinload(models.Job.client),
                selectinload(models.Job.worker),
                selectinload(models.Job.service).selectinload(ServiceModel.worker),
                selectinload(models.Job.thread),
            )
            .filter(models.Job.id == job_id)
        )
        result = await self.db.execute(stmt)
        job = result.unique().scalar_one_or_none()
        if not job:
            logger.warning(f"Job not found: job_id={job_id}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
        return job

    def _construct_job_read(self, job_model: models.Job) -> schemas.JobRead:
        """Helper to construct JobRead schema from Job model instance."""
        client_info = JobClientInfo.model_validate(job_model.client)

        worker_info: JobWorkerInfo | None = None
        if job_model.worker:
            worker_info = JobWorkerInfo.model_validate(job_model.worker)

        service_info: JobServiceInfo | None = None
        if job_model.service:
            service_info = JobServiceInfo.model_validate(job_model.service)

        return schemas.JobRead(
            id=job_model.id,
            client=client_info,
            worker=worker_info,
            service=service_info,
            status=job_model.status,
            cancel_reason=job_model.cancel_reason,
            started_at=job_model.started_at,
            completed_at=job_model.completed_at,
            cancelled_at=job_model.cancelled_at,
            created_at=job_model.created_at,
            updated_at=job_model.updated_at,
        )

    async def _invalidate_job_caches(
        self, job_id: UUID | None, client_id: UUID, worker_id: UUID | None
    ) -> None:
        """Invalidate relevant cache entries related to a job, client, and worker."""
        if not self.cache:
            return

        keys_to_delete = []
        patterns_to_invalidate = []

        if job_id:
            keys_to_delete.append(_cache_key(JOB_DETAIL_NS, job_id))
        patterns_to_invalidate.append(f"{CACHE_PREFIX}{JOB_LIST_USER_NS}:{client_id}:*")
        patterns_to_invalidate.append(f"{CACHE_PREFIX}{CLIENT_JOBS_NS}:{client_id}:*")

        if worker_id:
            patterns_to_invalidate.append(f"{CACHE_PREFIX}{JOB_LIST_USER_NS}:{worker_id}:*")
            patterns_to_invalidate.append(f"{CACHE_PREFIX}{WORKER_JOBS_NS}:{worker_id}:*")

        logger.info(
            f"[CACHE ASYNC JOB] Invalidating job caches for job={job_id}, client={client_id}, worker={worker_id}"
        )
        logger.debug(f"[CACHE ASYNC JOB] Keys to delete: {keys_to_delete}")
        logger.debug(f"[CACHE ASYNC JOB] Patterns to invalidate: {patterns_to_invalidate}")

        try:
            if keys_to_delete:
                await self.cache.delete(*keys_to_delete)
            for pattern in patterns_to_invalidate:
                await _invalidate_pattern(self.cache, pattern)
        except Exception as e:
            logger.error(f"[CACHE ASYNC JOB ERROR] Failed deleting job keys/patterns: {e}")

    # ---------------------------------------------------
    # Job Creation
    # ---------------------------------------------------
    async def create_job(self, client_id: UUID, payload: schemas.JobCreate) -> schemas.JobRead:
        """Client initiates a new job associated with a service and message thread."""
        logger.info(
            f"Client {client_id} creating job for service {payload.service_id} via thread {payload.thread_id}"
        )

        client_user = await self._get_user_or_404(client_id)
        if client_user.role != UserRole.CLIENT:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Only clients can create jobs."
            )

        service_result = await self.db.execute(
            select(ServiceModel)
            .options(selectinload(ServiceModel.worker))
            .filter_by(id=payload.service_id)
        )
        service: ServiceModel | None = service_result.unique().scalar_one_or_none()
        if not service or not service.worker:
            raise HTTPException(status_code=400, detail="Service or service worker not found.")

        worker_id = service.worker_id

        thread_result = await self.db.execute(select(MessageThread).filter_by(id=payload.thread_id))
        thread: MessageThread | None = thread_result.unique().scalar_one_or_none()
        if not thread:
            raise HTTPException(status_code=400, detail="Message thread not found.")

        if thread.job_id:
            existing_job = await self.db.get(models.Job, thread.job_id)
            if existing_job:
                raise HTTPException(
                    status_code=400, detail="A job is already linked to this thread."
                )
            logger.warning(f"Thread {thread.id} has stale job_id {thread.job_id}. Overwriting.")
            thread.job_id = None

        job = models.Job(
            client_id=client_id,
            worker_id=worker_id,
            service_id=payload.service_id,
            status=JobStatus.NEGOTIATING,
        )
        self.db.add(job)
        await self.db.flush()

        thread.job_id = job.id
        self.db.add(thread)

        await self._invalidate_job_caches(job_id=job.id, client_id=client_id, worker_id=worker_id)

        try:
            await self.db.commit()
        except Exception as e:
            logger.error(f"Error committing job creation or thread update: {e}", exc_info=True)
            await self.db.rollback()
            raise HTTPException(status_code=500, detail="Failed to create job or link thread.")

        await self.db.refresh(job, attribute_names=["client", "worker", "service"])
        if job.service:
            await self.db.refresh(job.service, attribute_names=["worker"])

        logger.info(f"Job created successfully: job_id={job.id}, linked to thread_id={thread.id}")
        return self._construct_job_read(job)

    # ---------------------------------------------------
    # Job Lifecycle Actions
    # ---------------------------------------------------
    async def accept_job(self, worker_id: UUID, job_id: UUID) -> schemas.JobRead:
        """Worker accepts a job in 'NEGOTIATING' status."""
        logger.info(f"Worker {worker_id} accepting job {job_id}")
        worker_user = await self._get_user_or_404(worker_id)
        if worker_user.role != UserRole.WORKER:
            raise HTTPException(status_code=403, detail="Only workers can accept jobs.")

        job = await self._get_job_with_relations_or_404(job_id)

        if job.worker_id != worker_id:
            raise HTTPException(status_code=403, detail="Unauthorized to accept this job.")

        if job.status != JobStatus.NEGOTIATING:
            raise HTTPException(status_code=400, detail="Only negotiating jobs can be accepted.")

        job.status = JobStatus.ACCEPTED
        job.started_at = datetime.now(timezone.utc)
        await self._invalidate_job_caches(job.id, job.client_id, worker_id)
        await self.db.commit()
        await self.db.refresh(job, attribute_names=["client", "worker", "service"])
        if job.service:
            await self.db.refresh(job.service, attribute_names=["worker"])
        logger.info(f"Job accepted: job_id={job.id}")
        return self._construct_job_read(job)

    async def reject_job(
        self, worker_id: UUID, job_id: UUID, payload: schemas.JobReject
    ) -> schemas.JobRead:
        """Worker rejects a job and optionally closes the thread."""
        logger.info(f"Worker {worker_id} rejecting job {job_id}")
        worker_user = await self._get_user_or_404(worker_id)
        if worker_user.role != UserRole.WORKER:
            raise HTTPException(status_code=403, detail="Only workers can reject jobs.")

        job = await self._get_job_with_relations_or_404(job_id)

        if job.worker_id != worker_id:
            raise HTTPException(status_code=403, detail="Unauthorized to reject this job.")

        if job.status != JobStatus.NEGOTIATING:
            raise HTTPException(
                status_code=400, detail="Only jobs in NEGOTIATING status can be rejected."
            )

        job.status = JobStatus.REJECTED
        job.cancelled_at = datetime.now(timezone.utc)
        job.cancel_reason = payload.reject_reason

        if job.thread:
            job.thread.is_closed = True
            self.db.add(job.thread)

        await self._invalidate_job_caches(job.id, job.client_id, worker_id)
        await self.db.commit()
        await self.db.refresh(job, attribute_names=["client", "worker", "service", "thread"])
        if job.service:
            await self.db.refresh(job.service, attribute_names=["worker"])
        logger.info(f"Job rejected: job_id={job.id}")
        return self._construct_job_read(job)

    async def complete_job(self, worker_id: UUID, job_id: UUID) -> schemas.JobRead:
        """Worker marks job as completed."""
        logger.info(f"Worker {worker_id} completing job {job_id}")
        worker_user = await self._get_user_or_404(worker_id)
        if worker_user.role != UserRole.WORKER:
            raise HTTPException(status_code=403, detail="Only workers can complete jobs.")

        job = await self._get_job_with_relations_or_404(job_id)

        if job.worker_id != worker_id:
            raise HTTPException(status_code=403, detail="Unauthorized to complete this job.")

        if job.status != JobStatus.ACCEPTED:
            raise HTTPException(status_code=400, detail="Only accepted jobs can be completed.")

        job.status = JobStatus.COMPLETED
        job.completed_at = datetime.now(timezone.utc)
        await self._invalidate_job_caches(job.id, job.client_id, worker_id)
        await self.db.commit()
        await self.db.refresh(job, attribute_names=["client", "worker", "service"])
        if job.service:
            await self.db.refresh(job.service, attribute_names=["worker"])
        logger.info(f"Job completed: job_id={job.id}")
        return self._construct_job_read(job)

    async def cancel_job(self, user_id: UUID, job_id: UUID, cancel_reason: str) -> schemas.JobRead:
        """Client cancels a job."""
        logger.info(f"Client {user_id} cancelling job {job_id}")
        client_user = await self._get_user_or_404(user_id)
        if client_user.role != UserRole.CLIENT:
            raise HTTPException(status_code=403, detail="Only clients can cancel jobs.")

        job = await self._get_job_with_relations_or_404(job_id)

        if job.client_id != user_id:
            raise HTTPException(status_code=403, detail="Unauthorized to cancel this job.")

        if job.status in {JobStatus.COMPLETED, JobStatus.FINALIZED, JobStatus.CANCELLED}:
            raise HTTPException(status_code=400, detail="Cannot cancel job in its current state.")

        job.status = JobStatus.CANCELLED
        job.cancelled_at = datetime.now(timezone.utc)
        job.cancel_reason = cancel_reason
        await self._invalidate_job_caches(job.id, job.client_id, job.worker_id)
        await self.db.commit()
        await self.db.refresh(job, attribute_names=["client", "worker", "service"])
        if job.service:
            await self.db.refresh(job.service, attribute_names=["worker"])
        logger.info(f"Job cancelled: job_id={job.id}")
        return self._construct_job_read(job)

    # ---------------------------------------------------
    # Job Retrieval
    # ---------------------------------------------------
    # async def get_all_jobs_for_user(
    #     self, user_id: UUID, skip: int = 0, limit: int = 100
    # ) -> tuple[list[schemas.JobRead], int]:
    #     """Return jobs (as client or worker) with pagination and caching."""
    #     cache_key = _paginated_cache_key(JOB_LIST_USER_NS, user_id, skip, limit)
    #     if self.cache:
    #         try:
    #             cached_data = await self.cache.get(cache_key)
    #             if cached_data:
    #                 logger.info(
    #                     f"[CACHE ASYNC HIT] Job list for user {user_id} (skip={skip}, limit={limit})"
    #                 )
    #                 payload = json.loads(cached_data)
    #                 items = [schemas.JobRead.model_validate(i) for i in payload["items"]]
    #                 return items, payload["total_count"]
    #         except Exception as e:
    #             logger.error(f"[CACHE ASYNC READ ERROR] Job list {user_id}: {e}")

    #     logger.info(
    #         f"[CACHE ASYNC MISS] Fetching job list for user_id={user_id} from DB (skip={skip}, limit={limit})"
    #     )

    #     base_stmt = select(models.Job).filter(
    #         (models.Job.client_id == user_id) | (models.Job.worker_id == user_id)
    #     )

    #     count_stmt = select(func.count()).select_from(base_stmt.subquery())
    #     count_result = await self.db.execute(count_stmt)
    #     count = count_result.scalar_one()

    #     data_stmt = (
    #         base_stmt.options(
    #             selectinload(models.Job.client),
    #             selectinload(models.Job.worker),
    #             selectinload(models.Job.service).selectinload(ServiceModel.worker),
    #         )
    #         .order_by(models.Job.created_at.desc())
    #         .offset(skip)
    #         .limit(limit)
    #     )
    #     rows_result = await self.db.execute(data_stmt)
    #     job_models = rows_result.unique().scalars().all()

    #     items = [self._construct_job_read(j) for j in job_models]

    #     if self.cache:
    #         try:
    #             serializable_items = [i.model_dump(mode='json') for i in items]
    #             await self.cache.set(
    #                 cache_key,
    #                 json.dumps({'items': serializable_items, 'total_count': count}),
    #                 ex=DEFAULT_CACHE_TTL,
    #             )
    #             logger.info(f"[CACHE ASYNC SET] Job list for user {user_id}")
    #         except Exception as e:
    #             logger.error(f"[CACHE ASYNC WRITE ERROR] Job list {user_id}: {e}")
    #     return items, count

    # async def get_job_detail(self, user_id: UUID, job_id: UUID) -> schemas.JobRead:
    #     """Return job detail only if user is authorized (client or worker), with embedded details."""
    #     cache_key = _cache_key(JOB_DETAIL_NS, job_id)
    #     if self.cache:
    #         try:
    #             cached_data = await self.cache.get(cache_key)
    #             if cached_data:
    #                 logger.info(f"[CACHE ASYNC HIT] Job detail for job {job_id}")
    #                 job_read_cached = schemas.JobRead.model_validate_json(cached_data)
    #                 if not (
    #                     (job_read_cached.client and job_read_cached.client.id == user_id)
    #                     or (job_read_cached.worker and job_read_cached.worker.id == user_id)
    #                 ):
    #                     logger.warning(
    #                         f"[CACHE ASYNC AUTH] User {user_id} unauthorized for cached job {job_id}"
    #                     )
    #                     raise HTTPException(status_code=403, detail="Unauthorized access to job.")
    #                 return job_read_cached
    #         except Exception as e:
    #             logger.error(f"[CACHE ASYNC READ ERROR] Job detail {job_id}: {e}")

    #     logger.info(f"[CACHE ASYNC MISS] Fetching job detail for job {job_id} from DB")

    #     job_model = await self._get_job_with_relations_or_404(job_id)

    #     if not ((job_model.client_id == user_id) or (job_model.worker_id == user_id)):
    #         raise HTTPException(status_code=403, detail="Unauthorized to view this job.")

    #     job_read = self._construct_job_read(job_model)

    #     if self.cache:
    #         try:
    #             await self.cache.set(cache_key, job_read.model_dump_json(), ex=DEFAULT_CACHE_TTL)
    #             logger.info(f"[CACHE ASYNC SET] Job detail for job {job_id}")
    #         except Exception as e:
    #             logger.error(f"[CACHE ASYNC WRITE ERROR] Job detail {job_id}: {e}")
    #     return job_read
