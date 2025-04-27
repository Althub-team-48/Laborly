"""
backend/app/messaging/websocket.py

Messaging WebSocket Route

Handles real-time messaging within threads via WebSocket:
- Authenticates WebSocket clients using headers
- Authorizes thread participation
- Receives, validates, and stores messages
- Broadcasts updates to all thread participants
"""

import json
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_from_ws
from app.database.models import User
from app.database.session import get_db
from app.messaging import schemas, services
from app.messaging.manager import manager

# ---------------------------------------------------
# Router Configuration
# ---------------------------------------------------
router = APIRouter()
logger = logging.getLogger(__name__)


# ---------------------------------------------------
# WebSocket Endpoint
# ---------------------------------------------------
@router.websocket("/ws/{thread_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    thread_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Handle WebSocket connection for real-time messaging in a thread.
    """

    # Authenticate the user from the WebSocket headers
    try:
        user: User = await get_current_user_from_ws(websocket, db)
        logger.info(f"[WEBSOCKET] Authenticated user {user.id} for thread {thread_id}")
    except Exception as e:
        logger.error(f"[WEBSOCKET] Authentication failed for thread {thread_id}: {e}")
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason=f"Authentication failed: {e}",
        )
        return None

    # Authorize the user's access to the thread
    try:
        await services.get_thread_detail(db, thread_id, user.id)
        logger.info(f"[WEBSOCKET] User {user.id} authorized for thread {thread_id}")
    except HTTPException as e:
        logger.warning(f"[WEBSOCKET] Authorization failed: {e.detail}")
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason=f"Authorization failed: {e.detail}",
        )
        return None
    except Exception as e:
        logger.error(
            f"[WEBSOCKET] Server error during authorization: {e}",
            exc_info=True,
        )
        await websocket.close(
            code=status.WS_1011_INTERNAL_ERROR,
            reason=f"Server error during authorization: {e}",
        )
        return None

    # Connect the user to the WebSocket room
    await manager.connect(thread_id, websocket)
    logger.info(f"[WEBSOCKET] User {user.id} connected to thread {thread_id}")

    try:
        # Continuously listen for incoming messages
        while True:
            raw_data = await websocket.receive_text()
            logger.debug(f"[WEBSOCKET] Received raw message from {user.id}: {raw_data}")

            try:
                data = json.loads(raw_data)
                content = data.get("content")

                if not content:
                    await websocket.send_text(json.dumps({"error": "Missing message content"}))
                    logger.warning(f"[WEBSOCKET] Missing content from user {user.id}")
                    continue

                # Prepare MessageCreate payload
                message_payload = schemas.MessageCreate(
                    thread_id=thread_id,
                    content=content,
                    job_id=data.get("job_id"),
                    service_id=data.get("service_id"),
                )

                # Send and save the message
                message = await services.send_message(
                    db=db,
                    sender_id=user.id,
                    sender_role=user.role,
                    message_data=message_payload,
                )
                logger.info(f"[WEBSOCKET] Message {message.id} sent in thread {thread_id}")

                # Broadcast the new message to all participants
                message_read = schemas.MessageRead.model_validate(message, from_attributes=True)
                broadcast_message = json.dumps(message_read.model_dump(mode="json"))
                await manager.broadcast_to_thread(thread_id, broadcast_message)

                logger.debug(f"[WEBSOCKET] Broadcasted message to thread {thread_id}")

            except json.JSONDecodeError:
                logger.warning(f"[WEBSOCKET] Invalid JSON format from user {user.id}")
                await websocket.send_text(json.dumps({"error": "Invalid JSON format"}))
            except Exception as e:
                logger.error(
                    f"[WEBSOCKET] Error processing message from user {user.id}: {e}",
                    exc_info=True,
                )
                await websocket.send_text(json.dumps({"error": f"Failed to send message: {e}"}))

    except WebSocketDisconnect as exc:
        # Handle user disconnection
        manager.disconnect(thread_id, websocket)
        logger.info(
            f"[WEBSOCKET] User {user.id} disconnected from thread {thread_id} (code: {exc.code})"
        )
    except Exception as e:
        logger.error(
            f"[WEBSOCKET] Unexpected error in WebSocket lifecycle for user {user.id}: {e}",
            exc_info=True,
        )
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason="Internal server error")

    return None
