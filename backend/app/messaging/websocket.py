"""
messaging/websocket.py

WebSocket route for real-time thread messaging.
- Authenticates and authorizes WebSocket clients
- Receives messages, stores them, and broadcasts updates to thread participants
"""

import json
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_from_token
from app.database.models import User
from app.database.session import get_db
from app.messaging import services
from app.messaging.manager import manager
from app.messaging.schemas import MessageCreate

router = APIRouter()


@router.websocket("/ws/{thread_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    thread_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Handles a WebSocket connection for real-time messaging within a thread.
    - Authenticates the user via token
    - Verifies thread access
    - Waits for messages and broadcasts to other participants
    """
    # Authenticate user from token in WebSocket headers
    user: User = await get_current_user_from_token(websocket, db)

    # Ensure the user is authorized to access the thread
    await services.get_thread_detail(db, thread_id, user.id)

    # Connect WebSocket to the thread room
    await manager.connect(thread_id, websocket)

    try:
        while True:
            # Wait for incoming message
            raw_data = await websocket.receive_text()
            data = json.loads(raw_data)
            content = data.get("content")

            # Validate message content
            if not content:
                await websocket.send_text("Error: Missing message content")
                continue

            # Save the message in DB
            message = await services.send_message(
                db=db,
                sender_id=user.id,
                message_data=MessageCreate(thread_id=thread_id, content=content),
                sender_role=user.role,
            )

            # Broadcast message to all participants in the thread
            await manager.broadcast_to_thread(
                thread_id,
                json.dumps({
                    "sender_id": str(message.sender_id),
                    "content": message.content,
                    "timestamp": message.timestamp.isoformat(),
                    "thread_id": str(thread_id),
                }),
            )

    except WebSocketDisconnect:
        # Graceful disconnection
        manager.disconnect(thread_id, websocket)
