from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework import status
from .models import ChatRoom, Message
from accounts.models import User
from django.utils import timezone  # <-- Make sure this import is correct

import os
import uuid
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.conf import settings
from PIL import Image
from io import BytesIO


# ---------- Existing class-based views ----------
class ChatRoomListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        rooms = request.user.chat_rooms.all()
        data = []
        for room in rooms:
            other = room.participants.exclude(id=request.user.id).first()
            last_msg = room.messages.first()
            data.append(
                {
                    "id": str(room.id),
                    "other_user": (
                        {
                            "id": str(other.id),
                            "username": other.username,
                            "email": other.email,
                        }
                        if other
                        else None
                    ),
                    "last_message": last_msg.content[:50] if last_msg else "",
                }
            )
        return Response(data)


class MessageListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        other_user_id = user_id
        room = ChatRoom.get_or_create_room(request.user.id, other_user_id)
        messages = room.messages.all()
        return Response(
            [
                {
                    "id": str(m.id),  # <-- ADD THIS LINE
                    "sender_id": str(m.sender_id),
                    "content": m.content,
                    "created_at": m.created_at,
                }
                for m in messages
            ]
        )


# ---------- NEW polling-based views (no WebSocket) ----------
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def send_message(request):
    recipient_id = request.data.get("recipient_id")
    content = request.data.get("content")
    if not recipient_id or not content:
        return Response({"error": "Missing recipient_id or content"}, status=400)
    try:
        recipient = User.objects.get(id=recipient_id)
        room = ChatRoom.get_or_create_room(request.user.id, recipient.id)
        Message.objects.create(room=room, sender=request.user, content=content)
        return Response({"status": "sent"}, status=201)
    except User.DoesNotExist:
        return Response({"error": "Recipient not found"}, status=404)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_messages(request, user_id):
    try:
        other_user = User.objects.get(id=user_id)
        room = ChatRoom.get_or_create_room(request.user.id, other_user.id)
        messages = room.messages.all().order_by("created_at")
        data = [
            {
                "id": str(m.id),  # <-- required
                "sender_id": str(m.sender_id),
                "content": m.content,
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ]
        return Response(data)
    except User.DoesNotExist:
        return Response({"error": "User not found"}, status=404)


# Temporary storage for typing status (in production use Redis)
typing_users = {}  # {room_id: {user_id: timestamp}}


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def typing(request):
    recipient_id = request.data.get("recipient_id")
    is_typing = request.data.get("is_typing", False)
    if not recipient_id:
        return Response({"error": "Missing recipient_id"}, status=400)

    room_id = str(ChatRoom.get_or_create_room(request.user.id, recipient_id).id)
    if is_typing:
        typing_users[room_id] = {
            **typing_users.get(room_id, {}),
            str(request.user.id): timezone.now(),
        }
    else:
        typing_users.get(room_id, {}).pop(str(request.user.id), None)

    return Response({"status": "ok"})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_typing(request, user_id):
    recipient_id = user_id
    room = ChatRoom.get_or_create_room(request.user.id, recipient_id)
    room_id = str(room.id)
    typing_data = typing_users.get(room_id, {})
    # Clean old typing status (older than 3 seconds)
    now = timezone.now()
    for uid, ts in list(typing_data.items()):
        if (now - ts).total_seconds() > 3:
            del typing_data[uid]
    return Response({"typing_user_ids": list(typing_data.keys())})


@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def edit_message(request, message_id):
    try:
        message = Message.objects.get(id=message_id)
        # Only the sender can edit
        if message.sender != request.user:
            return Response(
                {"error": "You can only edit your own messages"}, status=403
            )
        content = request.data.get("content")
        if not content or not content.strip():
            return Response({"error": "Message cannot be empty"}, status=400)
        message.content = content
        message.save()
        return Response(
            {
                "id": str(message.id),
                "sender_id": str(message.sender_id),
                "content": message.content,
                "created_at": message.created_at.isoformat(),
            }
        )
    except Message.DoesNotExist:
        return Response({"error": "Message not found"}, status=404)


api_view(["DELETE"])


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_message(request, message_id):
    try:
        message = Message.objects.get(id=message_id)
        if message.sender != request.user:
            return Response({"error": "Not your message"}, status=403)
        message.delete()
        return Response({"status": "deleted"}, status=200)
    except Message.DoesNotExist:
        return Response({"error": "Message not found"}, status=404)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def upload_chat_file(request):
    file = request.FILES.get("file")
    if not file:
        return Response({"error": "No file provided"}, status=400)

    allowed_types = [
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
        "application/pdf",
        "text/plain",
        "application/msword",  # .doc
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-powerpoint",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ]
    if file.content_type not in allowed_types:
        return Response({"error": "File type not allowed"}, status=400)

    if file.size > 10 * 1024 * 1024:
        return Response({"error": "File too large (max 10MB)"}, status=400)

    # Save file
    ext = os.path.splitext(file.name)[1]
    safe_filename = f"chat_files/{uuid.uuid4()}{ext}"
    saved_path = default_storage.save(safe_filename, ContentFile(file.read()))
    # Build absolute URL
    file_url = request.build_absolute_uri(default_storage.url(saved_path))

    is_image = file.content_type.startswith("image/")
    thumbnail_url = None

    if is_image:
        try:
            with default_storage.open(saved_path, "rb") as f:
                img = Image.open(f)
                img.thumbnail((200, 200))
                thumb_io = BytesIO()
                img.save(thumb_io, format="JPEG", quality=85)
                thumb_name = f"chat_thumbnails/{uuid.uuid4()}.jpg"
                thumb_path = default_storage.save(
                    thumb_name, ContentFile(thumb_io.getvalue())
                )
                thumbnail_url = request.build_absolute_uri(
                    default_storage.url(thumb_path)
                )
        except Exception as e:
            print(f"Thumbnail error: {e}")

    return Response(
        {
            "url": file_url,
            "filename": file.name,
            "is_image": is_image,
            "thumbnail_url": thumbnail_url,
            "size": file.size,
        }
    )
