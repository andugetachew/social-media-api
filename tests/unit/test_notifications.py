from unittest.mock import patch, call
from django.urls import reverse
from rest_framework import status
from notify.models import Notification
from tests.base import BaseTestCase


class NotificationTests(BaseTestCase):
    """Test notification system with async tasks"""

    @patch("notify.tasks.create_like_notification.delay")
    def test_notification_on_like(self, mock_notify):
        """Test notification sent when someone likes your post"""
        post = self.create_post(self.user2, "Post for likes")

        url = reverse("like", args=[post.id])
        self.client.post(url)

        mock_notify.assert_called_once_with(
            str(self.user2.id), str(self.user1.id), str(post.id)
        )

    @patch("notify.tasks.create_follow_notification.delay")
    def test_notification_on_follow(self, mock_notify):
        """Test notification sent when someone follows you"""
        url = reverse("follow", args=[self.user2.id])
        self.client.post(url)

        mock_notify.assert_called_once_with(str(self.user1.id), str(self.user2.id))

    def test_notification_list(self):
        """Test retrieving user notifications"""
        # Create a notification directly
        Notification.objects.create(
            recipient=self.user1,
            sender=self.user2,
            notification_type="like",
            message="User2 liked your post",
        )

        url = reverse("notifications")
        response = self.client.get(url)

        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["notification_type"], "like")

    def test_mark_notification_read(self):
        """Test marking a notification as read"""
        notification = Notification.objects.create(
            recipient=self.user1,
            notification_type="follow",
            message="New follower",
            is_read=False,
        )

        url = reverse("mark-read", args=[notification.id])
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)

    def test_unread_notification_count(self):
        """Test unread notification count"""
        Notification.objects.create(
            recipient=self.user1, is_read=False, notification_type="like", message=""
        )
        Notification.objects.create(
            recipient=self.user1, is_read=False, notification_type="like", message=""
        )
        Notification.objects.create(
            recipient=self.user1, is_read=True, notification_type="like", message=""
        )

        unread_count = Notification.objects.filter(
            recipient=self.user1, is_read=False
        ).count()
        self.assertEqual(unread_count, 2)
