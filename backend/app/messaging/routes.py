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


# --------------------------------------------
# Initiate New Thread
# --------------------------------------------
@router.post(
    "/{worker_id}",
    response_model=schemas.MessageRead,
    status_code=status.HTTP_201_CREATED,
    summary="Start New Thread",
    description="Starts a new message thread between the current user (Client or Admin) and a worker.",
)
@limiter.limit("5/minute")
async def initiate_message(
    request: Request,
    worker_id: UUID,
    message_data: schemas.ThreadInitiate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
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


# --------------------------------------------
# Reply to Existing Thread
# --------------------------------------------
@router.post(
    "/{thread_id}/reply",
    response_model=schemas.MessageRead,
    status_code=status.HTTP_201_CREATED,
    summary="Reply to Thread",
    description="Reply to an existing thread. The user must be a participant in the thread.",
)
@limiter.limit("10/minute")
async def reply_message(
    request: Request,
    thread_id: UUID,
    message_data: schemas.MessageBase,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await services.send_message(
        db=db,
        sender_id=current_user.id,
        message_data=schemas.MessageCreate(
            thread_id=thread_id,
            content=message_data.content
        ),
        sender_role=current_user.role
    )


# --------------------------------------------
# Get All Threads for Current User
# --------------------------------------------
@router.get(
    "/threads",
    response_model=List[schemas.ThreadRead],
    status_code=status.HTTP_200_OK,
    summary="List My Threads",
    description="Retrieve all message threads involving the authenticated user.",
)
async def get_my_threads(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await services.get_user_threads(db, current_user.id)


# --------------------------------------------
# Get Specific Thread Details
# --------------------------------------------
@router.get(
    "/threads/{thread_id}",
    response_model=schemas.ThreadRead,
    status_code=status.HTTP_200_OK,
    summary="Get Thread Details",
    description="Retrieve messages in a specific thread. Access allowed only if the user is a participant.",
)
async def get_thread_conversation(
    request: Request,
    thread_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await services.get_thread_detail(db, thread_id, current_user.id)
