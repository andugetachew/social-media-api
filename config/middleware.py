"""
config/middleware.py (or chat/middleware.py — see note in asgi.py below on
where to place this)

JWT authentication for Django Channels WebSocket connections.

The rest of this API authenticates via `Authorization: Bearer <token>`
(rest_framework_simplejwt), but browsers cannot set custom headers on a
WebSocket handshake — the standard workaround is passing the access token
as a query string parameter on the WS URL, e.g.:

    wss://yourhost/ws/chat/<room_id>/?token=<access_token>

This middleware reads that token, validates it the same way SimpleJWT
validates HTTP requests, and populates scope["user"] accordingly — which
is what ChatConsumer.connect() checks before accepting a connection.

Previously: asgi.py used channels.auth.AuthMiddlewareStack, which
authenticates via Django's session cookie. Nothing in this API sets a
session cookie (it's JWT-only), so scope["user"] was AnonymousUser for
essentially every real client connection, meaning the auth check added to
ChatConsumer.connect() would reject every legitimate connection.
"""
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import AccessToken


@database_sync_to_async
def get_user_from_token(token_str):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    try:
        access_token = AccessToken(token_str)
        user_id = access_token["user_id"]
        return User.objects.get(id=user_id)
    except (InvalidToken, TokenError, User.DoesNotExist, KeyError):
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        query_string = scope.get("query_string", b"").decode()
        query_params = parse_qs(query_string)
        token = query_params.get("token", [None])[0]

        if token:
            scope["user"] = await get_user_from_token(token)
        else:
            scope["user"] = AnonymousUser()

        return await super().__call__(scope, receive, send)


def JWTAuthMiddlewareStack(inner):
    return JWTAuthMiddleware(inner)