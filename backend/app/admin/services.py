"""
backend/app/admin/services.py

Admin Service Layer (Corrected Cache Invalidation)
Provides administrative capabilities including user management,
KYC approval/rejection, review moderation, and role-based user listing.
Leverages Redis caching for performance and consistency.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin import schemas
from app.core.blacklist import redis_client
from app.core.upload import generate_presigned_url, get_s3_key_from_url
from app.database.enums import KYCStatus, UserRole
from app.database.models import KYC, User
from app.review.models import Review
from app.worker.models import WorkerProfile
from app.worker.services import (
    _cache_key,
    _paginated_cache_key,
    DEFAULT_CACHE_TTL,
    WorkerService,
    CACHE_PREFIX,
)

logger = logging.getLogger(__name__)

ADMIN_PENDING_KYC_NS = "admin:pending_kyc"
ADMIN_KYC_DETAIL_NS = "admin:kyc_detail"
ADMIN_FLAGGED_REVIEWS_NS = "admin:flagged_reviews"
ADMIN_USER_LIST_NS = "admin:user_list"
ADMIN_USER_DETAIL_NS = "admin:user_detail"


# ---------------------------------------------------
# Cache Invalidation Helpers
# ---------------------------------------------------
async def _invalidate_pattern(cache: Any, pattern: str) -> None:
    """Delete keys matching a given pattern using the full key structure."""
    if not cache:
        return
    logger.debug(f"[CACHE ASYNC ADMIN] Scanning pattern: {pattern}")
    keys_deleted_count = 0
    try:
        async for key in cache.scan_iter(match=pattern):
            await cache.delete(key)
            keys_deleted_count += 1
        logger.info(
            f"[CACHE ASYNC ADMIN] Deleted {keys_deleted_count} keys matching pattern {pattern}"
        )
    except Exception as e:
        logger.error(f"[CACHE ASYNC ADMIN ERROR] Failed pattern deletion for {pattern}: {e}")


# ---------------------------------------------------
# AdminService
# ---------------------------------------------------
class AdminService:
    """Provides admin capabilities like KYC handling, user banning, and review moderation."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.cache = redis_client
        self.worker_service = WorkerService(db)

    async def _invalidate_admin_lists(self) -> None:
        """Invalidate admin-level list cache entries."""
        if not self.cache:
            return
        patterns = [
            f"{CACHE_PREFIX}{ADMIN_PENDING_KYC_NS}:*",
            f"{CACHE_PREFIX}{ADMIN_FLAGGED_REVIEWS_NS}:*",
            f"{CACHE_PREFIX}{ADMIN_USER_LIST_NS}:*",
        ]
        logger.info(f"[CACHE ASYNC ADMIN] Invalidating list caches: {patterns}")
        for pattern in patterns:
            await _invalidate_pattern(self.cache, pattern)

    async def _invalidate_kyc(self, user_id: UUID) -> None:
        """Invalidate a specific user's KYC cache."""
        if not self.cache:
            return
        keys_to_delete = [_cache_key(ADMIN_KYC_DETAIL_NS, user_id)]
        logger.info(f"[CACHE ASYNC ADMIN] Invalidating KYC caches for user {user_id}")
        try:
            if keys_to_delete:
                await self.cache.delete(*keys_to_delete)
            await self.worker_service._invalidate_worker_caches(user_id)
            await _invalidate_pattern(self.cache, f"{CACHE_PREFIX}{ADMIN_PENDING_KYC_NS}:*")
        except Exception as e:
            logger.error(f"[CACHE ASYNC ADMIN ERROR] Failed deleting KYC keys for {user_id}: {e}")

    async def _invalidate_user(self, user_id: UUID) -> None:
        """Invalidate admin user list and user detail cache."""
        if not self.cache:
            return
        keys_to_delete = [_cache_key(ADMIN_USER_DETAIL_NS, user_id)]
        logger.info(f"[CACHE ASYNC ADMIN] Invalidating user caches for user {user_id}")
        try:
            if keys_to_delete:
                await self.cache.delete(*keys_to_delete)
            await _invalidate_pattern(self.cache, f"{CACHE_PREFIX}{ADMIN_USER_LIST_NS}:*")
            await self.worker_service._invalidate_worker_caches(user_id)
        except Exception as e:
            logger.error(f"[CACHE ASYNC ADMIN ERROR] Failed deleting user keys for {user_id}: {e}")

    async def _invalidate_reviews(self) -> None:
        """Clear review-related admin cache."""
        if not self.cache:
            return
        await _invalidate_pattern(self.cache, f"{CACHE_PREFIX}{ADMIN_FLAGGED_REVIEWS_NS}:*")

    # ---------------------------------------------------
    # Internal DB Helpers
    # ---------------------------------------------------
    async def _get_kyc_or_404(self, user_id: UUID) -> KYC:
        stmt = select(KYC).filter(KYC.user_id == user_id)
        result = await self.db.execute(stmt)
        kyc_record = result.scalar_one_or_none()
        if not kyc_record:
            logger.error(f"[KYC] Record not found for user_id={user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="KYC record not found."
            )
        return kyc_record

    async def _get_user_or_404(self, user_id: UUID) -> User:
        stmt = select(User).filter(User.id == user_id)
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            logger.error(f"[USER] Record not found for user_id={user_id}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
        return user

    # ---------------------------------------------------
    # KYC Management
    # ---------------------------------------------------
    async def list_pending_kyc(
        self, skip: int = 0, limit: int = 100
    ) -> tuple[list[schemas.KYCPendingListItem], int]:
        """List KYC applications that are pending review."""
        key = _paginated_cache_key(ADMIN_PENDING_KYC_NS, "all", skip, limit)
        if self.cache:
            try:
                data = await self.cache.get(key)
                if data:
                    logger.info(
                        f"[CACHE ASYNC HIT] Admin pending KYC list (skip={skip}, limit={limit})"
                    )
                    payload = json.loads(data)
                    items = [schemas.KYCPendingListItem.model_validate(i) for i in payload["items"]]
                    return items, payload["total_count"]
            except Exception as e:
                logger.error(f"[CACHE ASYNC READ ERROR] Failed reading {key}: {e}")

        logger.info(
            f"[CACHE ASYNC MISS] Fetching pending KYC list from DB (skip={skip}, limit={limit})"
        )
        count = (
            await self.db.execute(
                select(func.count(KYC.id)).filter(KYC.status == KYCStatus.PENDING)
            )
        ).scalar_one()
        rows = await self.db.execute(
            select(KYC)
            .filter(KYC.status == KYCStatus.PENDING)
            .order_by(KYC.submitted_at.asc())
            .offset(skip)
            .limit(limit)
        )
        items = [schemas.KYCPendingListItem.model_validate(r) for r in rows.scalars().all()]

        if self.cache:
            try:
                await self.cache.set(
                    key,
                    json.dumps(
                        {"items": [i.model_dump(mode='json') for i in items], "total_count": count}
                    ),
                    ex=DEFAULT_CACHE_TTL,
                )
                logger.info(
                    f"[CACHE ASYNC SET] Admin pending KYC list (skip={skip}, limit={limit})"
                )
            except Exception as e:
                logger.error(f"[CACHE ASYNC WRITE ERROR] Failed writing {key}: {e}")

        return items, count

    async def get_kyc_detail(self, user_id: UUID) -> schemas.KYCDetailAdminView:
        """Retrieve detailed KYC information for a user."""
        key = _cache_key(ADMIN_KYC_DETAIL_NS, user_id)
        if self.cache:
            try:
                data = await self.cache.get(key)
                if data:
                    logger.info(f"[CACHE ASYNC HIT] Admin KYC detail for {user_id}")
                    return schemas.KYCDetailAdminView.model_validate_json(data)
            except Exception as e:
                logger.error(f"[CACHE ASYNC READ ERROR] Failed reading {key}: {e}")

        logger.info(f"[CACHE ASYNC MISS] Fetching KYC details from DB for user_id={user_id}")
        record = (
            await self.db.execute(select(KYC).filter(KYC.user_id == user_id))
        ).scalar_one_or_none()
        if not record:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="KYC not found")
        view = schemas.KYCDetailAdminView.model_validate(record)

        if self.cache:
            try:
                await self.cache.set(key, view.model_dump_json(), ex=DEFAULT_CACHE_TTL)
                logger.info(f"[CACHE ASYNC SET] Admin KYC detail for {user_id}")
            except Exception as e:
                logger.error(f"[CACHE ASYNC WRITE ERROR] Failed writing {key}: {e}")
        return view

    async def _change_kyc_status(
        self, user_id: UUID, stat: KYCStatus
    ) -> schemas.KYCReviewActionResponse:
        """Internal helper to approve or reject KYC."""
        await self._invalidate_kyc(user_id)
        kyc = (
            await self.db.execute(select(KYC).filter(KYC.user_id == user_id))
        ).scalar_one_or_none()
        if not kyc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="KYC not found")
        if kyc.status == stat:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=f"KYC already {stat.name.lower()}"
            )
        profile = (
            await self.db.execute(select(WorkerProfile).filter_by(user_id=user_id))
        ).scalar_one_or_none()
        if profile:
            profile.is_kyc_verified = stat == KYCStatus.APPROVED
        kyc.status = stat
        kyc.reviewed_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(kyc)
        if profile:
            await self.db.refresh(profile)
        response = schemas.KYCReviewActionResponse.model_validate(kyc)
        if self.cache:
            try:
                detail_view = schemas.KYCDetailAdminView.model_validate(kyc)
                await self.cache.set(
                    _cache_key(ADMIN_KYC_DETAIL_NS, user_id),
                    detail_view.model_dump_json(),
                    ex=DEFAULT_CACHE_TTL,
                )
            except Exception as e:
                logger.error(
                    f"[CACHE ASYNC WRITE ERROR] Post-KYC change cache set failed for {user_id}: {e}"
                )
        return response

    async def approve_kyc(self, user_id: UUID) -> schemas.KYCReviewActionResponse:
        """Approve a pending KYC application."""
        return await self._change_kyc_status(user_id, KYCStatus.APPROVED)

    async def reject_kyc(self, user_id: UUID) -> schemas.KYCReviewActionResponse:
        """Reject a KYC application."""
        return await self._change_kyc_status(user_id, KYCStatus.REJECTED)

    async def get_kyc_presigned_url(
        self, user_id: UUID, doc_type: Literal["document", "selfie"]
    ) -> str:
        record = (
            await self.db.execute(select(KYC).filter(KYC.user_id == user_id))
        ).scalar_one_or_none()
        if not record:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="KYC not found")
        url = record.document_path if doc_type == "document" else record.selfie_path
        if not url:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Path not set")
        key = get_s3_key_from_url(url)
        if not key:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid S3 key")
        presigned = generate_presigned_url(key)
        if not presigned:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to generate URL"
            )
        return presigned

    # ---------------------------------------------------
    # User Management
    # ---------------------------------------------------
    async def _change_user_flag(self, user_id: UUID, **flags: Any) -> schemas.AdminUserView:
        """Internal utility to update user flags like banned, frozen, active."""
        await self._invalidate_user(user_id)
        user = (await self.db.execute(select(User).filter(User.id == user_id))).scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        user_changed = False
        for attr, val in flags.items():
            if hasattr(user, attr) and getattr(user, attr) != val:
                setattr(user, attr, val)
                user_changed = True

        if 'is_banned' in flags and flags.get('is_banned'):
            if not user.is_active:
                user_changed = True
            user.is_active = False
            if not user.is_frozen:
                user_changed = True
            user.is_frozen = False
        elif 'is_frozen' in flags:
            if flags.get('is_frozen'):
                if user.is_active:
                    user_changed = True
                user.is_active = False
            else:
                if not user.is_banned and not user.is_active:
                    user.is_active = True
                    user_changed = True
        elif 'is_banned' in flags and not flags.get('is_banned'):
            if not user.is_frozen and not user.is_active:
                user.is_active = True
                user_changed = True

        if not user_changed:
            logger.info(f"No actual flag changes needed for user {user_id}")
        else:
            await self.db.commit()
            await self.db.refresh(user)

        view = schemas.AdminUserView.model_validate(user)
        if self.cache:
            try:
                await self.cache.set(
                    _cache_key(ADMIN_USER_DETAIL_NS, user_id),
                    view.model_dump_json(),
                    ex=DEFAULT_CACHE_TTL,
                )
            except Exception as e:
                logger.error(
                    f"[CACHE ASYNC WRITE ERROR] Post user flag change cache set failed for {user_id}: {e}"
                )
        return view

    async def freeze_user(self, user_id: UUID) -> schemas.AdminUserView:
        """Freeze a user account (sets is_active=False)."""
        return await self._change_user_flag(user_id, is_frozen=True, is_active=False)

    async def unfreeze_user(self, user_id: UUID) -> schemas.AdminUserView:
        """Unfreeze a user account (sets is_frozen=False, potentially is_active=True)."""
        return await self._change_user_flag(user_id, is_frozen=False)

    async def ban_user(self, user_id: UUID) -> schemas.AdminUserView:
        """Ban a user (sets is_banned=True and disables account)."""
        return await self._change_user_flag(
            user_id, is_banned=True, is_active=False, is_frozen=False
        )

    async def unban_user(self, user_id: UUID) -> schemas.AdminUserView:
        """Unban a user (sets is_banned=False, potentially is_active=True)."""
        return await self._change_user_flag(user_id, is_banned=False)

    async def delete_user(self, user_id: UUID) -> None:
        """Soft-delete a user."""
        await self._invalidate_user(user_id)
        user = (await self.db.execute(select(User).filter(User.id == user_id))).scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        if user.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="User already deleted"
            )
        user.is_deleted = True
        user.is_active = False
        user.is_banned = False
        user.is_frozen = False
        await self.db.commit()

    # ---------------------------------------------------
    # Review Moderation
    # ---------------------------------------------------
    async def list_flagged_reviews(
        self, skip: int = 0, limit: int = 100
    ) -> tuple[list[schemas.FlaggedReviewRead], int]:
        """List all flagged reviews."""
        key = _paginated_cache_key(ADMIN_FLAGGED_REVIEWS_NS, "all", skip, limit)
        if self.cache:
            try:
                data = await self.cache.get(key)
                if data:
                    logger.info(
                        f"[CACHE ASYNC HIT] Admin flagged reviews list (skip={skip}, limit={limit})"
                    )
                    payload = json.loads(data)
                    items = [schemas.FlaggedReviewRead.model_validate(i) for i in payload["items"]]
                    return items, payload["total_count"]
            except Exception as e:
                logger.error(f"[CACHE ASYNC READ ERROR] Failed reading {key}: {e}")

        logger.info(
            f"[CACHE ASYNC MISS] Fetching flagged reviews from DB (skip={skip}, limit={limit})"
        )
        total = (
            await self.db.execute(select(func.count(Review.id)).filter(Review.is_flagged.is_(True)))
        ).scalar_one()
        rows = await self.db.execute(
            select(Review).filter(Review.is_flagged.is_(True)).offset(skip).limit(limit)
        )
        items = [schemas.FlaggedReviewRead.model_validate(r) for r in rows.scalars().all()]

        if self.cache:
            try:
                await self.cache.set(
                    key,
                    json.dumps(
                        {"items": [i.model_dump(mode='json') for i in items], "total_count": total}
                    ),
                    ex=DEFAULT_CACHE_TTL,
                )
                logger.info(
                    f"[CACHE ASYNC SET] Admin flagged reviews list (skip={skip}, limit={limit})"
                )
            except Exception as e:
                logger.error(f"[CACHE ASYNC WRITE ERROR] Failed writing {key}: {e}")

        return items, total

    async def delete_review(self, review_id: UUID) -> None:
        """Permanently delete a review."""
        await self._invalidate_reviews()
        review = await self.db.get(Review, review_id)
        if not review:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
        await self.db.delete(review)
        await self.db.commit()


# ---------------------------------------------------
# UserService for Admin Context
# ---------------------------------------------------
class UserService:
    """Provides user listing and details for the admin interface."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.cache = redis_client

    async def list_users(
        self,
        skip: int = 0,
        limit: int = 100,
        role: UserRole | None = None,
        is_active: bool | None = None,
        is_banned: bool | None = None,
        is_deleted: bool | None = None,
    ) -> list[schemas.AdminUserView]:
        """List users with optional filters."""
        role_str = role.value if role else "any"
        active_str = str(is_active) if is_active is not None else "any"
        banned_str = str(is_banned) if is_banned is not None else "any"
        if is_deleted is None:
            deleted_str = "not_deleted"
        else:
            deleted_str = str(is_deleted)

        key = _cache_key(
            f"{ADMIN_USER_LIST_NS}:{role_str}:{active_str}:{banned_str}:{deleted_str}",
            f"skip={skip}:limit={limit}",
        )
        if self.cache:
            try:
                data = await self.cache.get(key)
                if data:
                    logger.info(f"[CACHE ASYNC HIT] Admin user list ({key})")
                    users_data = json.loads(data)
                    return [schemas.AdminUserView.model_validate(u) for u in users_data]
            except Exception as e:
                logger.error(f"[CACHE ASYNC READ ERROR] Failed reading {key}: {e}")

        logger.info(f"[CACHE ASYNC MISS] Fetching user list from DB ({key})")
        filters = []
        if role:
            filters.append(User.role == role)
        if is_active is not None:
            filters.append(User.is_active == is_active)
        if is_banned is not None:
            filters.append(User.is_banned == is_banned)
        if is_deleted is None:
            filters.append(User.is_deleted.is_(False))
        else:
            filters.append(User.is_deleted == is_deleted)

        stmt = (
            select(User).filter(*filters).order_by(User.created_at.desc()).offset(skip).limit(limit)
        )
        rows = await self.db.execute(stmt)
        users = rows.scalars().all()
        validated_users = [schemas.AdminUserView.model_validate(u) for u in users]

        if self.cache:
            try:
                await self.cache.set(
                    key,
                    json.dumps([u.model_dump(mode='json') for u in validated_users]),
                    ex=DEFAULT_CACHE_TTL,
                )
                logger.info(f"[CACHE ASYNC SET] Admin user list ({key})")
            except Exception as e:
                logger.error(f"[CACHE ASYNC WRITE ERROR] Failed writing {key}: {e}")
        return validated_users

    async def get_user(self, user_id: UUID) -> schemas.AdminUserView:
        """Fetch detailed admin view of a user."""
        key = _cache_key(ADMIN_USER_DETAIL_NS, user_id)
        if self.cache:
            try:
                data = await self.cache.get(key)
                if data:
                    logger.info(f"[CACHE ASYNC HIT] Admin user detail for {user_id}")
                    return schemas.AdminUserView.model_validate_json(data)
            except Exception as e:
                logger.error(f"[CACHE ASYNC READ ERROR] Failed reading {key}: {e}")

        logger.info(f"[CACHE ASYNC MISS] Fetching user detail from DB for {user_id}")
        user = (await self.db.execute(select(User).filter(User.id == user_id))).scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        view = schemas.AdminUserView.model_validate(user)
        if self.cache:
            try:
                await self.cache.set(key, view.model_dump_json(), ex=DEFAULT_CACHE_TTL)
                logger.info(f"[CACHE ASYNC SET] Admin user detail for {user_id}")
            except Exception as e:
                logger.error(f"[CACHE ASYNC WRITE ERROR] Failed writing {key}: {e}")
        return view
