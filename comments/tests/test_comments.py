from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from posts.models import Post
from comments.models import Comment

User = get_user_model()


class CommentsTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user1 = User.objects.create_user(
            email="user1@test.com", username="user1", password="pass123"
        )
        self.user2 = User.objects.create_user(
            email="user2@test.com", username="user2", password="pass123"
        )
        self.client.force_authenticate(user=self.user1)
        self.post = Post.objects.create(author=self.user2, content="Test post")

    def test_add_comment(self):
        response = self.client.post(
            reverse("comments", args=[self.post.id]), {"content": "Nice!"}
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Comment.objects.count(), 1)

    def test_get_comments(self):
        Comment.objects.create(author=self.user1, post=self.post, content="First")
        Comment.objects.create(author=self.user2, post=self.post, content="Second")
        response = self.client.get(reverse("comments", args=[self.post.id]))
        self.assertEqual(len(response.data), 2)

    def test_delete_own_comment(self):
        comment = Comment.objects.create(
            author=self.user1, post=self.post, content="Mine"
        )
        response = self.client.delete(reverse("comment-delete", args=[comment.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Comment.objects.count(), 0)

    def test_cannot_delete_others_comment(self):
        comment = Comment.objects.create(
            author=self.user2, post=self.post, content="Theirs"
        )
        response = self.client.delete(reverse("comment-delete", args=[comment.id]))
        self.assertEqual(response.status_code, 403)

    def test_empty_comment_not_allowed(self):
        response = self.client.post(
            reverse("comments", args=[self.post.id]), {"content": ""}
        )
        self.assertEqual(response.status_code, 400)
