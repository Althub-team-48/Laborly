"""
backend/app/messaging/services.py

Messaging Service Logic

Handles core business operations for the messaging system:
- Create and manage message threads
- Send and fetch messages
- Enforce thread access control and manage thread lifecycle
"""

import logging
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from myapp.messaging import models, schemas
from myapp.service.models import Service

logger = logging.getLogger(__name__)


# ---------------------------------------------------
# Thread and Messaging Services
# ---------------------------------------------------
async def create_thread(
    db: AsyncSession,
    sender_id: UUID,
    receiver_id: UUID,
) -> models.MessageThread:
    """
    Create a new message thread and register both sender and receiver as participants.
    """
    thread = models.MessageThread()
    db.add(thread)
    await db.flush()

    sender_participant = models.ThreadParticipant(thread_id=thread.id, user_id=sender_id)
    receiver_participant = models.ThreadParticipant(thread_id=thread.id, user_id=receiver_id)
    db.add_all([sender_participant, receiver_participant])
    await db.flush()

    logger.info(f"[THREAD] Created thread {thread.id} between {sender_id} and {receiver_id}")
    return thread


async def send_message(
    db: AsyncSession,
    sender_id: UUID,
    message_data: schemas.MessageCreate,
    sender_role: str,
) -> models.Message:
    """
    Send a message within an existing thread or initiate a new thread if necessary.
    """
    thread_id: UUID
    receiver_id: UUID | None = None

    if not message_data.thread_id:
        # Creating a new thread
        if not message_data.service_id and sender_role != "ADMIN":
            logger.warning(
                f"[MESSAGE] User {sender_id} tried to initiate thread without service_id"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Service ID is required to initiate a conversation.",
            )

        if message_data.service_id:
            service_result = await db.execute(select(Service).filter_by(id=message_data.service_id))
            service = service_result.unique().scalar_one_or_none()
            if not service:
                logger.error(
                    f"[MESSAGE] Invalid service ID provided by {sender_id}: {message_data.service_id}"
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid service ID.",
                )
            receiver_id = service.worker_id

        if not receiver_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not determine receiver for new thread.",
            )

        if sender_id == receiver_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot initiate a conversation with yourself.",
            )

        thread_model = await create_thread(db, sender_id, receiver_id)
        thread_id = thread_model.id
        logger.info(f"[THREAD] New thread {thread_id} created by {sender_id}")

    else:
        # Replying to an existing thread
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
            logger.warning(
                f"[MESSAGE] Thread {thread_id} not found or user {sender_id} not a participant."
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Thread not found or access denied.",
            )

        if thread.is_closed:
            logger.warning(f"[MESSAGE] Attempt to message closed thread {thread_id} by {sender_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This thread is closed.",
            )

    # Create and save the message
    message = models.Message(
        thread_id=thread_id,
        sender_id=sender_id,
        content=message_data.content,
    )
    db.add(message)

    try:
        await db.commit()
        await db.refresh(message, attribute_names=["sender"])
        logger.info(f"[MESSAGE] Sent message {message.id} in thread {thread_id} by {sender_id}")
    except Exception as e:
        logger.error(f"[MESSAGE] Failed to send message in thread {thread_id}: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error sending message.",
        )

    return message


async def get_user_threads(
    db: AsyncSession, user_id: UUID, skip: int = 0, limit: int = 100
) -> tuple[list[models.MessageThread], int]:
    """
    Retrieve all threads involving the user, ordered by latest message timestamp, with pagination and total count.
    """
    logger.info(f"[THREAD] Fetching threads for user_id={user_id}")

    # Count total records
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

    logger.info(
        f"[THREAD] Found {len(threads)} threads for user_id={user_id} (Total: {total_count})."
    )
    return threads, total_count


async def get_thread_detail(
    db: AsyncSession, thread_id: UUID, user_id: UUID
) -> models.MessageThread:
    """
    Retrieve a single thread with participants and messages if user is authorized.
    """
    logger.info(f"[THREAD] Fetching thread detail: thread_id={thread_id}, user_id={user_id}")

    stmt = (
        select(models.MessageThread)
        .join(
            models.ThreadParticipant, models.MessageThread.id == models.ThreadParticipant.thread_id
        )
        .filter(
            models.MessageThread.id == thread_id,
            models.ThreadParticipant.user_id == user_id,
        )
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
        logger.warning(
            f"[THREAD] Access denied or thread not found: thread_id={thread_id}, user_id={user_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread not found or access denied.",
        )

    logger.info(f"[THREAD] Thread detail retrieved for thread_id={thread_id}")
    return thread
