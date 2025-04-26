"""
backend/app/messaging/routes.py

Messaging API Routes

Defines all routes for the messaging system, including:
- Starting a new message thread
- Replying to existing threads
- Listing all threads involving the authenticated user
- Retrieving conversation details of a single thread

All operations require user authentication and appropriate access control.
"""

from uuid import UUID
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.core.limiter import limiter
from app.database.models import User
from app.database.session import get_db
from app.messaging import schemas, services

# ---------------------------------------------------
# Router Configuration
# ---------------------------------------------------
router = APIRouter(prefix="/messages", tags=["Messaging"])

# ---------------------------------------------------
# Dependencies
# ---------------------------------------------------
DBDep = Annotated[AsyncSession, Depends(get_db)]
AuthenticatedUserDep = Annotated[User, Depends(get_current_user)]

# ---------------------------------------------------
# Messaging Endpoints (Authenticated Users Only)
# ---------------------------------------------------


@router.post(
    "/initiate",
    response_model=schemas.MessageRead,
    status_code=status.HTTP_201_CREATED,
    summary="Start New Thread",
    description="Starts a new message thread. Requires service_id and authentication.",
)
@limiter.limit("5/minute")
async def initiate_message(
    request: Request,
    message_data: schemas.ThreadInitiate,
    db: DBDep,
    current_user: AuthenticatedUserDep,
) -> schemas.MessageRead:
    """
    Start a new message thread.
    """
    message_model = await services.send_message(
        db=db,
        sender_id=current_user.id,
        message_data=schemas.MessageCreate(
            content=message_data.content,
            service_id=message_data.service_id,
            thread_id=None,
            job_id=None,
        ),
        sender_role=current_user.role.value,
    )
    return schemas.MessageRead.model_validate(message_model, from_attributes=True)


@router.post(
    "/{thread_id}/reply",
    response_model=schemas.MessageRead,
    status_code=status.HTTP_201_CREATED,
    summary="Reply to Thread",
    description="Reply to an existing thread. User must be authenticated and a participant.",
)
@limiter.limit("20/minute")
async def reply_message(
    request: Request,
    thread_id: UUID,
    message_data: schemas.MessageBase,
    db: DBDep,
    current_user: AuthenticatedUserDep,
) -> schemas.MessageRead:
    """
    Reply to an existing message thread.
    """
    message_model = await services.send_message(
        db=db,
        sender_id=current_user.id,
        message_data=schemas.MessageCreate(
            thread_id=thread_id,
            content=message_data.content,
            job_id=None,
            service_id=None,
        ),
        sender_role=current_user.role.value,
    )
    return schemas.MessageRead.model_validate(message_model, from_attributes=True)


@router.get(
    "/threads",
    response_model=list[schemas.ThreadRead],
    status_code=status.HTTP_200_OK,
    summary="List My Threads",
    description="Retrieve all message threads involving the authenticated user, ordered by latest activity.",
)
@limiter.limit("10/minute")
async def get_my_threads(
    request: Request,
    db: DBDep,
    current_user: AuthenticatedUserDep,
) -> list[schemas.ThreadRead]:
    """
    Retrieve all threads involving the authenticated user.
    """
    thread_models = await services.get_user_threads(db, current_user.id)
    return [schemas.ThreadRead.model_validate(t, from_attributes=True) for t in thread_models]


@router.get(
    "/threads/{thread_id}",
    response_model=schemas.ThreadRead,
    status_code=status.HTTP_200_OK,
    summary="Get Thread Details",
    description="Retrieve messages and participant info for a specific thread. Requires authentication and participation.",
)
@limiter.limit("15/minute")
async def get_thread_conversation(
    request: Request,
    thread_id: UUID,
    db: DBDep,
    current_user: AuthenticatedUserDep,
) -> schemas.ThreadRead:
    """
    Retrieve a conversation thread and its participants' details.
    """
    thread_model = await services.get_thread_detail(db, thread_id, current_user.id)
    return schemas.ThreadRead.model_validate(thread_model, from_attributes=True)
