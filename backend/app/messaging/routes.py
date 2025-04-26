"""
messaging/routes.py

API routes for the reusable messaging system:
- Start a new message thread (client/admin to worker)
- Reply to an existing thread
- Retrieve all threads for a user
- Get details of a single thread
"""

from uuid import UUID
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.core.limiter import limiter
from app.database.models import User
from app.database.session import get_db
from app.messaging import schemas, services

router = APIRouter(prefix="/messages", tags=["Messaging"])


@router.post(
    "/initiate",
    response_model=schemas.MessageRead,
    status_code=status.HTTP_201_CREATED,
    summary="Start New Thread",
    description="Starts a new message thread. Requires service_id.",
)
@limiter.limit("5/minute")
async def initiate_message(
    request: Request,
    message_data: schemas.ThreadInitiate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> schemas.MessageRead:
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
    description="Reply to an existing thread. User must be a participant.",
)
@limiter.limit("20/minute")
async def reply_message(
    request: Request,
    thread_id: UUID,
    message_data: schemas.MessageBase,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> schemas.MessageRead:
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
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[schemas.ThreadRead]:
    thread_models = await services.get_user_threads(db, current_user.id)
    return [schemas.ThreadRead.model_validate(t, from_attributes=True) for t in thread_models]


@router.get(
    "/threads/{thread_id}",
    response_model=schemas.ThreadRead,
    status_code=status.HTTP_200_OK,
    summary="Get Thread Details",
    description="Retrieve messages and participant info for a specific thread. Access requires participation.",
)
@limiter.limit("15/minute")
async def get_thread_conversation(
    request: Request,
    thread_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> schemas.ThreadRead:
    thread_model = await services.get_thread_detail(db, thread_id, current_user.id)
    return schemas.ThreadRead.model_validate(thread_model, from_attributes=True)
