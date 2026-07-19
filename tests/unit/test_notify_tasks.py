"""
Tests for notify/tasks.py covering the three fixes made earlier:

1. send_single_notification now creates notification_type="new_post",
   not the previous hardcoded (and wrong) "like".
2. Emails build links from settings.FRONTEND_URL instead of a hardcoded
   127.0.0.1 URL.
3. Failures raise/retry instead of being swallowed by a bare print().

Requires CELERY_TASK_ALWAYS_EAGER=True (or these tasks are called with
`.run()` / directly rather than `.delay()`) so they execute synchronously
in-process during tests. mailoutbox/send_mail is asserted via Django's
locmem backend (settings.py already switches EMAIL_BACKEND to locmem when
"test" in sys.argv).
"""
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import override_settings

from interactions.models import Follow
from notify.models import Notification
from notify.tasks import (
    create_follow_notification,
    create_like_notification,
    fan_out_notification_to_followers,
    send_password_reset_email,
    send_single_notification,
    send_verification_email,
    send_welcome_email,
)

User = get_user_model()


@pytest.fixture
def two_users(db):
    author = User.objects.create_user(username="author", email="author@test.com", password="pass12345")
    reader = User.objects.create_user(username="reader", email="reader@test.com", password="pass12345")
    return author, reader


class TestSendSingleNotification:
    def test_creates_notification_with_new_post_type_not_like(self, db, two_users):
        author, reader = two_users

        send_single_notification(reader.id, author.id, post_id=1, message="author shared a new post")

        notification = Notification.objects.get(recipient_id=reader.id, sender_id=author.id)
        assert notification.notification_type == "new_post"
        assert notification.message == "author shared a new post"

    def test_retries_instead_of_swallowing_on_db_failure(self, db, two_users):
        author, reader = two_users

        with patch("notify.tasks.Notification.objects.create", side_effect=Exception("db down")):
            with pytest.raises(Exception):
                # bind=True task called directly (not via delay) still goes
                # through self.retry, which re-raises when retries are
                # exhausted / outside a real worker context — the key
                # behavioral change is that this no longer returns silently.
                send_single_notification.run(reader.id, author.id, post_id=1, message="x")


class TestFanOutNotificationToFollowers:
    def test_dispatches_one_task_per_follower(self, db, two_users):
        author, reader = two_users
        another_reader = User.objects.create_user(
            username="reader2", email="reader2@test.com", password="pass12345"
        )
        Follow.objects.create(follower=reader, following=author)
        Follow.objects.create(follower=another_reader, following=author)

        with patch("notify.tasks.send_single_notification.delay") as mock_delay:
            result = fan_out_notification_to_followers(
                author.id, post_id=1, message="new post!", follower_count=2
            )

        assert result["notifications_sent"] == 2
        assert mock_delay.call_count == 2

    def test_logs_warning_on_follower_count_mismatch(self, db, two_users, caplog):
        author, reader = two_users
        Follow.objects.create(follower=reader, following=author)

        with patch("notify.tasks.send_single_notification.delay"):
            with caplog.at_level("WARNING"):
                fan_out_notification_to_followers(
                    author.id, post_id=1, message="new post!", follower_count=99
                )

        assert any("mismatch" in record.message.lower() for record in caplog.records)

    def test_no_followers_returns_zero_sent(self, db, two_users):
        author, _ = two_users
        with patch("notify.tasks.send_single_notification.delay") as mock_delay:
            result = fan_out_notification_to_followers(
                author.id, post_id=1, message="new post!", follower_count=0
            )
        assert result["notifications_sent"] == 0
        mock_delay.assert_not_called()


class TestEmailTasksUseFrontendUrl:
    @override_settings(FRONTEND_URL="https://app.example.com")
    def test_verification_email_links_to_frontend_url(self, db):
        send_verification_email("user-id-1", "user@test.com", "sometoken")

        assert len(mail.outbox) == 1
        sent = mail.outbox[0]
        assert "https://app.example.com/verify-email" in sent.body
        assert "127.0.0.1" not in sent.body
        assert "sometoken" in sent.body

    @override_settings(FRONTEND_URL="https://app.example.com")
    def test_password_reset_email_links_to_frontend_url(self, db):
        send_password_reset_email("user-id-1", "user@test.com", "resettoken")

        assert len(mail.outbox) == 1
        sent = mail.outbox[0]
        assert "https://app.example.com/password-reset-confirm" in sent.body
        assert "127.0.0.1" not in sent.body

    def test_welcome_email_sends_to_correct_recipient(self, db):
        send_welcome_email("user-id-1", "user@test.com", "someusername")

        assert len(mail.outbox) == 1
        sent = mail.outbox[0]
        assert sent.to == ["user@test.com"]
        assert "someusername" in sent.body


class TestFollowAndLikeNotifications:
    def test_create_follow_notification_sets_correct_type_and_direction(self, db, two_users):
        author, reader = two_users

        create_follow_notification(following_id=author.id, follower_id=reader.id)

        notification = Notification.objects.get(recipient_id=author.id, sender_id=reader.id)
        assert notification.notification_type == "follow"

    def test_create_like_notification_sets_correct_type_and_direction(self, db, two_users):
        author, reader = two_users

        create_like_notification(post_owner_id=author.id, liker_id=reader.id, post_id=5)

        notification = Notification.objects.get(recipient_id=author.id, sender_id=reader.id)
        assert notification.notification_type == "like"

    def test_create_follow_notification_retries_on_failure(self, db, two_users):
        author, reader = two_users
        with patch("notify.tasks.Notification.objects.create", side_effect=Exception("db down")):
            with pytest.raises(Exception):
                create_follow_notification.run(following_id=author.id, follower_id=reader.id)