"""
Tests for interactions/views.py covering the fixes:
- FollowUserView 404s on a nonexistent target user instead of creating a
  dangling Follow / misreporting IntegrityError as "already following"
- self-follow guard works regardless of whether the URL conf coerces
  user_id to a UUID or leaves it as a string
- FollowStatsView 404s for a nonexistent user instead of silently
  returning zeros for any failure
"""
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from interactions.models import Follow

User = get_user_model()

FOLLOW_URL = "/api/interactions/follow/{}/"
UNFOLLOW_URL = "/api/interactions/unfollow/{}/"
CHECK_FOLLOW_URL = "/api/interactions/check/{}/"
FOLLOWERS_URL = "/api/interactions/followers/{}/"
FOLLOWING_URL = "/api/interactions/following/{}/"
FOLLOW_STATS_URL = "/api/interactions/stats/{}/"


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def two_users(db):
    alice = User.objects.create_user(username="alice", email="alice@test.com", password="pass12345")
    bob = User.objects.create_user(username="bob", email="bob@test.com", password="pass12345")
    return alice, bob


class TestFollowUserView:
    def test_follow_creates_relationship_and_dispatches_notification(self, api_client, two_users):
        alice, bob = two_users
        api_client.force_authenticate(user=alice)

        with patch("interactions.views.create_follow_notification.delay") as mock_delay:
            response = api_client.post(FOLLOW_URL.format(bob.id))

        assert response.status_code == 201
        assert Follow.objects.filter(follower=alice, following=bob).exists()
        mock_delay.assert_called_once_with(str(alice.id), str(bob.id))

    def test_cannot_follow_self_even_as_string_user_id(self, api_client, two_users):
        alice, _ = two_users
        api_client.force_authenticate(user=alice)

        response = api_client.post(FOLLOW_URL.format(str(alice.id)))

        assert response.status_code == 400
        assert "yourself" in response.data["error"].lower()
        assert not Follow.objects.filter(follower=alice, following=alice).exists()

    def test_following_nonexistent_user_returns_404_not_already_following(self, api_client, two_users):
        alice, _ = two_users
        api_client.force_authenticate(user=alice)
        fake_user_id = "00000000-0000-0000-0000-000000000000"

        response = api_client.post(FOLLOW_URL.format(fake_user_id))

        assert response.status_code == 404
        assert response.data["error"] == "User not found"
        assert not Follow.objects.filter(follower=alice).exists()

    def test_following_same_user_twice_returns_already_following(self, api_client, two_users):
        alice, bob = two_users
        Follow.objects.create(follower=alice, following=bob)
        api_client.force_authenticate(user=alice)

        with patch("interactions.views.create_follow_notification.delay"):
            response = api_client.post(FOLLOW_URL.format(bob.id))

        assert response.status_code == 400
        assert "already following" in response.data["error"].lower()


class TestUnfollowUserView:
    def test_unfollow_removes_existing_relationship(self, api_client, two_users):
        alice, bob = two_users
        Follow.objects.create(follower=alice, following=bob)
        api_client.force_authenticate(user=alice)

        response = api_client.delete(UNFOLLOW_URL.format(bob.id))

        assert response.status_code == 200
        assert not Follow.objects.filter(follower=alice, following=bob).exists()

    def test_unfollowing_when_not_following_returns_400(self, api_client, two_users):
        alice, bob = two_users
        api_client.force_authenticate(user=alice)

        response = api_client.delete(UNFOLLOW_URL.format(bob.id))

        assert response.status_code == 400


class TestCheckFollowView:
    def test_returns_true_when_following(self, api_client, two_users):
        alice, bob = two_users
        Follow.objects.create(follower=alice, following=bob)
        api_client.force_authenticate(user=alice)

        response = api_client.get(CHECK_FOLLOW_URL.format(bob.id))

        assert response.data["is_following"] is True

    def test_returns_false_when_not_following(self, api_client, two_users):
        alice, bob = two_users
        api_client.force_authenticate(user=alice)

        response = api_client.get(CHECK_FOLLOW_URL.format(bob.id))

        assert response.data["is_following"] is False


class TestFollowersAndFollowingList:
    def test_followers_list_returns_users_following_target(self, api_client, two_users):
        alice, bob = two_users
        Follow.objects.create(follower=alice, following=bob)
        api_client.force_authenticate(user=alice)

        response = api_client.get(FOLLOWERS_URL.format(bob.id))

        assert response.status_code == 200
        assert len(response.data) == 1

    def test_followers_list_404s_for_nonexistent_user(self, api_client, two_users):
        alice, _ = two_users
        api_client.force_authenticate(user=alice)

        response = api_client.get(FOLLOWERS_URL.format("00000000-0000-0000-0000-000000000000"))

        assert response.status_code == 404

    def test_following_list_returns_users_target_follows(self, api_client, two_users):
        alice, bob = two_users
        Follow.objects.create(follower=alice, following=bob)
        api_client.force_authenticate(user=alice)

        response = api_client.get(FOLLOWING_URL.format(alice.id))

        assert response.status_code == 200
        assert len(response.data) == 1


class TestFollowStatsView:
    def test_returns_correct_counts(self, api_client, two_users):
        alice, bob = two_users
        carol = User.objects.create_user(username="carol", email="carol@test.com", password="pass12345")
        Follow.objects.create(follower=alice, following=bob)
        Follow.objects.create(follower=carol, following=bob)
        Follow.objects.create(follower=bob, following=alice)
        api_client.force_authenticate(user=alice)

        response = api_client.get(FOLLOW_STATS_URL.format(bob.id))

        assert response.status_code == 200
        assert response.data["followers_count"] == 2
        assert response.data["following_count"] == 1

    def test_returns_404_for_nonexistent_user_instead_of_fake_zeros(self, api_client, two_users):
        alice, _ = two_users
        api_client.force_authenticate(user=alice)

        response = api_client.get(FOLLOW_STATS_URL.format("00000000-0000-0000-0000-000000000000"))


        assert response.status_code == 404

    def test_zero_counts_for_real_user_with_no_relationships(self, api_client, two_users):
        alice, bob = two_users
        api_client.force_authenticate(user=alice)

        response = api_client.get(FOLLOW_STATS_URL.format(bob.id))

        assert response.status_code == 200
        assert response.data["followers_count"] == 0
        assert response.data["following_count"] == 0