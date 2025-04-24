"""
messaging/services.py

Business logic for reusable messaging system:
- Create and manage threads
- Send and fetch messages
- Enforce access control and thread lifecycle
"""

import logging
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.messaging import models, schemas
from app.service.models import Service

logger = logging.getLogger(__name__)


async def create_thread(db: AsyncSession, sender_id: UUID, receiver_id: UUID) -> UUID:
    """
    Creates a new thread and registers both sender and receiver as participants.
    Returns only the thread ID to avoid accessing ORM state post-commit.
    """
    thread = models.MessageThread()
    db.add(thread)
    await db.flush()
    thread_id: UUID = thread.id

    for uid in [sender_id, receiver_id]:
        db.add(models.ThreadParticipant(thread_id=thread_id, user_id=uid))

    return thread_id


async def send_message(
    db: AsyncSession, sender_id: UUID, message_data: schemas.MessageCreate, sender_role: str
) -> schemas.MessageRead:
    """
    Sends a message either in an existing thread or creates a new one.
    Enforces required conditions such as job association for non-admins.
    """
    if not message_data.thread_id:
        if sender_role != "ADMIN":
            if not message_data.service_id:
                logger.warning(
                    f"Non-admin {sender_id} attempted to start thread without service_id"
                )
                raise HTTPException(
                    status_code=400, detail="Service ID is required for non-admin users."
                )
            # Derive worker_id (receiver) from service
            service_result = await db.execute(select(Service).filter_by(id=message_data.service_id))
            service = service_result.unique().scalar_one_or_none()
            if not service:
                logger.error(f"Invalid service ID: {message_data.service_id}")
                raise HTTPException(status_code=400, detail="Invalid service ID")
            receiver_id = service.worker_id
        else:
            logger.error("Admins must provide receiver_id for new threads")
            raise HTTPException(status_code=400, detail="Receiver ID is required for admins.")

        thread_id = await create_thread(db, sender_id, receiver_id)
    else:
        thread_id = message_data.thread_id
        result = await db.execute(select(models.MessageThread).filter_by(id=thread_id))
        thread = result.scalars().first()
        if not thread:
            logger.warning(f"Thread {thread_id} not found for sender {sender_id}")
            raise HTTPException(status_code=404, detail="Thread not found")
        if thread.is_closed:
            logger.warning(f"Attempt to message closed thread {thread_id} by user {sender_id}")
            raise HTTPException(
                status_code=403, detail="This thread is closed. No further messages allowed."
            )

    message = models.Message(thread_id=thread_id, sender_id=sender_id, content=message_data.content)

    try:
        db.add(message)
        await db.commit()
        await db.refresh(message)
        logger.info(f"Message sent in thread {thread_id} by user {sender_id}")
    except Exception as e:
        logger.error(f"Failed to send message: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")

    return schemas.MessageRead.model_validate(message, from_attributes=True)


async def get_user_threads(db: AsyncSession, user_id: UUID) -> list[schemas.ThreadRead]:
    """
    Retrieves all threads the given user is a participant in.
    Ordered by latest created.
    """
    result = await db.execute(
        select(models.MessageThread)
        .join(models.ThreadParticipant)
        .filter(models.ThreadParticipant.user_id == user_id)
        .order_by(models.MessageThread.created_at.desc())
    )
    threads = result.scalars().all()
    return [schemas.ThreadRead.model_validate(t, from_attributes=True) for t in threads]


async def get_thread_detail(db: AsyncSession, thread_id: UUID, user_id: UUID) -> schemas.ThreadRead:
    """
    Retrieves a single thread if the user is a participant.
    Enforces access control.
    """
    result = await db.execute(
        select(models.MessageThread)
        .join(models.ThreadParticipant)
        .filter(models.MessageThread.id == thread_id, models.ThreadParticipant.user_id == user_id)
    )
    thread = result.scalars().first()

    if not thread:
        logger.warning(
            f"User {user_id} tried to access unauthorized or non-existent thread {thread_id}"
        )
        raise HTTPException(status_code=404, detail="Thread not found or access denied")

    return schemas.ThreadRead.model_validate(thread, from_attributes=True)
