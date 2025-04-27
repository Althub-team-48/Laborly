"""
backend/app/review/routes.py

Review Routes
Defines API endpoints related to job reviews:
- Submit a new review for a completed job (Authenticated Client)
- Fetch all reviews received by a worker (Public)
- Fetch all reviews submitted by the current client (Authenticated Client)
- Get a review summary (average rating and count) for a worker (Public)
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_with_role, PaginationParams
from app.core.limiter import limiter
from app.core.schemas import PaginatedResponse
from app.database.enums import UserRole
from app.database.models import User
from app.database.session import get_db
from app.review import schemas
from app.review.services import ReviewService

router = APIRouter(prefix="/reviews", tags=["Reviews"])

DBDep = Annotated[AsyncSession, Depends(get_db)]
AuthenticatedClientDep = Annotated[User, Depends(get_current_user_with_role(UserRole.CLIENT))]


# ----------------------------------------------------
# Public Review Endpoints
# ----------------------------------------------------
@router.get(
    "/worker/{worker_id}/public",
    response_model=PaginatedResponse[schemas.PublicReviewRead],
    status_code=status.HTTP_200_OK,
    summary="Public Worker Reviews",
    description="Fetch all reviews received by a specific worker (publicly accessible).",
)
@limiter.limit("10/minute")
async def get_public_worker_reviews(
    request: Request,
    worker_id: UUID,
    db: DBDep,
    pagination: PaginationParams = Depends(),
) -> PaginatedResponse[schemas.PublicReviewRead]:
    """Retrieve all public reviews for a specific worker with pagination."""
    reviews, total_count = await ReviewService(db).get_reviews_for_worker(
        worker_id=worker_id, skip=pagination.skip, limit=pagination.limit
    )
    return PaginatedResponse(
        total_count=total_count,
        has_next_page=(pagination.skip + pagination.limit) < total_count,
        items=[
            schemas.PublicReviewRead.model_validate(review, from_attributes=True)
            for review in reviews
        ],
    )


@router.get(
    "/summary/{worker_id}",
    response_model=schemas.WorkerReviewSummary,
    status_code=status.HTTP_200_OK,
    summary="Worker Review Summary",
    description="Return average rating and total number of reviews for a specific worker (publicly accessible).",
)
@limiter.limit("10/minute")
async def get_worker_review_summary(
    request: Request,
    worker_id: UUID,
    db: DBDep,
) -> schemas.WorkerReviewSummary:
    """Retrieve average rating and total reviews count for a specific worker."""
    return await ReviewService(db).get_review_summary(worker_id=worker_id)


# ----------------------------------------------------
# Authenticated Review Endpoints (Client)
# ----------------------------------------------------
@router.post(
    "/{job_id}",
    response_model=schemas.ReviewRead,
    status_code=status.HTTP_201_CREATED,
    summary="Submit Review",
    description="Submit a review for a completed job (authenticated client only).",
)
@limiter.limit("5/minute")
async def submit_review(
    request: Request,
    job_id: UUID,
    payload: schemas.ReviewWrite,
    db: DBDep,
    current_user: AuthenticatedClientDep,
) -> schemas.ReviewRead:
    """Allow authenticated client to submit a review for a job."""
    review = await ReviewService(db).submit_review(
        job_id=job_id,
        reviewer_id=current_user.id,
        data=payload,
    )
    return schemas.ReviewRead.model_validate(review, from_attributes=True)


@router.get(
    "/my",
    response_model=PaginatedResponse[schemas.ReviewRead],
    status_code=status.HTTP_200_OK,
    summary="My Submitted Reviews",
    description="Retrieve all reviews submitted by the authenticated client.",
)
@limiter.limit("5/minute")
async def get_my_reviews(
    request: Request,
    db: DBDep,
    current_user: AuthenticatedClientDep,
    pagination: PaginationParams = Depends(),
) -> PaginatedResponse[schemas.ReviewRead]:
    """Retrieve all reviews submitted by the authenticated client with pagination."""
    reviews, total_count = await ReviewService(db).get_reviews_by_client(
        client_id=current_user.id, skip=pagination.skip, limit=pagination.limit
    )
    return PaginatedResponse(
        total_count=total_count,
        has_next_page=(pagination.skip + pagination.limit) < total_count,
        items=[
            schemas.ReviewRead.model_validate(review, from_attributes=True) for review in reviews
        ],
    )
