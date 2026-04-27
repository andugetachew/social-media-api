from django.test import TestCase
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from posts.models import Post
from interactions.models import Follow
from django.urls import reverse

User = get_user_model()


class FeedTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user1 = User.objects.create_user(
            email="user1@test.com", username="user1", password="pass123"
        )
        self.user2 = User.objects.create_user(
            email="user2@test.com", username="user2", password="pass123"
        )
        self.client.force_authenticate(user=self.user1)

    def test_feed_shows_followed_users_posts(self):
        Post.objects.create(author=self.user2, content="User2 post")
        Follow.objects.create(follower=self.user1, following=self.user2)
        response = self.client.get(reverse("feed"))
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["content"], "User2 post")

    def test_feed_shows_own_posts(self):
        Post.objects.create(author=self.user1, content="My own post")
        response = self.client.get(reverse("feed"))
        self.assertEqual(len(response.data["results"]), 1)

    def test_feed_does_not_show_unfollowed_posts(self):
        Post.objects.create(author=self.user2, content="Hidden post")
        response = self.client.get(reverse("feed"))
        self.assertEqual(len(response.data["results"]), 0)

    def test_feed_pagination(self):
        for i in range(15):
            Post.objects.create(author=self.user1, content=f"Post {i}")
        response = self.client.get(reverse("feed") + "?page=1&page_size=10")
        self.assertEqual(len(response.data["results"]), 10)
        self.assertIsNotNone(response.data["next"])
