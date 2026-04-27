from django.test import TestCase
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from posts.models import Post, Like
from interactions.models import Follow
from comments.models import Comment

User = get_user_model()


class EndToEndSocialTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user1 = User.objects.create_user(
            email="alice@test.com", username="alice", password="pass123"
        )
        self.user2 = User.objects.create_user(
            email="bob@test.com", username="bob", password="pass123"
        )

    def test_complete_social_flow(self):
        # 1. Alice creates a post
        self.client.force_authenticate(user=self.user1)
        post_response = self.client.post("/api/posts/", {"content": "Hello world!"})
        self.assertEqual(post_response.status_code, 201)
        post_id = post_response.data["id"]

        # 2. Bob follows Alice
        self.client.force_authenticate(user=self.user2)
        follow_response = self.client.post(f"/api/interactions/follow/{self.user1.id}/")
        self.assertEqual(follow_response.status_code, 201)
        self.assertTrue(
            Follow.objects.filter(follower=self.user2, following=self.user1).exists()
        )

        # 3. Bob likes Alice's post
        like_response = self.client.post(f"/api/posts/{post_id}/like/")
        self.assertEqual(like_response.status_code, 200)
        self.assertTrue(Like.objects.filter(user=self.user2, post_id=post_id).exists())

        # 4. Bob comments on Alice's post
        comment_response = self.client.post(
            f"/api/comments/post/{post_id}/", {"content": "Great post!"}
        )
        self.assertEqual(comment_response.status_code, 201)
        self.assertEqual(Comment.objects.count(), 1)

        # 5. Alice checks her feed (should see her own post)
        self.client.force_authenticate(user=self.user1)
        feed_response = self.client.get("/api/posts/feed/")
        self.assertEqual(len(feed_response.data["results"]), 1)
