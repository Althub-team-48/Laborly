"""
messaging/services.py

Business logic for reusable messaging system:
- Create and manage threads
- Send and fetch messages
- Enforce access control and thread lifecycle
"""

import logging
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.messaging import models, schemas
from app.service.models import Service

logger = logging.getLogger(__name__)


async def create_thread(
    db: AsyncSession, sender_id: UUID, receiver_id: UUID
) -> models.MessageThread:
    """
    Creates a new thread and registers both sender and receiver as participants.
    Returns the MessageThread model instance.
    """
    thread = models.MessageThread()
    db.add(thread)
    await db.flush()

    sender_participant = models.ThreadParticipant(thread_id=thread.id, user_id=sender_id)
    receiver_participant = models.ThreadParticipant(thread_id=thread.id, user_id=receiver_id)
    db.add_all([sender_participant, receiver_participant])
    await db.flush()

    logger.info(f"Thread created: {thread.id} between {sender_id} and {receiver_id}")
    return thread


async def send_message(
    db: AsyncSession, sender_id: UUID, message_data: schemas.MessageCreate, sender_role: str
) -> models.Message:
    """
    Sends a message either in an existing thread or creates a new one.
    Returns the created Message model instance.
    """
    thread_id: UUID
    receiver_id: UUID | None = None

    if not message_data.thread_id:
        # --- Logic for creating a new thread ---
        if (
            not message_data.service_id and sender_role != "ADMIN"
        ):  # Admins might initiate differently
            logger.warning(f"User {sender_id} attempted to start thread without service_id")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Service ID is required to initiate a conversation.",
            )

        if message_data.service_id:
            service_result = await db.execute(select(Service).filter_by(id=message_data.service_id))
            service = service_result.unique().scalar_one_or_none()
            if not service:
                logger.error(
                    f"Invalid service ID provided by {sender_id}: {message_data.service_id}"
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid service ID"
                )
            receiver_id = service.worker_id
        # else: Handle admin case, e.g., require receiver_id in payload

        if not receiver_id:
            raise HTTPException(
                status_code=400, detail="Could not determine receiver for new thread."
            )

        if sender_id == receiver_id:
            raise HTTPException(
                status_code=400, detail="Cannot initiate a conversation with yourself."
            )

        thread_model = await create_thread(db, sender_id, receiver_id)
        thread_id = thread_model.id
        logger.info(f"New thread {thread_id} created for message from {sender_id} to {receiver_id}")

    else:
        # --- Logic for replying to an existing thread ---
        thread_id = message_data.thread_id
        stmt = (
            select(models.MessageThread)
            .join(models.ThreadParticipant)
            .filter(
                models.MessageThread.id == thread_id, models.ThreadParticipant.user_id == sender_id
            )
        )
        result = await db.execute(stmt)
        thread = result.unique().scalar_one_or_none()

        if not thread:
            logger.warning(f"Thread {thread_id} not found or user {sender_id} not a participant.")
            raise HTTPException(status_code=404, detail="Thread not found or access denied")
        if thread.is_closed:
            logger.warning(f"Attempt to message closed thread {thread_id} by user {sender_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="This thread is closed."
            )

    # Create the message
    message = models.Message(thread_id=thread_id, sender_id=sender_id, content=message_data.content)
    db.add(message)

    try:
        await db.commit()
        await db.refresh(message, attribute_names=['sender'])
        logger.info(f"Message {message.id} sent in thread {thread_id} by user {sender_id}")
    except Exception as e:
        logger.error(f"Failed to send message in thread {thread_id}: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error sending message.")

    return message


async def get_user_threads(db: AsyncSession, user_id: UUID) -> list[models.MessageThread]:
    """
    Retrieves all threads the given user is a participant in, ordered by latest message.
    Eagerly loads participants/users and messages/senders.
    """
    logger.info(f"Fetching threads for user_id={user_id}")

    # Subquery to get the latest message timestamp for each thread
    latest_message_subq = (
        select(
            models.Message.thread_id, func.max(models.Message.timestamp).label("latest_timestamp")
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
    )

    result = await db.execute(stmt)
    threads = list(result.unique().scalars().all())
    logger.info(f"Found {len(threads)} threads for user_id={user_id}")
    return threads


async def get_thread_detail(
    db: AsyncSession, thread_id: UUID, user_id: UUID
) -> models.MessageThread:
    """
    Retrieves a single thread if the user is a participant.
    Eagerly loads participants/users and messages/senders (messages ordered by timestamp).
    Enforces access control.
    """
    logger.info(f"Fetching detail for thread_id={thread_id}, user_id={user_id}")
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
        logger.warning(
            f"User {user_id} tried to access unauthorized or non-existent thread {thread_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found or access denied"
        )

    logger.info(f"Thread detail retrieved for thread_id={thread_id}")
    return thread
