"""
Tests for notify/views.py, including MarkAllNotificationsReadView, which
was documented in the README but missing from the original file.
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from notify.models import Notification

User = get_user_model()

NOTIFICATIONS_URL = "/api/notifications/"
MARK_READ_URL = "/api/notifications/{}/read/"
MARK_ALL_READ_URL = "/api/notifications/mark-all-read/"


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def two_users(db):
    alice = User.objects.create_user(username="alice", email="alice@test.com", password="pass12345")
    bob = User.objects.create_user(username="bob", email="bob@test.com", password="pass12345")
    return alice, bob


class TestNotificationListView:
    def test_returns_only_current_users_notifications(self, api_client, two_users):
        alice, bob = two_users
        Notification.objects.create(
            recipient=alice, sender=bob, notification_type="follow", message="bob followed you"
        )
        Notification.objects.create(
            recipient=bob, sender=alice, notification_type="follow", message="alice followed you"
        )
        api_client.force_authenticate(user=alice)

        response = api_client.get(NOTIFICATIONS_URL)

        assert response.status_code == 200
        assert len(response.data) == 1

    def test_ordered_most_recent_first(self, api_client, two_users):
        # created_at uses auto_now_add, so two Notification.objects.create()
        # calls in quick succession within a test can land in the same
        # timestamp resolution window and produce a genuine tie. Rather
        # than adding an id-based tiebreaker in production code (id is a
        # random UUID here, not sequential, so it wouldn't reflect actual
        # recency anyway), control the timestamps explicitly in the test:
        # auto_now_add prevents setting created_at on create(), so update()
        # it afterward to force a clear, unambiguous ordering.
        alice, bob = two_users
        first = Notification.objects.create(
            recipient=alice, sender=bob, notification_type="follow", message="first"
        )
        second = Notification.objects.create(
            recipient=alice, sender=bob, notification_type="like", message="second"
        )
        from django.utils import timezone
        import datetime
        Notification.objects.filter(id=first.id).update(
            created_at=timezone.now() - datetime.timedelta(seconds=10)
        )
        Notification.objects.filter(id=second.id).update(
            created_at=timezone.now()
        )
        api_client.force_authenticate(user=alice)

        response = api_client.get(NOTIFICATIONS_URL)

        assert response.data[0]["message"] == "second"
        assert response.data[1]["message"] == "first"

    def test_caps_at_50_results(self, api_client, two_users):
        alice, bob = two_users
        for i in range(60):
            Notification.objects.create(
                recipient=alice, sender=bob, notification_type="like", message=f"n{i}"
            )
        api_client.force_authenticate(user=alice)

        response = api_client.get(NOTIFICATIONS_URL)

        assert len(response.data) == 50


class TestMarkNotificationReadView:
    def test_marks_own_notification_as_read(self, api_client, two_users):
        alice, bob = two_users
        notification = Notification.objects.create(
            recipient=alice, sender=bob, notification_type="follow", message="x", is_read=False
        )
        api_client.force_authenticate(user=alice)

        response = api_client.post(MARK_READ_URL.format(notification.id))

        assert response.status_code == 200
        notification.refresh_from_db()
        assert notification.is_read is True

    def test_cannot_mark_another_users_notification_as_read(self, api_client, two_users):
        alice, bob = two_users
        notification = Notification.objects.create(
            recipient=bob, sender=alice, notification_type="follow", message="x", is_read=False
        )
        api_client.force_authenticate(user=alice)

        response = api_client.post(MARK_READ_URL.format(notification.id))

        assert response.status_code == 404
        notification.refresh_from_db()
        assert notification.is_read is False

    def test_nonexistent_notification_returns_404(self, api_client, two_users):
        alice, _ = two_users
        api_client.force_authenticate(user=alice)

        response = api_client.post(
            MARK_READ_URL.format("00000000-0000-0000-0000-000000000000")
        )

        assert response.status_code == 404


class TestMarkAllNotificationsReadView:
    def test_marks_all_unread_notifications_as_read(self, api_client, two_users):
        alice, bob = two_users
        for i in range(5):
            Notification.objects.create(
                recipient=alice, sender=bob, notification_type="like", message=f"n{i}", is_read=False
            )
        api_client.force_authenticate(user=alice)

        response = api_client.post(MARK_ALL_READ_URL)

        assert response.status_code == 200
        assert response.data["count"] == 5
        assert Notification.objects.filter(recipient=alice, is_read=False).count() == 0

    def test_does_not_touch_another_users_notifications(self, api_client, two_users):
        alice, bob = two_users
        bobs_notification = Notification.objects.create(
            recipient=bob, sender=alice, notification_type="like", message="x", is_read=False
        )
        api_client.force_authenticate(user=alice)

        api_client.post(MARK_ALL_READ_URL)

        bobs_notification.refresh_from_db()
        assert bobs_notification.is_read is False

    def test_already_read_notifications_are_not_recounted(self, api_client, two_users):
        alice, bob = two_users
        Notification.objects.create(
            recipient=alice, sender=bob, notification_type="like", message="already read", is_read=True
        )
        Notification.objects.create(
            recipient=alice, sender=bob, notification_type="like", message="unread", is_read=False
        )
        api_client.force_authenticate(user=alice)

        response = api_client.post(MARK_ALL_READ_URL)

        assert response.data["count"] == 1

    def test_no_unread_notifications_returns_zero_count(self, api_client, two_users):
        alice, _ = two_users
        api_client.force_authenticate(user=alice)

        response = api_client.post(MARK_ALL_READ_URL)

        assert response.status_code == 200
        assert response.data["count"] == 0