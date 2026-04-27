from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from posts.models import Post, Like

User = get_user_model()


class PostAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user1 = User.objects.create_user(
            email="user1@test.com", username="user1", password="pass123"
        )
        self.user2 = User.objects.create_user(
            email="user2@test.com", username="user2", password="pass123"
        )
        self.client.force_authenticate(user=self.user1)

    def test_create_post(self):
        response = self.client.post(reverse("posts"), {"content": "Test post"})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Post.objects.count(), 1)

    def test_get_user_posts(self):
        Post.objects.create(author=self.user1, content="Post 1")
        Post.objects.create(author=self.user1, content="Post 2")
        response = self.client.get(reverse("posts"))
        self.assertEqual(len(response.data), 2)

    def test_delete_own_post(self):
        post = Post.objects.create(author=self.user1, content="Delete me")
        response = self.client.delete(reverse("post-detail", args=[post.id]))
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Post.objects.count(), 0)

    def test_cannot_delete_others_post(self):
        post = Post.objects.create(author=self.user2, content="Someone's post")
        response = self.client.delete(reverse("post-detail", args=[post.id]))
        self.assertEqual(response.status_code, 404)

    def test_like_post(self):
        post = Post.objects.create(author=self.user2, content="Target")
        response = self.client.post(reverse("like", args=[post.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Like.objects.count(), 1)

    def test_unlike_post(self):
        post = Post.objects.create(author=self.user2, content="Target")
        Like.objects.create(user=self.user1, post=post)
        response = self.client.post(reverse("like", args=[post.id]))
        self.assertEqual(Like.objects.count(), 0)
