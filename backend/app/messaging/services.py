"""
messaging/services.py

Business logic for reusable messaging system:
- Create and manage threads
- Send and fetch messages
- Enforce access control and thread lifecycle
"""

import uuid
import logging
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.messaging import models, schemas
from app.database.models import User  # Adjust import path if necessary

logger = logging.getLogger(__name__)


# -------------------------------------
# Thread Creation Logic
# -------------------------------------
def create_thread(
    db: Session,
    sender_id: uuid.UUID,
    receiver_id: uuid.UUID,
    job_id: uuid.UUID | None
) -> models.MessageThread:
    """
    Creates a new message thread between sender and receiver.
    """
    thread = models.MessageThread(job_id=job_id)
    db.add(thread)
    db.flush()

    for uid in [sender_id, receiver_id]:
        participant = models.ThreadParticipant(thread_id=thread.id, user_id=uid)
        db.add(participant)

    db.flush()
    logger.info(f"Thread created: {thread.id} by {sender_id} with receiver {receiver_id} (job_id={job_id})")
    return thread


# -------------------------------------
# Send a Message (New or Reply)
# -------------------------------------
def send_message(
    db: Session,
    sender_id: uuid.UUID,
    message_data: schemas.MessageCreate,
    sender_role: str
) -> models.Message:
    """
    Sends a message either by initiating a new thread or replying to an existing one.
    Validates thread access and participant rules.
    """
    # Replying to an existing thread
    if message_data.thread_id:
        thread = db.get(models.MessageThread, message_data.thread_id)
        if not thread:
            logger.warning(f"Thread {message_data.thread_id} not found for sender {sender_id}")
            raise HTTPException(status_code=404, detail="Thread not found")
        if thread.is_closed:
            logger.warning(f"Attempt to message closed thread {thread.id} by user {sender_id}")
            raise HTTPException(status_code=403, detail="This thread is closed. No further messages allowed.")
    else:
        # Initiating a new thread
        if not message_data.receiver_id:
            logger.error(f"Missing receiver_id for new message from {sender_id}")
            raise HTTPException(status_code=400, detail="Receiver ID is required for new thread")
        if sender_role != "ADMIN" and not message_data.job_id:
            logger.warning(f"Non-admin {sender_id} attempted to start thread without job_id")
            raise HTTPException(status_code=400, detail="Job ID is required for non-admin users.")
        thread = create_thread(db, sender_id, message_data.receiver_id, message_data.job_id)

    # Create and persist message
    message = models.Message(
        thread_id=thread.id,
        sender_id=sender_id,
        content=message_data.content
    )
    db.add(message)
    db.commit()
    db.refresh(message)

    logger.info(f"Message sent in thread {thread.id} by user {sender_id}")
    return message


# -------------------------------------
# Retrieve Threads for a User
# -------------------------------------
def get_user_threads(db: Session, user_id: uuid.UUID) -> list[models.MessageThread]:
    """
    Returns all threads the user is participating in.
    """
    return (
        db.query(models.MessageThread)
        .join(models.ThreadParticipant)
        .filter(models.ThreadParticipant.user_id == user_id)
        .order_by(models.MessageThread.created_at.desc())
        .all()
    )


# -------------------------------------
# Retrieve Thread Details
# -------------------------------------
def get_thread_detail(
    db: Session,
    thread_id: uuid.UUID,
    user_id: uuid.UUID
) -> models.MessageThread:
    """
    Returns a specific thread if the user is a participant.
    """
    thread = (
        db.query(models.MessageThread)
        .join(models.ThreadParticipant)
        .filter(
            models.MessageThread.id == thread_id,
            models.ThreadParticipant.user_id == user_id
        )
        .first()
    )
    if not thread:
        logger.warning(f"User {user_id} tried to access unauthorized or non-existent thread {thread_id}")
        raise HTTPException(status_code=404, detail="Thread not found or access denied")
    return thread
