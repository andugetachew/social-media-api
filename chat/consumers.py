import json
import logging

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

logger = logging.getLogger(__name__)


class ChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for 1:1 chat rooms.

    Assumes JWT auth is handled by upstream ASGI middleware (e.g. a custom
    JWTAuthMiddleware wrapping AuthMiddlewareStack) which populates
    self.scope["user"] before connect() runs. Adjust the participant check
    in `_get_authorized_room` to match your actual ChatRoom model fields
    (e.g. `participants`, `user1`/`user2`, etc.) — written generically here.
    """

    async def connect(self):
        user = self.scope.get("user")

        # 1. Reject unauthenticated connections outright.
        if user is None or not getattr(user, "is_authenticated", False):
            await self.close(code=4001)  # custom code: unauthenticated
            return

        self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
        self.user = user

        # 2. Verify the authenticated user is actually a participant of
        #    this room before letting them join the group at all.
        room = await self._get_authorized_room(self.room_id, self.user.id)
        if room is None:
            await self.close(code=4003)  # custom code: forbidden
            return

        self.room_group_name = f"chat_{self.room_id}"
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        logger.debug("WS connected: user=%s room=%s", self.user.id, self.room_group_name)

    async def disconnect(self, close_code):
        # group_name only exists if connect() got far enough to set it.
        if hasattr(self, "room_group_name"):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message = data["message"]
        except (json.JSONDecodeError, KeyError):
            await self.send(text_data=json.dumps({"error": "invalid_payload"}))
            return

        if not message or not str(message).strip():
            await self.send(text_data=json.dumps({"error": "empty_message"}))
            return

        # 3. sender_id comes from the authenticated scope, never from the
        #    client payload — prevents impersonation.
        sender_id = self.user.id

        try:
            saved_message = await self.save_message(self.room_id, sender_id, message)
        except Exception:
            logger.exception("Failed to save chat message for room %s", self.room_id)
            await self.send(text_data=json.dumps({"error": "send_failed"}))
            return

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "message": message,
                # str() here: sender_id is a UUID object (self.user.id).
                # channels_redis serializes group_send payloads via
                # msgpack, which cannot serialize UUID objects directly —
                # raised TypeError: can not serialize 'UUID' object.
                "sender_id": str(sender_id),
                "id": saved_message["id"],
            },
        )

    async def chat_message(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "id": event["id"],
                    "message": event["message"],
                    "sender_id": event["sender_id"],
                }
            )
        )

    @database_sync_to_async
    def _get_authorized_room(self, room_id, user_id):
        """
        Fetch the room by its URL id and confirm the connecting user is a
        participant. Returns None if the room doesn't exist, the user
        isn't authorized for it, or room_id isn't even a valid UUID —
        caller closes the socket in all three cases.

        NOTE: adjust the participant lookup to match your actual ChatRoom
        model. Written here assuming a `participants` M2M; swap for
        `user1`/`user2` equality checks if that's your schema instead.
        """
        from django.core.exceptions import ValidationError
        from .models import ChatRoom

        try:
            room = ChatRoom.objects.get(id=room_id)
        except (ChatRoom.DoesNotExist, ValidationError, ValueError):
            
            return None

        if hasattr(room, "participants"):
            if not room.participants.filter(id=user_id).exists():
                return None
        else:
            # fallback for user1/user2-style schema
            participant_ids = {getattr(room, "user1_id", None), getattr(room, "user2_id", None)}
            if user_id not in participant_ids:
                return None

        return room

    @database_sync_to_async
    def save_message(self, room_id, sender_id, content):
        from .models import ChatRoom, Message

        room = ChatRoom.objects.get(id=room_id)
        msg = Message.objects.create(room=room, sender_id=sender_id, content=content)
        return {"id": str(msg.id)}