"""
backend/app/messaging/services.py

Messaging Service Logic

Handles core business operations for the messaging system:
- Create and manage message threads
- Send and fetch messages
- Enforce thread access control and manage thread lifecycle
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

from app.messaging import models, schemas
from app.service.models import Service

logger = logging.getLogger(__name__)

THREAD_DETAIL_NS = "message:thread"
THREAD_LIST_USER_NS = "message:list:user"
THREAD_PARTICIPANTS_NS = "message:thread_participants"
SHORT_CACHE_TTL = 15


# ==================================================
# --- Utility: Pattern-based Cache Invalidation ---
# ==================================================
async def _invalidate_pattern(cache: Any, pattern: str) -> None:
    """Delete Redis keys matching the given pattern."""
    if not cache:
        return
    logger.debug(f"[CACHE ASYNC MSG] Scanning pattern: {pattern}")
    deleted = 0
    try:
        if not redis_client:
            logger.warning("[CACHE ASYNC MSG] Redis client not available for pattern invalidation.")
            return
        async for key in redis_client.scan_iter(match=pattern):
            await redis_client.delete(key)
            deleted += 1
        logger.info(f"[CACHE ASYNC MSG] Deleted {deleted} keys matching pattern {pattern}")
    except Exception as e:
        logger.error(f"[CACHE ASYNC MSG ERROR] Failed pattern deletion for {pattern}: {e}")


# ===============================
# --- Messaging Service Logic---
# ===============================
async def _get_thread_participant_ids(db: AsyncSession, thread_id: UUID) -> list[UUID]:
    """Helper to fetch participant IDs for a given thread."""
    stmt = select(models.ThreadParticipant.user_id).filter_by(thread_id=thread_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def _invalidate_message_caches(cache: Any, db: AsyncSession, thread_id: UUID) -> None:
    """Invalidate thread detail and participant list caches."""
    if not cache:
        return
    keys_to_delete = [_cache_key(THREAD_DETAIL_NS, thread_id)]
    patterns_to_invalidate = []
    try:
        participant_ids = await _get_thread_participant_ids(db, thread_id)
        for user_id in participant_ids:
            patterns_to_invalidate.append(f"{CACHE_PREFIX}{THREAD_LIST_USER_NS}:{user_id}:*")
        logger.info(f"[CACHE ASYNC MSG] Invalidating caches for thread {thread_id}")
        logger.debug(f"[CACHE ASYNC MSG] Keys to delete: {keys_to_delete}")
        logger.debug(f"[CACHE ASYNC MSG] Patterns to invalidate: {patterns_to_invalidate}")

        if keys_to_delete:
            await cache.delete(*keys_to_delete)
        for pattern in patterns_to_invalidate:
            await _invalidate_pattern(cache, pattern)
    except Exception as e:
        logger.error(f"[CACHE ASYNC MSG ERROR] Failed invalidating thread {thread_id}: {e}")


async def create_thread(
    db: AsyncSession,
    sender_id: UUID,
    receiver_id: UUID,
) -> models.MessageThread:
    """
    Create a new message thread and register both sender and receiver as participants.
    (Internal helper, invalidation handled by send_message)
    """
    thread = models.MessageThread()
    db.add(thread)
    await db.flush()

    sender_participant = models.ThreadParticipant(thread_id=thread.id, user_id=sender_id)
    receiver_participant = models.ThreadParticipant(thread_id=thread.id, user_id=receiver_id)
    db.add_all([sender_participant, receiver_participant])
    await db.flush()

    logger.info(f"[THREAD] Created thread object {thread.id} between {sender_id} and {receiver_id}")
    return thread


async def send_message(
    db: AsyncSession,
    sender_id: UUID,
    message_data: schemas.MessageCreate,
    sender_role: str,
) -> schemas.MessageRead:
    """
    Send a message within an existing thread or initiate a new thread if necessary.
    Handles cache invalidation.
    """
    thread_id: UUID
    receiver_id: UUID | None = None

    cache = redis_client

    if not message_data.thread_id:
        # --- Initiating a new thread ---
        if not message_data.service_id and sender_role != "ADMIN":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Service ID is required to initiate a new conversation.",
            )

        if message_data.service_id:
            service_result = await db.execute(select(Service).filter_by(id=message_data.service_id))
            service = service_result.unique().scalar_one_or_none()
            if not service:
                raise HTTPException(status_code=400, detail="Invalid service ID.")
            receiver_id = service.worker_id

        if not receiver_id:
            raise HTTPException(
                status_code=400, detail="Could not determine receiver for new thread."
            )

        if sender_id == receiver_id:
            raise HTTPException(status_code=400, detail="Cannot start conversation with yourself.")

        thread_model = await create_thread(db, sender_id, receiver_id)
        thread_id = thread_model.id
        logger.info(f"[THREAD] New thread {thread_id} initiated by {sender_id}")

    else:
        # --- Replying to an existing thread ---
        thread_id = message_data.thread_id
        stmt = (
            select(models.MessageThread)
            .join(models.ThreadParticipant)
            .filter(
                models.MessageThread.id == thread_id,
                models.ThreadParticipant.user_id == sender_id,
            )
        )
        result = await db.execute(stmt)
        thread = result.unique().scalar_one_or_none()

        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found or access denied.")
        if thread.is_closed:
            raise HTTPException(status_code=403, detail="This thread is closed.")

    message = models.Message(
        thread_id=thread_id,
        sender_id=sender_id,
        content=message_data.content,
    )
    db.add(message)

    # --- Invalidate caches BEFORE commit ---
    await _invalidate_message_caches(cache, db, thread_id)

    try:
        await db.commit()
        await db.refresh(message, attribute_names=['sender'])
        logger.info(f"[MESSAGE] Sent message {message.id} in thread {thread_id} by {sender_id}")
    except Exception as e:
        logger.error(f"[MESSAGE] Failed to send message in thread {thread_id}: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error sending message.",
        )
    return schemas.MessageRead.model_validate(message)


async def get_user_threads(
    db: AsyncSession, user_id: UUID, skip: int = 0, limit: int = 100
) -> tuple[list[schemas.ThreadRead], int]:
    """
    Retrieve all threads involving the user, ordered by latest message timestamp,
    with pagination and cache support.
    """
    cache = redis_client
    cache_key = _paginated_cache_key(THREAD_LIST_USER_NS, user_id, skip, limit)

    if cache:
        try:
            cached_data = await cache.get(cache_key)
            if cached_data:
                logger.info(
                    f"[CACHE ASYNC HIT] Thread list for user {user_id} (skip={skip}, limit={limit})"
                )
                payload = json.loads(cached_data)
                items = [schemas.ThreadRead.model_validate(i) for i in payload["items"]]
                return items, payload["total_count"]
        except Exception as e:
            logger.error(f"[CACHE ASYNC READ ERROR] Thread list {user_id}: {e}")

    logger.info(
        f"[CACHE ASYNC MISS] Fetching threads for user_id={user_id} from DB (skip={skip}, limit={limit})"
    )

    count_stmt = (
        select(func.count())
        .select_from(models.MessageThread)
        .join(models.ThreadParticipant)
        .filter(models.ThreadParticipant.user_id == user_id)
    )
    total_count_result = await db.execute(count_stmt)
    total_count = total_count_result.scalar_one()

    latest_message_subq = (
        select(
            models.Message.thread_id,
            func.max(models.Message.timestamp).label("latest_timestamp"),
        )
        .group_by(models.Message.thread_id)
        .subquery()
    )

    stmt = (
        select(models.MessageThread)
        .join(
            models.ThreadParticipant, models.MessageThread.id == models.ThreadParticipant.thread_id
        )
        .outerjoin(latest_message_subq, models.MessageThread.id == latest_message_subq.c.thread_id)
        .filter(models.ThreadParticipant.user_id == user_id)
        .options(
            selectinload(models.MessageThread.participants).selectinload(
                models.ThreadParticipant.user
            ),
            selectinload(models.MessageThread.messages).selectinload(models.Message.sender),
        )
        .order_by(
            latest_message_subq.c.latest_timestamp.desc().nulls_last(),
            models.MessageThread.created_at.desc(),
        )
        .offset(skip)
        .limit(limit)
    )

    result = await db.execute(stmt)
    threads = list(result.unique().scalars().all())

    pydantic_threads = [schemas.ThreadRead.model_validate(t) for t in threads]

    if cache:
        try:
            payload_to_cache = json.dumps(
                {
                    'items': [t.model_dump(mode='json') for t in pydantic_threads],
                    'total_count': total_count,
                }
            )
            await cache.set(cache_key, payload_to_cache, ex=SHORT_CACHE_TTL)
            logger.info(
                f"[CACHE ASYNC SET] Thread list for user {user_id} (skip={skip}, limit={limit})"
            )
        except Exception as e:
            logger.error(f"[CACHE ASYNC WRITE ERROR] Thread list {user_id}: {e}")

    logger.info(
        f"[THREAD] Found {len(pydantic_threads)} threads for user_id={user_id} (Total: {total_count})."
    )
    return pydantic_threads, total_count


async def get_thread_detail(db: AsyncSession, thread_id: UUID, user_id: UUID) -> schemas.ThreadRead:
    """
    Retrieve a single thread with participants and messages if user is authorized, with cache support.
    """
    cache = redis_client
    cache_key = _cache_key(THREAD_DETAIL_NS, thread_id)

    if cache:
        try:
            cached_data = await cache.get(cache_key)
            if cached_data:
                logger.info(f"[CACHE ASYNC HIT] Thread detail {thread_id}")
                thread_read_cached = schemas.ThreadRead.model_validate_json(cached_data)
                participant_ids = {p.user.id for p in thread_read_cached.participants}
                if user_id not in participant_ids:
                    logger.warning(
                        f"[CACHE ASYNC AUTH] User {user_id} unauthorized for cached thread {thread_id}"
                    )
                    raise HTTPException(status_code=403, detail="Access denied to thread.")
                return thread_read_cached
        except Exception as e:
            logger.error(f"[CACHE ASYNC READ ERROR] Thread detail {thread_id}: {e}")

    logger.info(
        f"[CACHE ASYNC MISS] Fetching thread detail: thread_id={thread_id}, user_id={user_id} from DB"
    )

    stmt = (
        select(models.MessageThread)
        .join(
            models.ThreadParticipant, models.MessageThread.id == models.ThreadParticipant.thread_id
        )
        .filter(models.MessageThread.id == thread_id, models.ThreadParticipant.user_id == user_id)
        .options(
            selectinload(models.MessageThread.participants).selectinload(
                models.ThreadParticipant.user
            ),
            selectinload(models.MessageThread.messages).selectinload(models.Message.sender),
        )
        .limit(1)
    )

    result = await db.execute(stmt)
    thread = result.unique().scalar_one_or_none()

    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found or access denied.")

    thread_read = schemas.ThreadRead.model_validate(thread)

    if cache:
        try:
            await cache.set(cache_key, thread_read.model_dump_json(), ex=DEFAULT_CACHE_TTL)
            logger.info(f"[CACHE ASYNC SET] Thread detail for thread {thread_id}")
        except Exception as e:
            logger.error(f"[CACHE ASYNC WRITE ERROR] Thread detail {thread_id}: {e}")

    logger.info(f"[THREAD] Thread detail retrieved for thread_id={thread_id}")
    return thread_read
