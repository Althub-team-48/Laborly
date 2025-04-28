"""
tests/messaging/test_messaging_routes.py

Test cases for messaging API endpoints.
Covers message initiation, replying, thread listing, and fetching thread details.
"""

import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from fastapi import status, HTTPException

from app.messaging import schemas as msg_schemas
from app.messaging.models import Message, MessageThread
from app.database.models import User

# Message Initiation and Reply Endpoints


@pytest.mark.asyncio
@patch("app.messaging.routes.services.send_message", new_callable=AsyncMock)
async def test_initiate_message_success(
    mock_send_message: AsyncMock,
    fake_message_read: msg_schemas.MessageRead,
    mock_current_client_user: User,
    async_client: AsyncClient,
    override_get_db: None,
) -> None:
    """Test initiating a message thread successfully."""
    fake_message_read.sender.id = mock_current_client_user.id
    fake_message_read.sender.first_name = mock_current_client_user.first_name
    fake_message_read.sender.last_name = mock_current_client_user.last_name
    fake_message_read.content = "Hi, can you fix my dishwasher?"
    mock_send_message.return_value = MagicMock(spec=Message, **fake_message_read.model_dump())

    payload_schema = msg_schemas.ThreadInitiate(
        content="Hi, can you fix my dishwasher?",
        service_id=uuid4(),
        receiver_id=None,
    )
    payload = payload_schema.model_dump(mode='json')

    response = await async_client.post("/messages/initiate", json=payload)

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["id"] == str(fake_message_read.id)
    assert data["sender"]["id"] == str(mock_current_client_user.id)
    assert data["content"] == payload_schema.content

    mock_send_message.assert_awaited_once()
    call_args, call_kwargs = mock_send_message.call_args_list[0]
    assert call_kwargs["sender_id"] == mock_current_client_user.id
    assert call_kwargs["sender_role"] == mock_current_client_user.role.value
    assert isinstance(call_kwargs["message_data"], msg_schemas.MessageCreate)
    assert call_kwargs["message_data"].content == payload_schema.content
    assert call_kwargs["message_data"].service_id == payload_schema.service_id
    assert call_kwargs["message_data"].thread_id is None


@pytest.mark.asyncio
@patch("app.messaging.routes.services.send_message", new_callable=AsyncMock)
async def test_reply_message_success(
    mock_send_message: AsyncMock,
    fake_message_read: msg_schemas.MessageRead,
    mock_current_worker_user: User,
    async_client: AsyncClient,
    override_get_db: None,
) -> None:
    """Test replying to an existing message thread successfully."""
    thread_id = uuid4()
    fake_message_read.sender.id = mock_current_worker_user.id
    fake_message_read.sender.first_name = mock_current_worker_user.first_name
    fake_message_read.sender.last_name = mock_current_worker_user.last_name
    fake_message_read.thread_id = thread_id
    fake_message_read.content = "Yes, I can."
    mock_send_message.return_value = MagicMock(spec=Message, **fake_message_read.model_dump())

    payload_schema = msg_schemas.MessageBase(content="Yes, I can.")
    payload = payload_schema.model_dump(mode='json')

    response = await async_client.post(f"/messages/{thread_id}/reply", json=payload)

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["id"] == str(fake_message_read.id)
    assert data["thread_id"] == str(thread_id)
    assert data["sender"]["id"] == str(mock_current_worker_user.id)
    assert data["content"] == payload_schema.content

    mock_send_message.assert_awaited_once()
    call_args, call_kwargs = mock_send_message.call_args_list[0]
    assert call_kwargs["sender_id"] == mock_current_worker_user.id
    assert call_kwargs["sender_role"] == mock_current_worker_user.role.value
    assert isinstance(call_kwargs["message_data"], msg_schemas.MessageCreate)
    assert call_kwargs["message_data"].content == payload_schema.content
    assert call_kwargs["message_data"].thread_id == thread_id


# Message Threads and Details Endpoints


@pytest.mark.asyncio
@patch("app.messaging.routes.services.get_user_threads", new_callable=AsyncMock)
async def test_get_my_threads_success(
    mock_get_user_threads: AsyncMock,
    fake_thread_read: msg_schemas.ThreadRead,
    mock_current_client_user: User,
    async_client: AsyncClient,
    override_get_db: None,
) -> None:
    """Test retrieving list of user's message threads."""
    threads_list = [MagicMock(spec=MessageThread, **fake_thread_read.model_dump(by_alias=True))]
    total_count = 5
    mock_get_user_threads.return_value = (threads_list, total_count)

    response = await async_client.get("/messages/threads?skip=0&limit=10")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total_count"] == total_count
    assert len(data["items"]) == len(threads_list)
    assert data["items"][0]["id"] == str(fake_thread_read.id)

    actual_call_args, _ = mock_get_user_threads.call_args
    mock_get_user_threads.assert_awaited_once_with(
        actual_call_args[0], mock_current_client_user.id, skip=0, limit=10
    )


@pytest.mark.asyncio
@patch("app.messaging.routes.services.get_thread_detail", new_callable=AsyncMock)
async def test_get_thread_conversation_success(
    mock_get_thread_detail: AsyncMock,
    fake_thread_read: msg_schemas.ThreadRead,
    mock_current_client_user: User,
    async_client: AsyncClient,
    override_get_db: None,
) -> None:
    """Test retrieving the conversation of a specific thread."""
    thread_id = fake_thread_read.id
    mock_get_thread_detail.return_value = MagicMock(
        spec=MessageThread, **fake_thread_read.model_dump(by_alias=True)
    )

    response = await async_client.get(f"/messages/threads/{thread_id}")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == str(thread_id)
    assert len(data["messages"]) == len(fake_thread_read.messages)

    actual_call_args, _ = mock_get_thread_detail.call_args
    mock_get_thread_detail.assert_awaited_once_with(
        actual_call_args[0], thread_id, mock_current_client_user.id
    )


@pytest.mark.asyncio
@patch("app.messaging.routes.services.get_thread_detail", new_callable=AsyncMock)
async def test_get_thread_conversation_not_found(
    mock_get_thread_detail: AsyncMock,
    mock_current_client_user: User,
    async_client: AsyncClient,
    override_get_db: None,
) -> None:
    """Test retrieving a non-existent thread conversation."""
    thread_id = uuid4()
    mock_get_thread_detail.side_effect = HTTPException(
        status_code=404, detail="Thread not found or access denied."
    )

    response = await async_client.get(f"/messages/threads/{thread_id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Thread not found or access denied."

    actual_call_args, _ = mock_get_thread_detail.call_args
    mock_get_thread_detail.assert_awaited_once_with(
        actual_call_args[0], thread_id, mock_current_client_user.id
    )
