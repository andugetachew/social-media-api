from django.urls import reverse
from rest_framework import status
from interactions.models import Follow
from tests.base import BaseTestCase


class FollowSystemTests(BaseTestCase):
    """Test follow/unfollow functionality"""

    def test_follow_user(self):
        """Test following another user"""
        url = reverse("follow", args=[self.user2.id])
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Follow.objects.count(), 1)
        self.assertTrue(
            Follow.objects.filter(follower=self.user1, following=self.user2).exists()
        )

    def test_unfollow_user(self):
        """Test unfollowing a user"""
        self.create_follow(self.user1, self.user2)
        url = reverse("unfollow", args=[self.user2.id])
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Follow.objects.count(), 0)

    def test_follow_self(self):
        """Test trying to follow yourself (should fail)"""
        url = reverse("follow", args=[self.user1.id])
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_follow_already_following(self):
        """Test following a user already followed (should be idempotent)"""
        self.create_follow(self.user1, self.user2)
        url = reverse("follow", args=[self.user2.id])
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unfollow_not_following(self):
        """Test unfollowing a user not followed"""
        url = reverse("unfollow", args=[self.user2.id])
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_followers_list(self):
        """Test retrieving followers list"""
        self.create_follow(self.user2, self.user1)
        self.create_follow(self.user3, self.user1)

        url = reverse("followers", args=[self.user1.id])
        response = self.client.get(url)

        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]["username"], self.user2.username)

    def test_get_following_list(self):
        """Test retrieving following list"""
        self.create_follow(self.user1, self.user2)
        self.create_follow(self.user1, self.user3)

        url = reverse("following", args=[self.user1.id])
        response = self.client.get(url)

        self.assertEqual(len(response.data), 2)

    def test_follow_stats(self):
        """Test follower/following counts"""
        self.create_follow(self.user2, self.user1)
        self.create_follow(self.user3, self.user1)
        self.create_follow(self.user1, self.user2)

        url = reverse("follow-stats", args=[self.user1.id])
        response = self.client.get(url)

        self.assertEqual(response.data["followers_count"], 2)
        self.assertEqual(response.data["following_count"], 1)
