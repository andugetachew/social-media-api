from django.core.cache import cache
from django.http import HttpResponse
from django.test import RequestFactory, TestCase

from config.cache_utils import CacheService, cache_response


class TestCacheService(TestCase):
    def setUp(self):
        cache.clear()
        self.user_id = "1"
        self.post_id = "10"

    def test_get_key_generation(self):
        key = CacheService._get_key("user", "1", "page_1")
        self.assertEqual(key, "user:1:page_1")

    def test_hash_key_short(self):
        key = CacheService._hash_key("short_key")
        self.assertEqual(key, "short_key")

    def test_hash_key_long(self):
        long_key = "x" * 250
        hashed = CacheService._hash_key(long_key)
        self.assertEqual(len(hashed), 32)  # md5 hash length

    def test_set_and_get_user(self):
        data = {"id": 1, "name": "Test"}

        CacheService.set_user(self.user_id, data)
        result = CacheService.get_user(self.user_id)

        self.assertEqual(result, data)

    def test_invalidate_user(self):
        CacheService.set_user(self.user_id, {"name": "Test"})
        CacheService.invalidate_user(self.user_id)

        result = CacheService.get_user(self.user_id)
        self.assertIsNone(result)

    def test_set_and_get_post(self):
        data = {"id": self.post_id, "title": "Post"}

        CacheService.set_post(self.post_id, data)
        result = CacheService.get_post(self.post_id)

        self.assertEqual(result, data)

    def test_invalidate_post(self):
        CacheService.set_post(self.post_id, {"title": "Test"})
        CacheService.invalidate_post(self.post_id)

        result = CacheService.get_post(self.post_id)
        self.assertIsNone(result)

    def test_set_and_get_feed(self):
        data = [{"id": 1}, {"id": 2}]

        CacheService.set_user_feed(self.user_id, 1, data)
        result = CacheService.get_user_feed(self.user_id, 1)

        self.assertEqual(result, data)

    def test_invalidate_feed(self):
        CacheService.set_user_feed(self.user_id, 1, [{"id": 1}])
        CacheService.invalidate_user_feed(self.user_id)

        result = CacheService.get_user_feed(self.user_id, 1)
        self.assertIsNone(result)

    def test_set_and_get_comments(self):
        data = [{"comment": "hi"}]

        CacheService.set_post_comments(self.post_id, 1, data)
        result = CacheService.get_post_comments(self.post_id, 1)

        self.assertEqual(result, data)

    def test_invalidate_comments(self):
        CacheService.set_post_comments(self.post_id, 1, [{"c": 1}])
        CacheService.invalidate_post_comments(self.post_id)

        result = CacheService.get_post_comments(self.post_id, 1)
        self.assertIsNone(result)

  
    def test_set_and_get_notifications(self):
        data = [{"n": 1}]

        CacheService.set_user_notifications(self.user_id, 1, data)
        result = CacheService.get_user_notifications(self.user_id, 1)

        self.assertEqual(result, data)

    def test_invalidate_notifications(self):
        CacheService.set_user_notifications(self.user_id, 1, [{"n": 1}])
        CacheService.invalidate_user_notifications(self.user_id)

        result = CacheService.get_user_notifications(self.user_id, 1)
        self.assertIsNone(result)

    def test_clear_all_cache(self):
        CacheService.set_user(self.user_id, {"x": 1})
        CacheService.clear_all()

        result = CacheService.get_user(self.user_id)
        self.assertIsNone(result)



class TestCacheDecorator(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        cache.clear()

    def test_cache_response_decorator(self):
        @cache_response(timeout=300, key_prefix="test")
        def dummy_view(self, request):
            return HttpResponse("OK")

        request = self.factory.get("/test-url")

        response1 = dummy_view(self, request)
        response2 = dummy_view(self, request)

        self.assertEqual(response1.status_code, 200)
        self.assertEqual(response2.status_code, 200)