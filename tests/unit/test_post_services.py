"""
Tests for posts/services.py: PostService.

Covers the fixes made:
- fan_out_notification_to_followers.delay() only fires after the
  transaction commits (transaction.on_commit), not immediately inside it
- toggle_like survives a get_or_create race against the unique_together
  constraint instead of raising IntegrityError
- whitespace-only content is rejected, not just empty/oversized content

django_capture_on_commit_callbacks (pytest-django) is used to explicitly
run on_commit callbacks in tests, since Django's test transactions roll
back rather than commit by default — without this, on_commit callbacks
never fire in a normal TestCase-wrapped test, which would make the fix
untestable with a plain "was .delay() called" assertion.
"""
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from interactions.models import Follow
from posts.models import Like, Post
from posts.services import PostService

User = get_user_model()


@pytest.fixture
def author(db):
    return User.objects.create_user(username="author", email="author@test.com", password="pass12345")


@pytest.fixture
def follower(db):
    return User.objects.create_user(username="follower", email="follower@test.com", password="pass12345")


class TestCreatePost:
    def test_creates_post_with_valid_content(self, author):
        result = PostService.create_post(str(author.id), "hello world")

        assert result["content"] == "hello world"
        assert result["author_id"] == str(author.id)
        assert Post.objects.filter(author=author, content="hello world").exists()

    def test_rejects_empty_content(self, author):
        with pytest.raises(ValueError, match="1-280 characters"):
            PostService.create_post(str(author.id), "")

    def test_rejects_whitespace_only_content(self, author):
        with pytest.raises(ValueError, match="1-280 characters"):
            PostService.create_post(str(author.id), "   \n\t  ")

    def test_rejects_content_over_280_chars(self, author):
        with pytest.raises(ValueError, match="1-280 characters"):
            PostService.create_post(str(author.id), "x" * 281)

    def test_accepts_content_at_exactly_280_chars(self, author):
        result = PostService.create_post(str(author.id), "x" * 280)
        assert len(result["content"]) == 280

    def test_no_notification_dispatched_when_no_followers(self, author, django_capture_on_commit_callbacks):
        with patch("posts.services.fan_out_notification_to_followers.delay") as mock_delay:
            with django_capture_on_commit_callbacks(execute=True):
                result = PostService.create_post(str(author.id), "no followers yet")

        assert result["notifications_queued"] == 0
        mock_delay.assert_not_called()

    def test_notification_not_dispatched_until_transaction_commits(
        self, author, follower, django_capture_on_commit_callbacks
    ):
        Follow.objects.create(follower=follower, following=author)

        with patch("posts.services.fan_out_notification_to_followers.delay") as mock_delay:
            # capture without executing yet — proves the call is deferred,
            # not fired inside the atomic block
            with django_capture_on_commit_callbacks(execute=False) as callbacks:
                PostService.create_post(str(author.id), "hello followers")
            mock_delay.assert_not_called()
            assert len(callbacks) == 1

            for callback in callbacks:
                callback()

        mock_delay.assert_called_once()

    def test_notification_dispatched_after_commit_with_correct_args(
        self, author, follower, django_capture_on_commit_callbacks
    ):
        Follow.objects.create(follower=follower, following=author)

        with patch("posts.services.fan_out_notification_to_followers.delay") as mock_delay:
            with django_capture_on_commit_callbacks(execute=True):
                result = PostService.create_post(str(author.id), "hello followers")

        assert result["notifications_queued"] == 1
        mock_delay.assert_called_once()
        call_args = mock_delay.call_args[0]
        assert call_args[0] == str(author.id)
        assert call_args[2] == f"{author.username} posted new content"
        assert call_args[3] == 1


class TestDeletePost:
    def test_author_can_delete_own_post(self, author):
        post = Post.objects.create(author=author, content="delete me")

        result = PostService.delete_post(str(author.id), str(post.id))

        assert result is True
        assert not Post.objects.filter(id=post.id).exists()

    def test_non_author_cannot_delete_post(self, author, follower):
        post = Post.objects.create(author=author, content="not yours")

        with pytest.raises(ValueError, match="don't have permission"):
            PostService.delete_post(str(follower.id), str(post.id))

        assert Post.objects.filter(id=post.id).exists()

    def test_deleting_nonexistent_post_raises(self, author):
        with pytest.raises(ValueError):
            PostService.delete_post(str(author.id), "00000000-0000-0000-0000-000000000000")


class TestToggleLike:
    def test_liking_a_post_creates_like(self, author, follower):
        post = Post.objects.create(author=author, content="like this")

        result = PostService.toggle_like(str(follower.id), str(post.id))

        assert result == {"liked": True, "likes_count": 1}
        assert Like.objects.filter(user=follower, post=post).exists()

    def test_unliking_removes_the_like(self, author, follower):
        post = Post.objects.create(author=author, content="like this")
        Like.objects.create(user=follower, post=post)

        result = PostService.toggle_like(str(follower.id), str(post.id))

        assert result == {"liked": False, "likes_count": 0}
        assert not Like.objects.filter(user=follower, post=post).exists()

    def test_toggling_nonexistent_post_raises(self, follower):
        with pytest.raises(ValueError, match="Post not found"):
            PostService.toggle_like(str(follower.id), "00000000-0000-0000-0000-000000000000")

    def test_survives_integrity_error_race_on_get_or_create(self, author, follower):
        post = Post.objects.create(author=author, content="race condition")

      
        with patch(
            "posts.services.Like.objects.get_or_create",
            side_effect=IntegrityError("duplicate key value violates unique constraint"),
        ):
            Like.objects.create(user=follower, post=post)  # the "concurrent" row
            result = PostService.toggle_like(str(follower.id), str(post.id))

        assert result["liked"] is False

    def test_likes_count_reflects_multiple_likers(self, author, follower):
        post = Post.objects.create(author=author, content="popular post")
        other_liker = User.objects.create_user(
            username="other", email="other@test.com", password="pass12345"
        )
        Like.objects.create(user=other_liker, post=post)

        result = PostService.toggle_like(str(follower.id), str(post.id))

        assert result == {"liked": True, "likes_count": 2}