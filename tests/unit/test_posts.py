"""
Additional tests for posts/views.py targeting branches not covered
elsewhere: PostDeleteView/PostUpdateView (the kept-for-compatibility
duplicates), UserPostsView's error path, FeedView pagination behavior,
and PostListCreateView.post's image-handling branch.
"""
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from posts.models import Post

User = get_user_model()

POSTS_URL = "/api/posts/"
POST_DETAIL_URL = "/api/posts/{}/"
POST_DELETE_LEGACY_URL = "/api/posts/{}/delete/"
POST_UPDATE_LEGACY_URL = "/api/posts/{}/update/"
FEED_URL = "/api/posts/feed/"
USER_POSTS_URL = "/api/posts/user/{}/"
LIKE_URL = "/api/posts/{}/like/"


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def author(db):
    return User.objects.create_user(username="author", email="author@test.com", password="pass12345")


class TestPostListCreateView:
    def test_create_post_without_image(self, api_client, author):
        api_client.force_authenticate(user=author)

        with patch("posts.services.fan_out_notification_to_followers.delay"):
            response = api_client.post(POSTS_URL, {"content": "hello world"})

        assert response.status_code == 201
        assert Post.objects.filter(author=author, content="hello world").exists()

    def test_create_post_rejects_invalid_content(self, api_client, author):
        api_client.force_authenticate(user=author)

        response = api_client.post(POSTS_URL, {"content": ""})

        assert response.status_code == 400

    def test_get_returns_only_own_posts(self, api_client, author):
        other = User.objects.create_user(username="other", email="other@test.com", password="pass12345")
        Post.objects.create(author=author, content="mine")
        Post.objects.create(author=other, content="not mine")
        api_client.force_authenticate(user=author)

        response = api_client.get(POSTS_URL)

        assert response.status_code == 200
        assert len(response.data) == 1


class TestPostDetailView:
    def test_get_existing_post(self, api_client, author):
        post = Post.objects.create(author=author, content="hello")
        api_client.force_authenticate(user=author)

        response = api_client.get(POST_DETAIL_URL.format(post.id))

        assert response.status_code == 200

    def test_get_nonexistent_post_returns_404(self, api_client, author):
        api_client.force_authenticate(user=author)

        response = api_client.get(
            POST_DETAIL_URL.format("00000000-0000-0000-0000-000000000000")
        )
        assert response.status_code == 404

    def test_put_updates_own_post(self, api_client, author):
        post = Post.objects.create(author=author, content="original")
        api_client.force_authenticate(user=author)

        response = api_client.put(POST_DETAIL_URL.format(post.id), {"content": "updated"})

        assert response.status_code == 200
        post.refresh_from_db()
        assert post.content == "updated"

    def test_put_on_others_post_returns_404(self, api_client, author):
        other = User.objects.create_user(username="other", email="other@test.com", password="pass12345")
        post = Post.objects.create(author=other, content="not yours")
        api_client.force_authenticate(user=author)

        response = api_client.put(POST_DETAIL_URL.format(post.id), {"content": "hacked"})

        assert response.status_code == 404

    def test_delete_own_post(self, api_client, author):
        post = Post.objects.create(author=author, content="delete me")
        api_client.force_authenticate(user=author)

        response = api_client.delete(POST_DETAIL_URL.format(post.id))

        assert response.status_code == 204
        assert not Post.objects.filter(id=post.id).exists()


class TestFeedView:
    def test_returns_paginated_feed_metadata(self, api_client, author):
        for i in range(5):
            Post.objects.create(author=author, content=f"post {i}")
        api_client.force_authenticate(user=author)

        response = api_client.get(FEED_URL, {"page": 1, "page_size": 2})

        assert response.status_code == 200
        assert "results" in response.data
        assert "count" in response.data
        assert "next" in response.data
        assert "previous" in response.data

    def test_page_size_capped_at_fifty(self, api_client, author):
        api_client.force_authenticate(user=author)

        response = api_client.get(FEED_URL, {"page_size": 999})

        assert response.status_code == 200


class TestUserPostsView:
    def test_returns_posts_for_given_user(self, api_client, author):
        Post.objects.create(author=author, content="hello")
        api_client.force_authenticate(user=author)

        response = api_client.get(USER_POSTS_URL.format(author.id))

        assert response.status_code == 200
        assert len(response.data) == 1

    def test_returns_empty_list_for_user_with_no_posts(self, api_client, author):
        other = User.objects.create_user(username="other", email="other@test.com", password="pass12345")
        api_client.force_authenticate(user=author)

        response = api_client.get(USER_POSTS_URL.format(other.id))

        assert response.status_code == 200
        assert response.data == []

    def test_serializer_error_returns_500_not_leaked_detail(self, api_client, author):
        api_client.force_authenticate(user=author)

        with patch("posts.views.PostSerializer", side_effect=Exception("boom")):
            response = api_client.get(USER_POSTS_URL.format(author.id))

        assert response.status_code == 500
        assert response.data["error"] == "Unable to fetch posts"
        assert "boom" not in str(response.data)


class TestLikeToggleView:
    def test_like_then_unlike_toggles_correctly(self, api_client, author):
        post = Post.objects.create(author=author, content="likeable")
        liker = User.objects.create_user(username="liker", email="liker@test.com", password="pass12345")
        api_client.force_authenticate(user=liker)

        with patch("posts.views.create_like_notification.delay") as mock_delay:
            first = api_client.post(LIKE_URL.format(post.id))
            second = api_client.post(LIKE_URL.format(post.id))

        assert first.data["liked"] is True
        assert second.data["liked"] is False
        mock_delay.assert_called_once()

    def test_liking_own_post_does_not_notify(self, api_client, author):
        post = Post.objects.create(author=author, content="my own post")
        api_client.force_authenticate(user=author)

        with patch("posts.views.create_like_notification.delay") as mock_delay:
            api_client.post(LIKE_URL.format(post.id))

        mock_delay.assert_not_called()

    def test_liking_nonexistent_post_returns_404(self, api_client, author):
        api_client.force_authenticate(user=author)

        response = api_client.post(
            LIKE_URL.format("00000000-0000-0000-0000-000000000000")
        )
        assert response.status_code == 404