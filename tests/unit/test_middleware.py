"""
Uses transactional_db, not db — see the note in test_chat_consumer.py for
why: database_sync_to_async runs DB lookups on a separate thread/connection
that can't see the plain db fixture's rolled-back transaction.

Tests for config/middleware.py: JWTAuthMiddleware.

Also serves as the test that actually exercises chat/routing.py and
config/asgi.py end-to-end (via WebsocketCommunicator against the real
`application` object, not ChatConsumer.as_asgi() directly) — closing the
0% coverage gap on both files, since neither was reachable through any
test before this fix.
"""
import pytest
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken

from config.asgi import application

User = get_user_model()


@pytest.fixture
def user(transactional_db):
    return User.objects.create_user(
        username="alice", email="alice@test.com", password="pass12345"
    )


@pytest.fixture
def valid_token(user):
    return str(AccessToken.for_user(user))


@pytest.mark.asyncio
async def test_valid_token_authenticates_the_connection(transactional_db, user, valid_token):
    communicator = WebsocketCommunicator(
        application, f"/ws/chat/some-room-id/?token={valid_token}"
    )
    connected, _ = await communicator.connect()


    assert communicator.scope["user"].is_authenticated
    assert communicator.scope["user"].id == user.id

    await communicator.disconnect()


@pytest.mark.asyncio
async def test_missing_token_leaves_user_anonymous(transactional_db):
    communicator = WebsocketCommunicator(application, "/ws/chat/some-room-id/")
    await communicator.connect()

    assert not communicator.scope["user"].is_authenticated

    await communicator.disconnect()


@pytest.mark.asyncio
async def test_invalid_token_leaves_user_anonymous(transactional_db):
    communicator = WebsocketCommunicator(
        application, "/ws/chat/some-room-id/?token=not-a-real-token"
    )
    await communicator.connect()

    assert not communicator.scope["user"].is_authenticated

    await communicator.disconnect()


@pytest.mark.asyncio
async def test_token_for_nonexistent_user_leaves_user_anonymous(transactional_db, valid_token):
  
    from rest_framework_simplejwt.tokens import AccessToken as AT

    fake_token = AT.for_user(
        type("FakeUser", (), {"id": "00000000-0000-0000-0000-000000000000", "pk": "00000000-0000-0000-0000-000000000000"})()
    )
    communicator = WebsocketCommunicator(
        application, f"/ws/chat/some-room-id/?token={fake_token}"
    )
    await communicator.connect()

    assert not communicator.scope["user"].is_authenticated

    await communicator.disconnect()