from django.urls import reverse
from rest_framework import status
from posts.models import Post, Like
from tests.base import BaseTestCase


class PostCRUDTests(BaseTestCase):
    """Test Post Create, Read, Update, Delete operations"""

    def test_create_post(self):
        """Test creating a new post"""
        url = reverse("posts")
        data = {"content": "This is my test post"}
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Post.objects.count(), 1)
        self.assertEqual(response.data["content"], "This is my test post")

    def test_create_post_empty_content(self):
        """Test creating post with empty content (should fail)"""
        url = reverse("posts")
        data = {"content": ""}
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_post_max_length(self):
        """Test creating post with content exceeding 280 chars"""
        url = reverse("posts")
        data = {"content": "a" * 281}
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_user_posts(self):
        """Test retrieving user's own posts"""
        self.create_post(self.user1, "Post 1")
        self.create_post(self.user1, "Post 2")

        url = reverse("posts")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_update_own_post(self):
        """Test updating own post"""
        post = self.create_post(self.user1, "Original content")
        url = reverse("post-detail", args=[post.id])
        data = {"content": "Updated content"}
        response = self.client.put(url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        post.refresh_from_db()
        self.assertEqual(post.content, "Updated content")

    def test_update_others_post(self):
        """Test updating another user's post (should fail)"""
        post = self.create_post(self.user2, "User2 post")
        url = reverse("post-detail", args=[post.id])
        data = {"content": "Trying to update"}
        response = self.client.put(url, data)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_own_post(self):
        """Test deleting own post"""
        post = self.create_post(self.user1, "To delete")
        url = reverse("post-detail", args=[post.id])
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Post.objects.count(), 0)

    def test_delete_others_post(self):
        """Test deleting another user's post (should fail)"""
        post = self.create_post(self.user2, "User2 post")
        url = reverse("post-detail", args=[post.id])
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_single_post(self):
        """Test retrieving a single post"""
        post = self.create_post(self.user1, "Single post")
        url = reverse("post-detail", args=[post.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["content"], "Single post")

    def test_get_nonexistent_post(self):
        """Test retrieving non-existent post"""
        import uuid

        url = reverse("post-detail", args=[uuid.uuid4()])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class PostFeedTests(BaseTestCase):
    """Test post feed functionality"""

    def test_feed_shows_own_posts(self):
        """Test that user sees their own posts in feed"""
        self.create_post(self.user1, "My post")
        url = reverse("feed")
        response = self.client.get(url)

        self.assertEqual(len(response.data["results"]), 1)

    def test_feed_shows_followed_users_posts(self):
        """Test feed shows posts from followed users"""
        self.create_follow(self.user1, self.user2)
        self.create_post(self.user2, "User2 post")

        url = reverse("feed")
        response = self.client.get(url)

        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["content"], "User2 post")

    def test_feed_hides_unfollowed_posts(self):
        """Test feed does NOT show posts from unfollowed users"""
        self.create_post(self.user2, "Hidden post")
        self.create_post(self.user3, "Also hidden")

        url = reverse("feed")
        response = self.client.get(url)

        self.assertEqual(len(response.data["results"]), 0)

    def test_feed_pagination(self):
        """Test feed pagination"""
        for i in range(15):
            self.create_post(self.user1, f"Post {i}")

        url = reverse("feed")
        response = self.client.get(url + "?page=1&page_size=10")

        self.assertEqual(len(response.data["results"]), 10)
        self.assertIsNotNone(response.data["next"])
        self.assertIsNone(response.data["previous"])


class PostLikeTests(BaseTestCase):
    """Test like/unlike functionality"""

    def test_like_post(self):
        """Test liking a post"""
        post = self.create_post(self.user2, "Likeable post")
        url = reverse("like", args=[post.id])
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Like.objects.count(), 1)
        self.assertEqual(response.data["liked"], True)
        self.assertEqual(response.data["likes_count"], 1)

    def test_duplicate_like_prevention(self):
        """Test duplicate like prevention (idempotent)"""
        post = self.create_post(self.user2, "Post")
        url = reverse("like", args=[post.id])

        # First like
        response1 = self.client.post(url)
        # Second like (should unlike)
        response2 = self.client.post(url)

        self.assertEqual(response1.data["liked"], True)
        self.assertEqual(response2.data["liked"], False)
        self.assertEqual(Like.objects.count(), 0)

    def test_like_own_post(self):
        """Test liking own post"""
        post = self.create_post(self.user1, "My post")
        url = reverse("like", args=[post.id])
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Like.objects.count(), 1)

    def test_like_nonexistent_post(self):
        """Test liking non-existent post"""
        import uuid

        url = reverse("like", args=[uuid.uuid4()])
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_likes_count_updates_correctly(self):
        """Test likes count updates correctly with multiple likes"""
        post = self.create_post(self.user2, "Popular post")

        # User1 likes
        self.client.force_authenticate(user=self.user1)
        self.client.post(reverse("like", args=[post.id]))

        # User2 is author, can't like own? Actually they can
        self.client.force_authenticate(user=self.user2)
        self.client.post(reverse("like", args=[post.id]))

        # User3 likes
        self.client.force_authenticate(user=self.user3)
        self.client.post(reverse("like", args=[post.id]))

        post.refresh_from_db()
        self.assertEqual(post.likes.count(), 3)
