"""
messaging/websocket.py

WebSocket route for real-time thread messaging.
- Authenticates and authorizes WebSocket clients
- Receives messages, stores them, and broadcasts updates to thread participants
"""

import json
from uuid import UUID
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session

from app.messaging.manager import manager
from app.messaging import services
from app.database.session import get_db
from app.core.dependencies import get_current_user_from_token
from app.database.models import User

router = APIRouter()


@router.websocket("/ws/{thread_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    thread_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Establishes WebSocket connection for a given message thread.
    - Authenticates the user using the JWT token from the websocket.
    - Ensures the user is a valid thread participant.
    - Handles real-time communication within the thread.
    """
    # Authenticate user from query token
    user: User = await get_current_user_from_token(websocket, db)

    # Authorize: ensure user is a thread participant
    services.get_thread_detail(db, thread_id, user.id)

    # Register connection
    await manager.connect(thread_id, websocket)

    try:
        while True:
            # Receive raw JSON message from client
            raw_data = await websocket.receive_text()
            data = json.loads(raw_data)
            content = data.get("content")

            if not content:
                await websocket.send_text("Error: Missing message content")
                continue

            # Store the message in DB
            message = services.send_message(
                db=db,
                sender_id=user.id,
                message_data=data,
                sender_role=user.role,
            )

            # Broadcast to all participants in the thread
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
        manager.disconnect(thread_id, websocket)
