from django.core.cache import cache
from functools import wraps
import hashlib
import json
from typing import Any, Optional, Callable


class CacheService:
    """Centralized cache service for all models"""

    # Cache key prefixes
    USER_PREFIX = "user"
    POST_PREFIX = "post"
    FEED_PREFIX = "feed"
    COMMENT_PREFIX = "comment"
    NOTIFICATION_PREFIX = "notification"

    SHORT_TTL = 60
    MEDIUM_TTL = 300
    LONG_TTL = 3600
    DAY_TTL = 86400

    @classmethod
    def _get_key(cls, prefix: str, identifier: str, suffix: str = "") -> str:
        """Generate cache key"""
        key = f"{prefix}:{identifier}"
        if suffix:
            key += f":{suffix}"
        return key

    @classmethod
    def _hash_key(cls, key: str) -> str:
        """Hash long keys"""
        if len(key) > 200:
            return hashlib.md5(key.encode()).hexdigest()
        return key

    @classmethod
    def get_user(cls, user_id: str) -> Optional[dict]:
        """Get cached user data"""
        key = cls._get_key(cls.USER_PREFIX, user_id)
        return cache.get(key)

    @classmethod
    def set_user(cls, user_id: str, data: dict, ttl: int = MEDIUM_TTL):
        """Cache user data"""
        key = cls._get_key(cls.USER_PREFIX, user_id)
        cache.set(key, data, ttl)

    @classmethod
    def invalidate_user(cls, user_id: str):
        """Invalidate user cache"""
        key = cls._get_key(cls.USER_PREFIX, user_id)
        cache.delete(key)
        cls.invalidate_user_feed(user_id)

    @classmethod
    def get_user_feed(cls, user_id: str, page: int = 1) -> Optional[list]:
        """Get cached user feed"""
        key = cls._get_key(cls.FEED_PREFIX, user_id, f"page_{page}")
        return cache.get(key)

    @classmethod
    def set_user_feed(cls, user_id: str, page: int, data: list, ttl: int = SHORT_TTL):
        """Cache user feed"""
        key = cls._get_key(cls.FEED_PREFIX, user_id, f"page_{page}")
        cache.set(key, data, ttl)

    @classmethod
    def invalidate_user_feed(cls, user_id: str):
        """Invalidate all feed pages for user"""
        pattern = f"{cls.FEED_PREFIX}:{user_id}:*"
        cls._delete_pattern(pattern)

    @classmethod
    def get_post(cls, post_id: str) -> Optional[dict]:
        """Get cached post"""
        key = cls._get_key(cls.POST_PREFIX, post_id)
        return cache.get(key)

    @classmethod
    def set_post(cls, post_id: str, data: dict, ttl: int = MEDIUM_TTL):
        """Cache post data"""
        key = cls._get_key(cls.POST_PREFIX, post_id)
        cache.set(key, data, ttl)

    @classmethod
    def invalidate_post(cls, post_id: str):
        """Invalidate post cache"""
        key = cls._get_key(cls.POST_PREFIX, post_id)
        cache.delete(key)

    @classmethod
    def get_post_comments(cls, post_id: str, page: int = 1) -> Optional[list]:
        """Get cached comments for a post"""
        key = cls._get_key(cls.COMMENT_PREFIX, post_id, f"page_{page}")
        return cache.get(key)

    @classmethod
    def set_post_comments(
        cls, post_id: str, page: int, data: list, ttl: int = SHORT_TTL
    ):
        """Cache comments for a post"""
        key = cls._get_key(cls.COMMENT_PREFIX, post_id, f"page_{page}")
        cache.set(key, data, ttl)

    @classmethod
    def invalidate_post_comments(cls, post_id: str):
        """Invalidate all comments cache for a post"""
        pattern = f"{cls.COMMENT_PREFIX}:{post_id}:*"
        cls._delete_pattern(pattern)

    @classmethod
    def get_user_notifications(cls, user_id: str, page: int = 1) -> Optional[list]:
        """Get cached notifications"""
        key = cls._get_key(cls.NOTIFICATION_PREFIX, user_id, f"page_{page}")
        return cache.get(key)

    @classmethod
    def set_user_notifications(
        cls, user_id: str, page: int, data: list, ttl: int = SHORT_TTL
    ):
        """Cache notifications"""
        key = cls._get_key(cls.NOTIFICATION_PREFIX, user_id, f"page_{page}")
        cache.set(key, data, ttl)

    @classmethod
    def invalidate_user_notifications(cls, user_id: str):
        """Invalidate notifications cache"""
        pattern = f"{cls.NOTIFICATION_PREFIX}:{user_id}:*"
        cls._delete_pattern(pattern)

    # ========== Helper Methods ==========

    @classmethod
    def _delete_pattern(cls, pattern: str):
        """Delete multiple cache keys matching pattern"""
        # Note: This requires django-redis
        try:
            from django.core.cache import caches

            redis_cache = caches["default"]
            keys = redis_cache.keys(pattern)
            if keys:
                redis_cache.delete_many(keys)
        except Exception:
            pass

    @classmethod
    def clear_all(cls):
        """Clear entire cache (use carefully)"""
        cache.clear()


def cache_response(
    timeout: int = 300, key_prefix: str = "", user_specific: bool = False
):
    """Decorator to cache API responses"""

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(self, request, *args, **kwargs):

            key_parts = [key_prefix or view_func.__name__]

            if user_specific and request.user.is_authenticated:
                key_parts.append(str(request.user.id))

            key_parts.append(request.path)
            key_parts.append(request.GET.urlencode())

            cache_key = hashlib.md5(":".join(key_parts).encode()).hexdigest()

            cached_response = cache.get(cache_key)
            if cached_response:
                return cached_response

            response = view_func(self, request, *args, **kwargs)

            if response.status_code == 200:
                cache.set(cache_key, response, timeout)

            return response

        return wrapper

    return decorator


def invalidate_on_post_save(sender, instance, **kwargs):
    """Signal handler to invalidate cache when post is saved"""
    CacheService.invalidate_post(str(instance.id))
    CacheService.invalidate_user_feed(str(instance.author_id))


def invalidate_on_comment_save(sender, instance, **kwargs):
    """Signal handler to invalidate cache when comment is saved"""
    CacheService.invalidate_post_comments(str(instance.post_id))


def invalidate_on_follow_save(sender, instance, **kwargs):
    """Signal handler to invalidate cache when follow is saved"""
    CacheService.invalidate_user_feed(str(instance.follower_id))
    CacheService.invalidate_user(str(instance.following_id))
