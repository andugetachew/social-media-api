from unittest.mock import patch, MagicMock
from django.core import mail
from django.test import TestCase
from django.contrib.auth import get_user_model
from celery import current_app as celery_app
from notify.tasks import (
    send_verification_email,
    send_welcome_email,
    fan_out_notification_to_followers,
)
from posts.models import Post
from interactions.models import Follow

User = get_user_model()


class AsyncTaskTests(TestCase):
    """Test Celery async tasks"""

    def setUp(self):
        celery_app.conf.update(CELERY_ALWAYS_EAGER=True)

        self.user1 = User.objects.create_user(
            email="user1@test.com", username="user1", password="testpass"
        )
        self.user2 = User.objects.create_user(
            email="user2@test.com", username="user2", password="testpass"
        )

    def test_send_verification_email_task(self):
        """Test verification email task"""
        result = send_verification_email.delay(
            str(self.user1.id), self.user1.email, "test-token-123"
        )

        self.assertTrue(result.successful())
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Verify Your Email", mail.outbox[0].subject)
        self.assertIn(self.user1.email, mail.outbox[0].to)

    def test_send_welcome_email_task(self):
        """Test welcome email task"""
        result = send_welcome_email.delay(
            str(self.user1.id), self.user1.email, self.user1.username
        )

        self.assertTrue(result.successful())
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Welcome", mail.outbox[0].subject)

    @patch("notify.tasks.send_single_notification.delay")
    def test_fan_out_notification_to_followers(self, mock_send):
        Follow.objects.create(follower=self.user2, following=self.user1)
        user3 = User.objects.create_user(
            email="user3@test.com", username="user3", password="testpass"
        )
        Follow.objects.create(follower=user3, following=self.user1)
        post = Post.objects.create(author=self.user1, content="Test post")

        # Call directly instead of .delay() to test the logic
        result = fan_out_notification_to_followers(
            str(self.user1.id), str(post.id), "New post from user1", 2
        )
        self.assertEqual(mock_send.call_count, 2)
        self.assertEqual(result["notifications_sent"], 2)
