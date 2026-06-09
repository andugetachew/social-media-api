import uuid
from django.urls import reverse
from rest_framework import status
from django.core.files.uploadedfile import SimpleUploadedFile
from chat.models import ChatRoom, Message
from tests.base import BaseTestCase


class ChatRoomListViewTests(BaseTestCase):
    """Lines 24-44: ChatRoomListView"""

    def test_get_rooms_empty(self):
        response = self.client.get(reverse("chat-rooms"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_get_rooms_with_participant(self):
        ChatRoom.get_or_create_room(self.user1.id, self.user2.id)
        response = self.client.get(reverse("chat-rooms"))
        self.assertEqual(len(response.data), 1)
        self.assertIn("id", response.data[0])
        self.assertIn("other_user", response.data[0])
        self.assertIn("last_message", response.data[0])

    def test_get_rooms_last_message_populated(self):
        room = ChatRoom.get_or_create_room(self.user1.id, self.user2.id)
        Message.objects.create(room=room, sender=self.user1, content="Hi there")
        response = self.client.get(reverse("chat-rooms"))
        self.assertEqual(response.data[0]["last_message"], "Hi there")

    def test_get_rooms_unauthenticated(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(reverse("chat-rooms"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class MessageListViewTests(BaseTestCase):
    """Lines 51-54: MessageListView"""

    def test_get_messages_empty(self):
        response = self.client.get(reverse("chat-messages", args=[self.user2.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_get_messages_returns_fields(self):
        room = ChatRoom.get_or_create_room(self.user1.id, self.user2.id)
        Message.objects.create(room=room, sender=self.user1, content="Hello")
        response = self.client.get(reverse("chat-messages", args=[self.user2.id]))
        self.assertIn("id", response.data[0])
        self.assertIn("sender_id", response.data[0])
        self.assertIn("content", response.data[0])


class SendMessageViewTests(BaseTestCase):
    """Lines 71-81: send_message"""

    def test_send_message_success(self):
        response = self.client.post(reverse("send-message"), {
            "recipient_id": str(self.user2.id), "content": "Hello!"
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "sent")

    def test_send_message_missing_fields(self):
        response = self.client.post(reverse("send-message"), {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_send_message_nonexistent_recipient(self):
        response = self.client.post(reverse("send-message"), {
            "recipient_id": str(uuid.uuid4()), "content": "Hi"
        })
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_send_message_unauthenticated(self):
        self.client.force_authenticate(user=None)
        response = self.client.post(reverse("send-message"), {
            "recipient_id": str(self.user2.id), "content": "Hi"
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class GetMessagesViewTests(BaseTestCase):
    """Lines 87-102: get_messages (poll)"""

    def test_poll_messages_returns_list(self):
        room = ChatRoom.get_or_create_room(self.user1.id, self.user2.id)
        Message.objects.create(room=room, sender=self.user1, content="Msg1")
        response = self.client.get(reverse("poll-messages", args=[self.user2.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["content"], "Msg1")

    def test_poll_messages_nonexistent_user(self):
        response = self.client.get(reverse("poll-messages", args=[uuid.uuid4()]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_poll_messages_unauthenticated(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(reverse("poll-messages", args=[self.user2.id]))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TypingViewTests(BaseTestCase):
    """Lines 112-141: typing and get_typing"""

    def test_typing_true(self):
        response = self.client.post(reverse("typing"), {
            "recipient_id": str(self.user2.id), "is_typing": True
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "ok")

    def test_typing_false(self):
        # First set typing true, then false to cover the pop branch
        self.client.post(reverse("typing"), {
            "recipient_id": str(self.user2.id), "is_typing": True
        })
        response = self.client.post(reverse("typing"), {
            "recipient_id": str(self.user2.id), "is_typing": False
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_typing_missing_recipient(self):
        response = self.client.post(reverse("typing"), {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_typing_returns_list(self):
        response = self.client.get(reverse("get-typing", args=[self.user2.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("typing_user_ids", response.data)


class EditMessageViewTests(BaseTestCase):
    """Lines 147-168: edit_message"""

    def _msg(self, sender, content="Original"):
        room = ChatRoom.get_or_create_room(self.user1.id, self.user2.id)
        return Message.objects.create(room=room, sender=sender, content=content)

    def test_edit_own_message(self):
        msg = self._msg(self.user1)
        response = self.client.put(reverse("edit-message", args=[msg.id]), {"content": "Edited"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["content"], "Edited")

    def test_edit_other_users_message_returns_403(self):
        msg = self._msg(self.user2)
        response = self.client.put(reverse("edit-message", args=[msg.id]), {"content": "Hack"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_edit_empty_content_returns_400(self):
        msg = self._msg(self.user1)
        response = self.client.put(reverse("edit-message", args=[msg.id]), {"content": "  "})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_edit_nonexistent_message_returns_404(self):
        response = self.client.put(reverse("edit-message", args=[uuid.uuid4()]), {"content": "x"})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class DeleteMessageViewTests(BaseTestCase):
    """Lines 177-184: delete_message"""

    def _msg(self, sender):
        room = ChatRoom.get_or_create_room(self.user1.id, self.user2.id)
        return Message.objects.create(room=room, sender=sender, content="bye")

    def test_delete_own_message(self):
        msg = self._msg(self.user1)
        response = self.client.delete(reverse("delete-message", args=[msg.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Message.objects.filter(id=msg.id).exists())

    def test_delete_other_users_message_returns_403(self):
        msg = self._msg(self.user2)
        response = self.client.delete(reverse("delete-message", args=[msg.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_nonexistent_returns_404(self):
        response = self.client.delete(reverse("delete-message", args=[uuid.uuid4()]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class UploadChatFileViewTests(BaseTestCase):
    """Lines 190-239: upload_chat_file"""

    def test_no_file_returns_400(self):
        response = self.client.post(reverse("upload-chat-file"), {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_file_type_returns_400(self):
        f = SimpleUploadedFile("bad.exe", b"MZ", content_type="application/octet-stream")
        response = self.client.post(reverse("upload-chat-file"), {"file": f}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_oversized_file_returns_400(self):
        big = SimpleUploadedFile(
            "big.pdf", b"%PDF" + b"\x00" * (10 * 1024 * 1024 + 1), content_type="application/pdf"
        )
        response = self.client.post(reverse("upload-chat-file"), {"file": big}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_valid_pdf_returns_200(self):
        pdf = SimpleUploadedFile("doc.pdf", b"%PDF-1.4 content", content_type="application/pdf")
        response = self.client.post(reverse("upload-chat-file"), {"file": pdf}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["is_image"])
        self.assertIn("url", response.data)

    def test_valid_image_sets_is_image_true(self):
        # Minimal valid PNG (1x1 pixel)
        png_bytes = (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
            b'\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00'
            b'\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18'
            b'\xd8N\x00\x00\x00\x00IEND\xaeB`\x82'
        )
        img = SimpleUploadedFile("photo.png", png_bytes, content_type="image/png")
        response = self.client.post(reverse("upload-chat-file"), {"file": img}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["is_image"])

    def test_unauthenticated_returns_401(self):
        self.client.force_authenticate(user=None)
        pdf = SimpleUploadedFile("doc.pdf", b"%PDF-1.4", content_type="application/pdf")
        response = self.client.post(reverse("upload-chat-file"), {"file": pdf}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)