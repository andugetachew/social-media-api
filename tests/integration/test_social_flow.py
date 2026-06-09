from django.urls import reverse
from rest_framework import status
from posts.models import Post, Like
from interactions.models import Follow
from comments.models import Comment
from notify.models import Notification
from tests.base import BaseTestCase
from notify.tasks import create_like_notification


class SocialFlowIntegrationTests(BaseTestCase):
    """End-to-end social interaction tests"""

    def test_complete_social_flow(self):
        """Test complete user interaction flow"""

        # 1. User1 creates a post
        self.authenticate(self.user1)
        post_url = reverse("posts")
        post_response = self.client.post(post_url, {"content": "Hello world!"})
        self.assertEqual(post_response.status_code, status.HTTP_201_CREATED)
        post_id = post_response.data["id"]

        # 2. User2 follows User1
        self.authenticate(self.user2)
        follow_url = reverse("follow", args=[self.user1.id])
        follow_response = self.client.post(follow_url)
        self.assertEqual(follow_response.status_code, status.HTTP_201_CREATED)

        # 3. User2 likes User1's post
        like_url = reverse("like", args=[post_id])
        like_response = self.client.post(like_url)
        self.assertEqual(like_response.status_code, status.HTTP_200_OK)
        self.assertTrue(Like.objects.filter(user=self.user2, post_id=post_id).exists())

        # 4. User2 comments on the post
        comment_url = reverse("comments", args=[post_id])
        comment_response = self.client.post(comment_url, {"content": "Great post!"})
        self.assertEqual(comment_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Comment.objects.count(), 1)

        # 5. User2 creates their own post
        user2_post_response = self.client.post(post_url, {"content": "My first post"})
        self.assertEqual(user2_post_response.status_code, status.HTTP_201_CREATED)

        # 6. User1 checks their feed
        self.authenticate(self.user1)
        feed_url = reverse("feed")
        feed_response = self.client.get(feed_url)
        self.assertEqual(feed_response.status_code, status.HTTP_200_OK)
        # Feed should show User1's own post and User2's post (since User1 follows User2? No, User2 follows User1)
        # Actually User1 doesn't follow anyone yet, so only own post appears
        self.assertEqual(len(feed_response.data["results"]), 1)

        # 7. User1 follows User2
        follow_url = reverse("follow", args=[self.user2.id])
        self.client.post(follow_url)

        # 8. User1 checks feed again – should see User2's post now
        feed_response = self.client.get(feed_url)
        self.assertEqual(len(feed_response.data["results"]), 2)

        # 9. Check notifications
        notif_url = reverse("notifications")
        notif_response = self.client.get(notif_url)
        # User1 should have notifications: User2 liked their post, User2 followed them? Actually User2 followed User1
        self.assertGreaterEqual(len(notif_response.data), 1)
