import uuid
from django.db import models
from django.conf import settings


class ChatRoom(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name="chat_rooms"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @classmethod
    def get_or_create_room(cls, user1_id, user2_id):
        """Create deterministic UUID from two user IDs and return room."""
        sorted_ids = sorted([str(user1_id), str(user2_id)])
        namespace = uuid.NAMESPACE_DNS
        room_uuid = uuid.uuid5(namespace, "-".join(sorted_ids))
        room, created = cls.objects.get_or_create(id=room_uuid)
        # Ensure both participants are added
        room.participants.add(user1_id, user2_id)
        return room

    def __str__(self):
        return f"ChatRoom {self.id}"


class Message(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.ForeignKey(
        ChatRoom, on_delete=models.CASCADE, related_name="messages"
    )
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.sender.username}: {self.content[:50]}"
