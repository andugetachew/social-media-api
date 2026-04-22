import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
        self.room_group_name = f"chat_{self.room_id}"
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        print(f"WS Connected: {self.room_group_name}")

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data["message"]
        sender_id = data["sender_id"]
        recipient_id = data.get("recipient_id")
        if not recipient_id:
            return

        # Save message and get the created message object
        saved_message = await self.save_message(sender_id, recipient_id, message)

        # Broadcast to group including the id
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "message": message,
                "sender_id": sender_id,
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
    def save_message(self, sender_id, recipient_id, content):
        from .models import ChatRoom, Message
        from accounts.models import User

        room = ChatRoom.get_or_create_room(sender_id, recipient_id)
        sender = User.objects.get(id=sender_id)
        msg = Message.objects.create(room=room, sender=sender, content=content)
        return {"id": str(msg.id)}
