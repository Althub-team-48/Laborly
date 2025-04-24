"""
review/routes.py

Defines API endpoints related to job reviews:
- Submit a new review for a completed job
- Fetch all reviews received by a worker
- Fetch all reviews submitted by the current client
- Get a summary (average rating and count) for a specific worker
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_with_role, get_db
from app.core.limiter import limiter
from app.database.models import User
from app.database.enums import UserRole
from app.review import schemas
from app.review.services import ReviewService

router = APIRouter(prefix="/reviews", tags=["Reviews"])

client_dependency = get_current_user_with_role(UserRole.CLIENT)


@router.post(
    "/{job_id}",
    response_model=schemas.ReviewRead,
    status_code=status.HTTP_201_CREATED,
    summary="Submit Review",
    description="Allows a client to submit a review for a completed job. Each job can have only one review.",
)
@limiter.limit("5/minute")
async def submit_review(
    request: Request,
    job_id: UUID,
    payload: schemas.ReviewWrite,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(client_dependency),
) -> schemas.ReviewRead:
    review = await ReviewService(db).submit_review(
        job_id=job_id, reviewer_id=current_user.id, data=payload
    )
    return schemas.ReviewRead.model_validate(review, from_attributes=True)


@router.get(
    "/worker/{worker_id}",
    response_model=list[schemas.ReviewRead],
    status_code=status.HTTP_200_OK,
    summary="Worker Reviews",
    description="Fetches all reviews received by a specific worker.",
)
@limiter.limit("5/minute")
async def get_worker_reviews(
    request: Request,
    worker_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> list[schemas.ReviewRead]:
    reviews = await ReviewService(db).get_reviews_for_worker(worker_id=worker_id)
    return [schemas.ReviewRead.model_validate(r, from_attributes=True) for r in reviews]


@router.get(
    "/my",
    response_model=list[schemas.ReviewRead],
    status_code=status.HTTP_200_OK,
    summary="My Submitted Reviews",
    description="Returns all reviews submitted by the currently authenticated client.",
)
@limiter.limit("5/minute")
async def get_my_reviews(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(client_dependency),
) -> list[schemas.ReviewRead]:
    reviews = await ReviewService(db).get_reviews_by_client(client_id=current_user.id)
    return [schemas.ReviewRead.model_validate(r, from_attributes=True) for r in reviews]


@router.get(
    "/summary/{worker_id}",
    response_model=schemas.WorkerReviewSummary,
    status_code=status.HTTP_200_OK,
    summary="Worker Review Summary",
    description="Returns the average rating and total number of reviews for a specific worker.",
)
@limiter.limit("5/minute")
async def get_worker_review_summary(
    request: Request,
    worker_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> schemas.WorkerReviewSummary:
    return await ReviewService(db).get_review_summary(worker_id=worker_id)
