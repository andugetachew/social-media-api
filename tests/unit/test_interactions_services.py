from django.test import TestCase
from django.contrib.auth import get_user_model
from interactions.services import FollowService
from interactions.models import Follow

User = get_user_model()


class FollowServiceTests(TestCase):
    """Covers interactions/services.py lines 1-46"""

    def setUp(self):
        self.user1 = User.objects.create_user(
            email="svc1@test.com", username="svcuser1", password="pass"
        )
        self.user2 = User.objects.create_user(
            email="svc2@test.com", username="svcuser2", password="pass"
        )

    def test_follow_user_success(self):
        result = FollowService.follow_user(str(self.user1.id), str(self.user2.id))
        self.assertTrue(result["followed"])
        self.assertTrue(
            Follow.objects.filter(follower=self.user1, following=self.user2).exists()
        )

    def test_follow_self_raises_value_error(self):
        with self.assertRaises(ValueError):
            FollowService.follow_user(str(self.user1.id), str(self.user1.id))

    def test_follow_duplicate_raises_value_error(self):
        FollowService.follow_user(str(self.user1.id), str(self.user2.id))
        with self.assertRaises(ValueError):
            FollowService.follow_user(str(self.user1.id), str(self.user2.id))

    def test_unfollow_user_success(self):
        Follow.objects.create(follower=self.user1, following=self.user2)
        result = FollowService.unfollow_user(str(self.user1.id), str(self.user2.id))
        self.assertFalse(result["followed"])
        self.assertFalse(
            Follow.objects.filter(follower=self.user1, following=self.user2).exists()
        )

    def test_unfollow_not_following_raises_value_error(self):
        with self.assertRaises(ValueError):
            FollowService.unfollow_user(str(self.user1.id), str(self.user2.id))

    def test_get_follow_stats(self):
        Follow.objects.create(follower=self.user2, following=self.user1)
        Follow.objects.create(follower=self.user1, following=self.user2)
        stats = FollowService.get_follow_stats(str(self.user1.id))
        self.assertEqual(stats["followers_count"], 1)
        self.assertEqual(stats["following_count"], 1)

    def test_get_follow_stats_zero(self):
        stats = FollowService.get_follow_stats(str(self.user1.id))
        self.assertEqual(stats["followers_count"], 0)
        self.assertEqual(stats["following_count"], 0)