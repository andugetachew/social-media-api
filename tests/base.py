from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from django.core.cache import cache
from unittest.mock import patch, MagicMock
from celery import current_app as celery_app

User = get_user_model()


class BaseTestCase(TestCase):
    """Base test class with common setup and utilities"""

    def setUp(self):
        self.client = APIClient()
        cache.clear()
        celery_app.conf.update(
            task_always_eager=True,
            task_eager_propagates=True,
        )
        # Create test users
        self.user1 = User.objects.create_user(
            email="user1@test.com",
            username="user1",
            password="testpass123",
            full_name="Test User 1",
        )

        self.user2 = User.objects.create_user(
            email="user2@test.com",
            username="user2",
            password="testpass123",
            full_name="Test User 2",
        )

        self.user3 = User.objects.create_user(
            email="user3@test.com",
            username="user3",
            password="testpass123",
            full_name="Test User 3",
        )

        self.authenticate(self.user1)

    def authenticate(self, user):
        """Authenticate client with user"""
        self.client.force_authenticate(user=user)

    def get_access_token(self, user):
        """Get JWT access token for user"""
        from rest_framework_simplejwt.tokens import RefreshToken

        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)

    def create_post(self, author, content="Test post content"):
        """Helper to create a post"""
        from posts.models import Post

        return Post.objects.create(author=author, content=content)

    def create_comment(self, author, post, content="Test comment"):
        """Helper to create a comment"""
        from comments.models import Comment

        return Comment.objects.create(author=author, post=post, content=content)

    def create_follow(self, follower, following):
        """Helper to create a follow relationship"""
        from interactions.models import Follow

        return Follow.objects.create(follower=follower, following=following)
