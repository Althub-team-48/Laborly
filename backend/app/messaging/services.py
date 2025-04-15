"""
messaging/services.py

Business logic for reusable messaging system:
- Create and manage threads
- Send and fetch messages
- Enforce access control and thread lifecycle
"""

import logging
import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import User
from app.job.schemas import JobCreate
from app.job.services import JobService
from app.messaging import models, schemas

logger = logging.getLogger(__name__)


async def create_thread(
    db: AsyncSession,
    sender_id: uuid.UUID,
    receiver_id: uuid.UUID
) -> uuid.UUID:
    """
    Creates a new thread and registers both sender and receiver as participants.
    Returns only the thread ID to avoid accessing ORM state post-commit.
    """
    thread = models.MessageThread()
    db.add(thread)
    await db.flush()  # thread.id is now assigned

    thread_id = thread.id  # ✅ Store immediately after flush

    # Add participants
    for uid in [sender_id, receiver_id]:
        db.add(models.ThreadParticipant(thread_id=thread_id, user_id=uid))

    # Do not refresh the thread or touch its attributes again
    return thread_id



async def send_message(
    db: AsyncSession,
    sender_id: uuid.UUID,
    message_data: schemas.MessageCreate,
    sender_role: str
) -> models.Message:
    """
    Sends a message either in an existing thread or creates a new one.
    Enforces required conditions such as job association for non-admins.
    """
    if not message_data.thread_id:
        if not message_data.receiver_id:
            logger.error(f"Missing receiver_id for new message from {sender_id}")
            raise HTTPException(status_code=400, detail="Receiver ID is required for new thread")

        if sender_role != "ADMIN" and not message_data.service_id:
            logger.warning(f"Non-admin {sender_id} attempted to start thread without service_id")
            raise HTTPException(status_code=400, detail="Service ID is required for non-admin users.")
        
        thread_id = await create_thread(db, sender_id, message_data.receiver_id)

        """job_payload = JobCreate(
            client_id=sender_id,
            worker_id=message_data.receiver_id,
            service_id=message_data.service_id,
            thread_id=thread_id
        )
        job = await JobService(db).create_job(payload=job_payload)
        logger.info(f"Job created with ID: {job.id} for thread: {thread_id}")"""
    else:
        thread_id = message_data.thread_id  # ✅ Ensure it's always defined
        result = await db.execute(select(models.MessageThread).filter_by(id=thread_id))
        thread = result.scalars().first()

        if not thread:
            logger.warning(f"Thread {thread_id} not found for sender {sender_id}")
            raise HTTPException(status_code=404, detail="Thread not found")

        if thread.is_closed:
            logger.warning(f"Attempt to message closed thread {thread_id} by user {sender_id}")
            raise HTTPException(status_code=403, detail="This thread is closed. No further messages allowed.")

    message = models.Message(
        thread_id=thread_id,
        sender_id=sender_id,
        content=message_data.content
    )
    try:
        db.add(message)
        await db.commit()
        await db.refresh(message)
        logger.info(f"Message sent in thread {thread_id} by user {sender_id}")
    except Exception as e:
        logger.error(f"Failed to send message: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")

    return message


async def get_user_threads(db: AsyncSession, user_id: uuid.UUID) -> list[models.MessageThread]:
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
    return result.scalars().all()


async def get_thread_detail(
    db: AsyncSession,
    thread_id: uuid.UUID,
    user_id: uuid.UUID
) -> models.MessageThread:
    """
    Retrieves a single thread if the user is a participant.
    Enforces access control.
    """
    result = await db.execute(
        select(models.MessageThread)
        .join(models.ThreadParticipant)
        .filter(
            models.MessageThread.id == thread_id,
            models.ThreadParticipant.user_id == user_id
        )
    )
    thread = result.scalars().first()

    if not thread:
        logger.warning(f"User {user_id} tried to access unauthorized or non-existent thread {thread_id}")
        raise HTTPException(status_code=404, detail="Thread not found or access denied")

    return thread
