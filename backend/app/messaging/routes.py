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

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.core.limiter import limiter
from app.database.models import User
from app.database.session import get_db
from app.messaging import schemas, services

router = APIRouter(prefix="/messages", tags=["Messaging"])


@router.post("/{worker_id}", status_code=status.HTTP_201_CREATED, response_model=schemas.MessageRead)
@limiter.limit("5/minute")
async def initiate_message(
    request: Request,
    worker_id: UUID,
    message_data: schemas.MessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Initiates a new message thread between the current user (Client/Admin) and the specified worker.
    """
    if current_user.role not in {"CLIENT", "ADMIN"}:
        raise HTTPException(status_code=403, detail="Only clients and admins can initiate conversations.")

    return await services.send_message(
        db=db,
        sender_id=current_user.id,
        message_data=schemas.MessageCreate(
            content=message_data.content,
            receiver_id=worker_id,
            job_id=message_data.job_id
        ),
        sender_role=current_user.role
    )


@router.post("/{thread_id}/reply", status_code=status.HTTP_201_CREATED, response_model=schemas.MessageRead)
@limiter.limit("10/minute")
async def reply_message(
    request: Request,
    thread_id: UUID,
    message_data: schemas.MessageBase,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Sends a reply in an existing message thread.
    """
    return await services.send_message(
        db=db,
        sender_id=current_user.id,
        message_data=schemas.MessageCreate(
            thread_id=thread_id,
            content=message_data.content
        ),
        sender_role=current_user.role
    )


@router.get("/threads", response_model=List[schemas.ThreadRead])
async def get_my_threads(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves all message threads that the current user is participating in.
    """
    return await services.get_user_threads(db, current_user.id)


@router.get("/threads/{thread_id}", response_model=schemas.ThreadRead)
async def get_thread_conversation(
    request: Request,
    thread_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves a specific thread and all messages in it, if the user is a participant.
    """
    return await services.get_thread_detail(db, thread_id, current_user.id)
