from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from chat.models import ChatRoom, Message

User = get_user_model()


class ChatFlowTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user1 = User.objects.create_user(
            email="user1@test.com", username="user1", password="pass123"
        )
        self.user2 = User.objects.create_user(
            email="user2@test.com", username="user2", password="pass123"
        )
        self.client.force_authenticate(user=self.user1)

    def test_create_room(self):
        room = ChatRoom.get_or_create_room(self.user1.id, self.user2.id)
        self.assertIn(self.user1, room.participants.all())
        self.assertIn(self.user2, room.participants.all())

    def test_send_message(self):
        response = self.client.post(
            reverse("send-message"),
            {"recipient_id": str(self.user2.id), "content": "Hello"},
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Message.objects.count(), 1)

    def test_get_messages(self):
        room = ChatRoom.get_or_create_room(self.user1.id, self.user2.id)
        Message.objects.create(room=room, sender=self.user1, content="Hi")
        response = self.client.get(reverse("poll-messages", args=[self.user2.id]))
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["content"], "Hi")

    def test_delete_own_message(self):
        room = ChatRoom.get_or_create_room(self.user1.id, self.user2.id)
        msg = Message.objects.create(room=room, sender=self.user1, content="Delete me")
        response = self.client.delete(reverse("delete-message", args=[msg.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Message.objects.count(), 0)

    def test_cannot_delete_others_message(self):
        room = ChatRoom.get_or_create_room(self.user1.id, self.user2.id)
        msg = Message.objects.create(room=room, sender=self.user2, content="Not mine")
        response = self.client.delete(reverse("delete-message", args=[msg.id]))
        self.assertEqual(response.status_code, 403)
