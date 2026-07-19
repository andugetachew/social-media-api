"""
Tests for comments/views.py, including the fix that excludes
deactivated/flagged posts from being read or commented on — previously
Post.objects.get(id=post_id) ignored is_active entirely.
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from comments.models import Comment
from posts.models import Post

User = get_user_model()

COMMENTS_URL = "/api/comments/post/{}/"
COMMENT_DELETE_URL = "/api/comments/{}/"


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def two_users(db):
    alice = User.objects.create_user(username="alice", email="alice@test.com", password="pass12345")
    bob = User.objects.create_user(username="bob", email="bob@test.com", password="pass12345")
    return alice, bob


class TestCommentListCreateView:
    def test_lists_comments_on_active_post(self, api_client, two_users):
        alice, bob = two_users
        post = Post.objects.create(author=bob, content="hello")
        Comment.objects.create(author=alice, post=post, content="nice post")
        api_client.force_authenticate(user=alice)

        response = api_client.get(COMMENTS_URL.format(post.id))

        assert response.status_code == 200
        assert len(response.data) == 1

    def test_creates_comment_on_active_post(self, api_client, two_users):
        alice, bob = two_users
        post = Post.objects.create(author=bob, content="hello")
        api_client.force_authenticate(user=alice)

        response = api_client.post(COMMENTS_URL.format(post.id), {"content": "great!"})

        assert response.status_code == 201
        assert Comment.objects.filter(post=post, author=alice, content="great!").exists()

    def test_cannot_list_comments_on_deactivated_post(self, api_client, two_users):
        alice, bob = two_users
        post = Post.objects.create(author=bob, content="hidden", is_active=False)
        Comment.objects.create(author=alice, post=post, content="old comment")
        api_client.force_authenticate(user=alice)

        response = api_client.get(COMMENTS_URL.format(post.id))

        assert response.status_code == 404

    def test_cannot_comment_on_deactivated_post(self, api_client, two_users):
        alice, bob = two_users
        post = Post.objects.create(author=bob, content="hidden", is_active=False)
        api_client.force_authenticate(user=alice)

        response = api_client.post(COMMENTS_URL.format(post.id), {"content": "sneaky comment"})

        assert response.status_code == 404
        assert not Comment.objects.filter(post=post, content="sneaky comment").exists()

    def test_nonexistent_post_returns_404(self, api_client, two_users):
        alice, _ = two_users
        api_client.force_authenticate(user=alice)

        response = api_client.get(
            COMMENTS_URL.format("00000000-0000-0000-0000-000000000000")
        )

        assert response.status_code == 404


class TestCommentDeleteView:
    def test_author_can_delete_own_comment(self, api_client, two_users):
        alice, bob = two_users
        post = Post.objects.create(author=bob, content="hello")
        comment = Comment.objects.create(author=alice, post=post, content="mine")
        api_client.force_authenticate(user=alice)

        response = api_client.delete(COMMENT_DELETE_URL.format(comment.id))

        assert response.status_code == 200
        assert not Comment.objects.filter(id=comment.id).exists()

    def test_non_author_cannot_delete_comment(self, api_client, two_users):
        alice, bob = two_users
        post = Post.objects.create(author=bob, content="hello")
        comment = Comment.objects.create(author=alice, post=post, content="mine")
        api_client.force_authenticate(user=bob)

        response = api_client.delete(COMMENT_DELETE_URL.format(comment.id))

        assert response.status_code == 403
        assert Comment.objects.filter(id=comment.id).exists()

    def test_deleting_nonexistent_comment_returns_404(self, api_client, two_users):
        alice, _ = two_users
        api_client.force_authenticate(user=alice)

        response = api_client.delete(
            COMMENT_DELETE_URL.format("00000000-0000-0000-0000-000000000000")
        )

        assert response.status_code == 404