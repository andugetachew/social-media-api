import time
import statistics
from django.test import TransactionTestCase  # ← changed
from django.urls import reverse
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from posts.models import Post
from interactions.models import Follow

User = get_user_model()


class PerformanceTestCase(TransactionTestCase):  # ← changed
    """Performance tests for critical API endpoints"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="perf@test.com", username="perfuser", password="testpass"
        )
        self.client.force_authenticate(user=self.user)

        for i in range(100):
            Post.objects.create(author=self.user, content=f"Post {i}")

        for i in range(50):
            other = User.objects.create_user(
                email=f"follow{i}@test.com", username=f"followuser{i}", password="pass"
            )
            Follow.objects.create(follower=self.user, following=other)

    def measure_response_time(self, func, iterations=10):
        """Measure average response time"""
        times = []
        for _ in range(iterations):
            start = time.time()
            func()
            times.append((time.time() - start) * 1000)  # ms
        return {
            "avg": statistics.mean(times),
            "min": min(times),
            "max": max(times),
            "p95": (
                statistics.quantiles(times, n=20)[18] if len(times) > 18 else max(times)
            ),
        }

    def test_feed_performance(self):
        """Feed endpoint should load under 200ms"""

        def call_feed():
            self.client.get(reverse("feed") + "?page=1&page_size=20")

        metrics = self.measure_response_time(call_feed)
        print(
            f"\n📊 Feed Performance: avg={metrics['avg']:.1f}ms, p95={metrics['p95']:.1f}ms"
        )
        self.assertLess(metrics["avg"], 200, f"Feed too slow: {metrics['avg']:.1f}ms")

    def test_create_post_performance(self):
        """Create post should complete under 150ms"""

        def call_create():
            self.client.post(reverse("posts"), {"content": "Performance test post"})

        metrics = self.measure_response_time(call_create)
        print(f"📊 Create Post: avg={metrics['avg']:.1f}ms, p95={metrics['p95']:.1f}ms")
        self.assertLess(metrics["avg"], 150)

    def test_like_performance(self):
        """Like endpoint should complete under 100ms"""
        post = Post.objects.first()

        def call_like():
            self.client.post(reverse("like", args=[post.id]))

        metrics = self.measure_response_time(call_like)
        print(f"📊 Like Post: avg={metrics['avg']:.1f}ms, p95={metrics['p95']:.1f}ms")
        self.assertLess(metrics["avg"], 100)

    def test_follow_performance(self):
        """Follow endpoint should complete under 100ms"""
        other_user = User.objects.create_user(
            email="other@test.com", username="other", password="pass"
        )

        def call_follow():
            self.client.post(reverse("follow", args=[other_user.id]))

        metrics = self.measure_response_time(call_follow)
        print(f"📊 Follow User: avg={metrics['avg']:.1f}ms, p95={metrics['p95']:.1f}ms")
        self.assertLess(metrics["avg"], 100)

    def test_comment_performance(self):
        """Comment endpoint should complete under 100ms"""
        post = Post.objects.first()

        def call_comment():
            self.client.post(
                reverse("comments", args=[post.id]), {"content": "Test comment"}
            )

        metrics = self.measure_response_time(call_comment)
        print(f"📊 Add Comment: avg={metrics['avg']:.1f}ms, p95={metrics['p95']:.1f}ms")
        self.assertLess(metrics["avg"], 100)

    def test_search_performance(self):
        """Search endpoint should load under 150ms"""

        def call_search():
            self.client.get(reverse("user-search") + "?search=perf")

        metrics = self.measure_response_time(call_search)
        print(
            f"📊 Search Users: avg={metrics['avg']:.1f}ms, p95={metrics['p95']:.1f}ms"
        )
        self.assertLess(metrics["avg"], 150)

    def test_concurrent_likes(self):
        """Simulate concurrent likes (basic concurrency test)"""
        post = Post.objects.first()
        users = []

        # Create 10 users
        for i in range(10):
            u = User.objects.create_user(
                email=f"user{i}@test.com", username=f"user{i}", password="pass"
            )
            users.append(u)

        import threading

        results = []

        def like_post(user):
            client = APIClient()
            client.force_authenticate(user=user)
            response = client.post(reverse("like", args=[post.id]))
            results.append(response.status_code)

        threads = [threading.Thread(target=like_post, args=(u,)) for u in users]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        success_count = sum(1 for r in results if r == 200)
        print(f"📊 Concurrent Likes: {success_count}/10 successful")
        self.assertGreaterEqual(success_count, 9)
