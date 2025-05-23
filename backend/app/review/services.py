"""
backend/app/review/services.py

Review Services
Business logic for handling job reviews:
- Submit a new review (one per job) (Authenticated Client)
- Retrieve reviews for a specific worker or by a client (Public/Authenticated)
- Compute average rating and review count summary for a worker (Public)
"""

import json
import logging
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.blacklist import redis_client
from app.worker.services import (
    _cache_key,
    _paginated_cache_key,
    CACHE_PREFIX,
    DEFAULT_CACHE_TTL,
)
from app.database.models import User
from app.job.models import Job
from app.review import models, schemas
from app.job.schemas import JobServiceInfo


logger = logging.getLogger(__name__)

# --- Cache Namespaces ---
REVIEW_LIST_WORKER_NS = "review:list:worker"
REVIEW_LIST_CLIENT_NS = "review:list:client"
REVIEW_SUMMARY_WORKER_NS = "review:summary:worker"
ADMIN_FLAGGED_REVIEWS_NS = "admin:flagged_reviews"


# -------------------------------------------------
# --- Utility: Pattern-based Cache Invalidation ---
# -------------------------------------------------
async def _invalidate_pattern(cache: Any, pattern: str) -> None:
    """Delete Redis keys matching the given pattern."""
    if not cache:
        return
    logger.debug(f"[CACHE ASYNC REVIEW] Scanning pattern: {pattern}")
    deleted = 0
    try:
        if not redis_client:
            logger.warning(
                "[CACHE ASYNC REVIEW] Redis client not available for pattern invalidation."
            )
            return
        async for key in redis_client.scan_iter(match=pattern):
            await redis_client.delete(key)
            deleted += 1
        logger.info(f"[CACHE ASYNC REVIEW] Deleted {deleted} keys matching pattern {pattern}")
    except Exception as e:
        logger.error(f"[CACHE ASYNC REVIEW ERROR] Failed pattern deletion for {pattern}: {e}")


class ReviewService:
    """Service layer for managing job reviews with caching."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize the service with a database session and cache client."""
        self.db = db
        self.cache = redis_client
        if not self.cache:
            logger.warning("[CACHE ASYNC REVIEW] Redis client not configured, caching disabled.")

    def _construct_review_client_info(self, client_user: User) -> schemas.ReviewClientInfo:
        return schemas.ReviewClientInfo.model_validate(client_user)

    def _construct_review_worker_info(self, worker_user: User) -> schemas.ReviewWorkerInfo:
        return schemas.ReviewWorkerInfo.model_validate(worker_user)

    def _construct_review_job_info(self, job_model: Job) -> schemas.ReviewJobInfo:
        service_info: JobServiceInfo | None = None
        if job_model.service:
            service_info = JobServiceInfo.model_validate(job_model.service)
        return schemas.ReviewJobInfo(id=job_model.id, status=job_model.status, service=service_info)

    def _construct_review_read_response(self, review_model: models.Review) -> schemas.ReviewRead:
        """Helper to build the ReviewRead response with embedded details."""
        if not review_model.client or not review_model.worker or not review_model.job:
            raise ValueError(
                "Review model is missing required related entities (client, worker, or job)."
            )

        client_info = self._construct_review_client_info(review_model.client)
        worker_info = self._construct_review_worker_info(review_model.worker)
        job_info = self._construct_review_job_info(review_model.job)

        return schemas.ReviewRead(
            id=review_model.id,
            client=client_info,
            worker=worker_info,
            job=job_info,
            rating=review_model.rating,
            text=review_model.review_text,
            is_flagged=review_model.is_flagged,
            created_at=review_model.created_at,
        )

    def _construct_public_review_read_response(
        self, review_model: models.Review
    ) -> schemas.PublicReviewRead:
        """Helper to build the PublicReviewRead response with embedded details."""
        if not review_model.client or not review_model.worker or not review_model.job:
            raise ValueError("Review model is missing required related entities for public view.")

        client_info = self._construct_review_client_info(review_model.client)
        worker_info = self._construct_review_worker_info(review_model.worker)
        job_info = self._construct_review_job_info(review_model.job)

        return schemas.PublicReviewRead(
            id=review_model.id,
            client=client_info,
            worker=worker_info,
            job=job_info,
            rating=review_model.rating,
            text=review_model.review_text,
            created_at=review_model.created_at,
        )

    async def _invalidate_review_caches(self, worker_id: UUID, client_id: UUID) -> None:
        """Invalidate relevant review list and summary caches."""
        if not self.cache:
            return

        patterns_to_invalidate = [
            f"{CACHE_PREFIX}{REVIEW_LIST_WORKER_NS}:{worker_id}:*",
            f"{CACHE_PREFIX}{REVIEW_LIST_CLIENT_NS}:{client_id}:*",
            f"{CACHE_PREFIX}{ADMIN_FLAGGED_REVIEWS_NS}:*",
        ]
        keys_to_delete = [_cache_key(REVIEW_SUMMARY_WORKER_NS, worker_id)]

        logger.info(
            f"[CACHE ASYNC REVIEW] Invalidating review caches for worker={worker_id}, client={client_id}"
        )
        logger.debug(f"[CACHE ASYNC REVIEW] Keys to delete: {keys_to_delete}")
        logger.debug(f"[CACHE ASYNC REVIEW] Patterns to invalidate: {patterns_to_invalidate}")

        try:
            if keys_to_delete:
                await self.cache.delete(*keys_to_delete)
            for pattern in patterns_to_invalidate:
                await _invalidate_pattern(self.cache, pattern)
        except Exception as e:
            logger.error(f"[CACHE ASYNC REVIEW ERROR] Failed deleting review keys/patterns: {e}")

    # ---------------------------------------------------
    # Review Submission
    # ---------------------------------------------------
    async def submit_review(
        self, job_id: UUID, reviewer_id: UUID, data: schemas.ReviewWrite
    ) -> schemas.ReviewRead:
        """
        Submit a review for a completed job.
        Ensures the job belongs to the reviewer and has not already been reviewed.
        Invalidates relevant caches.
        """
        logger.info(f"[SUBMIT] Client {reviewer_id} submitting review for job {job_id}")

        job_result = await self.db.execute(
            select(Job)
            .options(
                selectinload(Job.client),
                selectinload(Job.worker),
                selectinload(Job.service),
            )
            .filter_by(id=job_id, client_id=reviewer_id)
        )
        job = job_result.unique().scalar_one_or_none()

        if not job:
            logger.warning(
                f"[SUBMIT] Unauthorized or job not found: job_id={job_id}, client_id={reviewer_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found or you are not authorized to review it.",
            )

        if not job.worker_id or not job.worker:
            logger.error(f"[SUBMIT] Job {job_id} has no worker assigned, cannot submit review.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot review a job with no assigned worker.",
            )

        existing_review_result = await self.db.execute(
            select(models.Review).filter_by(job_id=job_id)
        )
        if existing_review_result.scalars().first():
            logger.warning(f"[SUBMIT] Duplicate review attempt: job_id={job_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Review already submitted for this job",
            )

        review = models.Review(
            client_id=reviewer_id,
            worker_id=job.worker_id,
            job_id=job_id,
            rating=data.rating,
            review_text=data.text,
        )
        self.db.add(review)
        await self._invalidate_review_caches(worker_id=job.worker_id, client_id=reviewer_id)

        try:
            await self.db.commit()
            await self.db.refresh(review, attribute_names=["client", "worker", "job"])
            if review.job and review.job.service:
                await self.db.refresh(review.job.service)

        except Exception as e:
            await self.db.rollback()
            logger.error(f"[SUBMIT] Failed to commit review: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to submit review.")

        logger.info(f"[SUBMIT] Review created successfully: review_id={review.id}")
        return self._construct_review_read_response(review)

    # ---------------------------------------------------
    # Review Retrieval
    # ---------------------------------------------------
    async def get_reviews_for_worker(
        self, worker_id: UUID, skip: int = 0, limit: int = 100
    ) -> tuple[list[schemas.PublicReviewRead], int]:
        """
        Fetch all reviews received by a specific worker with pagination and cache support.
        Returns public view of reviews.
        """
        cache_key = _paginated_cache_key(REVIEW_LIST_WORKER_NS, worker_id, skip, limit)
        if self.cache:
            try:
                cached_data = await self.cache.get(cache_key)
                if cached_data:
                    logger.info(
                        f"[CACHE ASYNC HIT] Worker review list {worker_id} (skip={skip}, limit={limit})"
                    )
                    payload = json.loads(cached_data)
                    items = [schemas.PublicReviewRead.model_validate(i) for i in payload["items"]]
                    return items, payload["total_count"]
            except Exception as e:
                logger.error(f"[CACHE ASYNC READ ERROR] Worker review list {worker_id}: {e}")

        logger.info(f"[CACHE ASYNC MISS] Retrieving reviews for worker_id={worker_id} from DB")

        count_stmt = select(func.count(models.Review.id)).filter(
            models.Review.worker_id == worker_id, models.Review.is_flagged.is_(False)
        )
        total_count_result = await self.db.execute(count_stmt)
        total_count = total_count_result.scalar_one()

        stmt = (
            select(models.Review)
            .options(
                selectinload(models.Review.client),
                selectinload(models.Review.worker),
                selectinload(models.Review.job).selectinload(Job.service),
            )
            .filter(models.Review.worker_id == worker_id, models.Review.is_flagged.is_(False))
            .order_by(models.Review.created_at.desc())
            .offset(skip)
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        reviews_db = list(result.unique().scalars().all())
        pydantic_reviews = [self._construct_public_review_read_response(r) for r in reviews_db]

        if self.cache:
            try:
                serializable_items = [r.model_dump(mode='json') for r in pydantic_reviews]
                payload_to_cache = json.dumps(
                    {'items': serializable_items, 'total_count': total_count}
                )
                await self.cache.set(cache_key, payload_to_cache, ex=DEFAULT_CACHE_TTL)
                logger.info(
                    f"[CACHE ASYNC SET] Worker review list {worker_id} (skip={skip}, limit={limit})"
                )
            except Exception as e:
                logger.error(f"[CACHE ASYNC WRITE ERROR] Worker review list {worker_id}: {e}")

        return pydantic_reviews, total_count

    async def get_reviews_by_client(
        self, client_id: UUID, skip: int = 0, limit: int = 100
    ) -> tuple[list[schemas.ReviewRead], int]:
        """
        Fetch all reviews submitted by a specific client with pagination and cache support.
        Returns full review details including flagged status.
        """
        cache_key = _paginated_cache_key(REVIEW_LIST_CLIENT_NS, client_id, skip, limit)
        if self.cache:
            try:
                cached_data = await self.cache.get(cache_key)
                if cached_data:
                    logger.info(
                        f"[CACHE ASYNC HIT] Client review list {client_id} (skip={skip}, limit={limit})"
                    )
                    payload = json.loads(cached_data)
                    items = [schemas.ReviewRead.model_validate(i) for i in payload["items"]]
                    return items, payload["total_count"]
            except Exception as e:
                logger.error(f"[CACHE ASYNC READ ERROR] Client review list {client_id}: {e}")

        logger.info(f"[CACHE ASYNC MISS] Retrieving reviews by client_id={client_id} from DB")

        count_stmt = select(func.count(models.Review.id)).filter(
            models.Review.client_id == client_id
        )
        total_count_result = await self.db.execute(count_stmt)
        total_count = total_count_result.scalar_one()

        stmt = (
            select(models.Review)
            .options(
                selectinload(models.Review.client),
                selectinload(models.Review.worker),
                selectinload(models.Review.job).selectinload(Job.service),
            )
            .filter_by(client_id=client_id)
            .order_by(models.Review.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        reviews_db = list(result.unique().scalars().all())
        pydantic_reviews = [self._construct_review_read_response(r) for r in reviews_db]

        if self.cache:
            try:
                serializable_items = [r.model_dump(mode='json') for r in pydantic_reviews]
                payload_to_cache = json.dumps(
                    {'items': serializable_items, 'total_count': total_count}
                )
                await self.cache.set(cache_key, payload_to_cache, ex=DEFAULT_CACHE_TTL)
                logger.info(
                    f"[CACHE ASYNC SET] Client review list {client_id} (skip={skip}, limit={limit})"
                )
            except Exception as e:
                logger.error(f"[CACHE ASYNC WRITE ERROR] Client review list {client_id}: {e}")

        return pydantic_reviews, total_count

    # ---------------------------------------------------
    # Review Summary Calculation
    # ---------------------------------------------------
    async def get_review_summary(self, worker_id: UUID) -> schemas.WorkerReviewSummary:
        """
        Calculate average rating and total review count for a worker, with cache support.
        Considers only non-flagged reviews for public summary.
        """
        cache_key = _cache_key(REVIEW_SUMMARY_WORKER_NS, worker_id)
        if self.cache:
            try:
                cached_data = await self.cache.get(cache_key)
                if cached_data:
                    logger.info(f"[CACHE ASYNC HIT] Worker review summary {worker_id}")
                    return schemas.WorkerReviewSummary.model_validate_json(cached_data)
            except Exception as e:
                logger.error(f"[CACHE ASYNC READ ERROR] Worker review summary {worker_id}: {e}")

        logger.info(
            f"[CACHE ASYNC MISS] Calculating review summary for worker_id={worker_id} from DB"
        )

        stmt = select(
            func.coalesce(func.avg(models.Review.rating), 0.0).label(
                "average_rating"
            ),  # Added labels
            func.count(models.Review.id).label("total_reviews"),
        ).filter(models.Review.worker_id == worker_id, models.Review.is_flagged.is_(False))

        result = await self.db.execute(stmt)
        summary_data = result.first()
        avg_rating = summary_data.average_rating if summary_data else 0.0
        total_reviews = summary_data.total_reviews if summary_data else 0

        avg_rating_float = float(avg_rating)
        total_reviews_int = int(total_reviews)

        summary = schemas.WorkerReviewSummary(
            average_rating=round(avg_rating_float, 2),
            total_reviews=total_reviews_int,
        )

        if self.cache:
            try:
                await self.cache.set(cache_key, summary.model_dump_json(), ex=DEFAULT_CACHE_TTL)
                logger.info(f"[CACHE ASYNC SET] Worker review summary {worker_id}")
            except Exception as e:
                logger.error(f"[CACHE ASYNC WRITE ERROR] Worker review summary {worker_id}: {e}")

        logger.debug(f"[SUMMARY] Computed summary: {summary}")
        return summary
