"""
IMPORTANT: uses transactional_db, not the plain db fixture. ChatConsumer
uses @database_sync_to_async for DB access, which runs on a separate
thread with its own DB connection. pytest-django's default db fixture
wraps the test in a transaction that only the creating thread/connection
can see (rolled back after) — invisible to that separate thread, causing
false DoesNotExist / rejected-connection results even for valid data.
transactional_db actually commits (TransactionTestCase-style), making
data visible across threads/connections.

Tests for chat/consumers.py using Channels' WebsocketCommunicator.

Requires: pytest-asyncio (async test support) and channels' testing utils.
Add to pytest.ini / pyproject.toml:

    [tool.pytest.ini_options]
    asyncio_mode = "auto"

Adjust the ChatRoom creation calls to match your actual model fields —
written here assuming a `participants` M2M, matching the consumer's
default lookup path.
"""
import json
import uuid

import pytest
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model

from asgiref.sync import sync_to_async

from chat.consumers import ChatConsumer
from chat.models import ChatRoom

User = get_user_model()


@pytest.fixture
def two_users(transactional_db):
    alice = User.objects.create_user(username="alice", email="alice@test.com", password="pass12345")
    bob = User.objects.create_user(username="bob", email="bob@test.com", password="pass12345")
    return alice, bob


@pytest.fixture
def shared_room(transactional_db, two_users):
    alice, bob = two_users
    room = ChatRoom.objects.create()
    room.participants.add(alice, bob)
    return room


@pytest.mark.asyncio
async def test_unauthenticated_connection_is_rejected(transactional_db, shared_room):
    communicator = WebsocketCommunicator(ChatConsumer.as_asgi(), f"/ws/chat/{shared_room.id}/")
    communicator.scope["url_route"] = {"kwargs": {"room_id": str(shared_room.id)}}
    communicator.scope["user"] = None

    connected, _ = await communicator.connect()
    assert connected is False
    await communicator.disconnect()


@pytest.mark.asyncio
async def test_non_participant_is_rejected(transactional_db, two_users, shared_room):
    alice, _ = two_users
    outsider = await sync_to_async(User.objects.create_user)(
        username="mallory", email="mallory@test.com", password="pass12345"
    )

    communicator = WebsocketCommunicator(ChatConsumer.as_asgi(), f"/ws/chat/{shared_room.id}/")
    communicator.scope["url_route"] = {"kwargs": {"room_id": str(shared_room.id)}}
    communicator.scope["user"] = outsider

    connected, _ = await communicator.connect()
    assert connected is False
    await communicator.disconnect()


@pytest.mark.asyncio
async def test_participant_can_connect_and_send_message(transactional_db, two_users, shared_room):
    alice, bob = two_users

    communicator = WebsocketCommunicator(ChatConsumer.as_asgi(), f"/ws/chat/{shared_room.id}/")
    communicator.scope["url_route"] = {"kwargs": {"room_id": str(shared_room.id)}}
    communicator.scope["user"] = alice

    connected, _ = await communicator.connect()
    assert connected is True

    await communicator.send_to(text_data=json.dumps({"message": "hey bob"}))
    response = await communicator.receive_from()
    payload = json.loads(response)

    assert payload["message"] == "hey bob"
    # sender_id is serialized as a string by the consumer (msgpack over
    # the Redis channel layer can't carry a raw UUID object) — compare
    # against str(alice.id), not the UUID object itself.
    assert payload["sender_id"] == str(alice.id)

    await communicator.disconnect()


@pytest.mark.asyncio
async def test_sender_id_cannot_be_spoofed_by_client(transactional_db, two_users, shared_room):
    alice, bob = two_users

    communicator = WebsocketCommunicator(ChatConsumer.as_asgi(), f"/ws/chat/{shared_room.id}/")
    communicator.scope["url_route"] = {"kwargs": {"room_id": str(shared_room.id)}}
    communicator.scope["user"] = alice

    connected, _ = await communicator.connect()
    assert connected is True

    # client tries to impersonate bob
    await communicator.send_to(text_data=json.dumps({"message": "hi", "sender_id": str(bob.id)}))
    response = await communicator.receive_from()
    payload = json.loads(response)

    assert payload["sender_id"] == str(alice.id)  # server ignored the spoofed value
    await communicator.disconnect()


@pytest.mark.asyncio
async def test_malformed_payload_returns_error_without_crashing(transactional_db, two_users, shared_room):
    alice, _ = two_users

    communicator = WebsocketCommunicator(ChatConsumer.as_asgi(), f"/ws/chat/{shared_room.id}/")
    communicator.scope["url_route"] = {"kwargs": {"room_id": str(shared_room.id)}}
    communicator.scope["user"] = alice

    connected, _ = await communicator.connect()
    assert connected is True

    await communicator.send_to(text_data="not json")
    response = await communicator.receive_from()
    payload = json.loads(response)
    assert payload["error"] == "invalid_payload"

    await communicator.disconnect()


@pytest.mark.asyncio
async def test_nonexistent_room_is_rejected(transactional_db, two_users):
    alice, _ = two_users
    fake_room_id = uuid.uuid4()

    communicator = WebsocketCommunicator(ChatConsumer.as_asgi(), f"/ws/chat/{fake_room_id}/")
    communicator.scope["url_route"] = {"kwargs": {"room_id": str(fake_room_id)}}
    communicator.scope["user"] = alice

    connected, _ = await communicator.connect()
    assert connected is False
    await communicator.disconnect()


@pytest.mark.asyncio
async def test_empty_message_returns_error(transactional_db, two_users, shared_room):
    alice, _ = two_users

    communicator = WebsocketCommunicator(ChatConsumer.as_asgi(), f"/ws/chat/{shared_room.id}/")
    communicator.scope["url_route"] = {"kwargs": {"room_id": str(shared_room.id)}}
    communicator.scope["user"] = alice

    connected, _ = await communicator.connect()
    assert connected is True

    await communicator.send_to(text_data=json.dumps({"message": "   "}))
    response = await communicator.receive_from()
    payload = json.loads(response)
    assert payload["error"] == "empty_message"

    await communicator.disconnect()


@pytest.mark.asyncio
async def test_save_message_failure_returns_send_failed_error(transactional_db, two_users, shared_room):
    from unittest.mock import patch

    alice, _ = two_users

    communicator = WebsocketCommunicator(ChatConsumer.as_asgi(), f"/ws/chat/{shared_room.id}/")
    communicator.scope["url_route"] = {"kwargs": {"room_id": str(shared_room.id)}}
    communicator.scope["user"] = alice

    connected, _ = await communicator.connect()
    assert connected is True

    with patch("chat.consumers.ChatConsumer.save_message", side_effect=Exception("db down")):
        await communicator.send_to(text_data=json.dumps({"message": "hello"}))
        response = await communicator.receive_from()
        payload = json.loads(response)
        assert payload["error"] == "send_failed"

    await communicator.disconnect()