from django.urls import reverse
from rest_framework import status
from posts.models import Post
from comments.models import Comment
from tests.base import BaseTestCase


class CommentTests(BaseTestCase):
    """Test comment functionality"""

    def setUp(self):
        super().setUp()
        self.post = self.create_post(self.user2, "Post for comments")

    def test_add_comment(self):
        """Test adding a comment to a post"""
        url = reverse("comments", args=[self.post.id])
        data = {"content": "Great post!"}
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Comment.objects.count(), 1)
        self.assertEqual(response.data["content"], "Great post!")

    def test_add_empty_comment(self):
        """Test adding empty comment (should fail)"""
        url = reverse("comments", args=[self.post.id])
        data = {"content": ""}
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_comments(self):
        """Test retrieving comments for a post"""
        self.create_comment(self.user1, self.post, "First")
        self.create_comment(self.user2, self.post, "Second")

        url = reverse("comments", args=[self.post.id])
        response = self.client.get(url)

        self.assertEqual(len(response.data), 2)

    def test_delete_own_comment(self):
        """Test deleting own comment"""
        comment = self.create_comment(self.user1, self.post, "My comment")
        url = reverse("comment-delete", args=[comment.id])
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Comment.objects.count(), 0)

    def test_delete_others_comment(self):
        """Test deleting another user's comment (should fail)"""
        comment = self.create_comment(self.user2, self.post, "Their comment")
        url = reverse("comment-delete", args=[comment.id])
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_comment_on_nonexistent_post(self):
        import uuid

        url = reverse("comments", args=[uuid.uuid4()])
        data = {"content": "Comment on missing post"}
        response = self.client.post(url, data)
        self.assertEqual(
            response.status_code, status.HTTP_404_NOT_FOUND
        )  # ← 404 not 403
