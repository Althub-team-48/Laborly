import pytest
from httpx import AsyncClient
from httpx._transports.asgi import ASGITransport
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from fastapi import status, HTTPException
from datetime import datetime, timezone

from main import app
from app.messaging import schemas, services

# ---------------------------
# Create message
# ---------------------------
@patch.object(services, "send_message", new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_create_message_success(mock_send_message, fake_message_read, override_current_user, override_get_db, transport):
    mock_send_message.return_value = fake_message_read
    test_worker_id = uuid4()
    payload = {
        "content": "Hi,can you fix my dishwasher?",
        "service_id": str(uuid4())  
    }
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(f"/messages/{test_worker_id}", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["id"] == str(fake_message_read.id)
    assert response.json()["thread_id"] == str(fake_message_read.thread_id)

# ---------------------------
# Initiate New Thread
# ---------------------------
@patch.object(services, "send_message", new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_create_message_success(mock_send_message, fake_message_read, override_current_user, override_get_db, transport):
    mock_send_message.return_value = fake_message_read
    test_worker_id = uuid4()
    payload = {
        "content": "Hi,can you fix my dishwasher?",
        "service_id": str(uuid4())  
    }
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(f"/messages/{test_worker_id}", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["id"] == str(fake_message_read.id)
    assert response.json()["thread_id"] == str(fake_message_read.thread_id)
    
# ---------------------------
# Reply to Existing Thread
# ---------------------------
@patch.object(services, "send_message", new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_reply_message_success(mock_send_message, fake_message_read, override_current_user, override_get_db, transport):
    mock_send_message.return_value = fake_message_read
    thread_id = uuid4()
    payload = {
        "content": "Yes, I can",
        
    }
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(f"/messages/{thread_id}/reply", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["id"] == str(fake_message_read.id)
    assert response.json()["thread_id"] == str(fake_message_read.thread_id)

# ---------------------------
# Get All Threads for Current User
# ---------------------------
@patch.object(services, "get_user_threads", new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_get_my_threads_success(mock_get_user_threads, fake_thread_read, override_current_user, override_get_db, transport):
    mock_get_user_threads.return_value = [fake_thread_read]
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/messages/threads")
    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.json(), list)    

# ---------------------------
# Get Specific Thread Details
# ---------------------------
@patch.object(services, "get_thread_detail", new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_thread_conversation_success(mock_get_thread_detail, fake_thread_read, override_current_user, override_get_db, transport):
    thread_id = uuid4()
    mock_get_thread_detail.return_value = fake_thread_read
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/messages/threads/{thread_id}")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()["messages"]) == len(fake_thread_read.messages)

# ---------------------------
# Error Handling
# ---------------------------
@patch.object(services, "get_thread_detail", new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_thread_conversation_failed(mock_get_thread_detail, fake_thread_read, override_current_user, override_get_db, transport):
    thread_id = uuid4()
    mock_get_thread_detail.side_effect = HTTPException(status_code=404, detail="Thread not found")
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/messages/threads/{thread_id}")
    assert response.status_code == 404
    assert response.json()["detail"] == "Thread not found"


