"""
messaging/manager.py

WebSocket connection manager for thread-based live messaging.
- Handles connection lifecycle for each thread
- Broadcasts messages to all participants within a thread
"""

from typing import Dict, List
from fastapi import WebSocket
from uuid import UUID


class ConnectionManager:
    """
    Manages WebSocket connections per message thread.
    """

    def __init__(self):
        # Mapping of thread_id to list of connected WebSocket clients
        self.active_connections: Dict[UUID, List[WebSocket]] = {}

    async def connect(self, thread_id: UUID, websocket: WebSocket) -> None:
        """
        Accepts a new WebSocket connection and adds it to the thread pool.
        """
        await websocket.accept()
        self.active_connections.setdefault(thread_id, []).append(websocket)

    def disconnect(self, thread_id: UUID, websocket: WebSocket) -> None:
        """
        Removes a WebSocket connection from the thread pool.
        """
        if thread_id in self.active_connections:
            self.active_connections[thread_id].remove(websocket)
            if not self.active_connections[thread_id]:
                del self.active_connections[thread_id]

    async def send_personal_message(self, message: str, websocket: WebSocket) -> None:
        """
        Sends a message to a single WebSocket client.
        """
        await websocket.send_text(message)

    async def broadcast_to_thread(self, thread_id: UUID, message: str) -> None:
        """
        Broadcasts a message to all participants in a thread.
        """
        for connection in self.active_connections.get(thread_id, []):
            await connection.send_text(message)


# Global instance of the manager for import and use across modules
manager = ConnectionManager()
