from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from interactions.models import Follow

User = get_user_model()


class SocialActionsTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user1 = User.objects.create_user(
            email="user1@test.com", username="user1", password="pass123"
        )
        self.user2 = User.objects.create_user(
            email="user2@test.com", username="user2", password="pass123"
        )
        self.client.force_authenticate(user=self.user1)

    def test_follow_user(self):
        response = self.client.post(reverse("follow", args=[self.user2.id]))
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Follow.objects.count(), 1)

    def test_unfollow_user(self):
        Follow.objects.create(follower=self.user1, following=self.user2)
        response = self.client.delete(reverse("unfollow", args=[self.user2.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Follow.objects.count(), 0)

    def test_cannot_follow_self(self):
        response = self.client.post(reverse("follow", args=[self.user1.id]))
        self.assertEqual(response.status_code, 201)

    def test_follow_stats(self):
        Follow.objects.create(follower=self.user2, following=self.user1)
        response = self.client.get(reverse("follow-stats", args=[self.user1.id]))
        self.assertEqual(response.data["followers_count"], 1)
        self.assertEqual(response.data["following_count"], 0)

    def test_followers_list(self):
        Follow.objects.create(follower=self.user2, following=self.user1)
        response = self.client.get(reverse("followers", args=[self.user1.id]))
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["username"], "user2")

    def test_following_list(self):
        Follow.objects.create(follower=self.user1, following=self.user2)
        response = self.client.get(reverse("following", args=[self.user1.id]))
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["username"], "user2")
