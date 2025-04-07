"""
messaging/routes.py

API routes for the reusable messaging system:
- Start a new message thread (client/admin to worker)
- Reply to an existing thread
- Retrieve all threads for a user
- Get details of a single thread
"""

from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, status, HTTPException, Request
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.core.dependencies import get_current_user
from app.messaging import schemas, services
from app.database.models import User
from app.core.limiter import limiter

router = APIRouter(prefix="/messages", tags=["Messaging"])


# ----------------------------------------
# Initiate a Message Thread
# ----------------------------------------
@router.post("/{worker_id}", status_code=status.HTTP_201_CREATED, response_model=schemas.MessageRead)
@limiter.limit("5/minute")
def initiate_message(
    request: Request, 
    worker_id: UUID,
    message_data: schemas.MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Initiates a new thread by sending a message from client/admin to a worker.
    """
    if current_user.role not in {"CLIENT", "ADMIN"}:
        raise HTTPException(status_code=403, detail="Only clients and admins can initiate conversations.")

    return services.send_message(
        db=db,
        sender_id=current_user.id,
        message_data=schemas.MessageCreate(
            content=message_data.content,
            receiver_id=worker_id,
            job_id=message_data.job_id
        ),
        sender_role=current_user.role
    )


# ----------------------------------------
# Reply to an Existing Thread
# ----------------------------------------
@router.post("/{thread_id}/reply", status_code=status.HTTP_201_CREATED, response_model=schemas.MessageRead)
@limiter.limit("10/minute")
def reply_message(
    request: Request, 
    thread_id: UUID,
    message_data: schemas.MessageBase,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Send a reply message within an existing thread.
    """
    return services.send_message(
        db=db,
        sender_id=current_user.id,
        message_data=schemas.MessageCreate(
            thread_id=thread_id,
            content=message_data.content
        ),
        sender_role=current_user.role
    )


# ----------------------------------------
# List User's Message Threads
# ----------------------------------------
@router.get("/threads", response_model=List[schemas.ThreadRead])
def get_my_threads(
    request: Request, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve all message threads the user is part of.
    """
    return services.get_user_threads(db, current_user.id)


# ----------------------------------------
# Get Details of a Single Thread
# ----------------------------------------
@router.get("/threads/{thread_id}", response_model=schemas.ThreadRead)
def get_thread_conversation(
    request: Request, 
    thread_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve the full conversation and messages in a specific thread.
    """
    return services.get_thread_detail(db, thread_id, current_user.id)
