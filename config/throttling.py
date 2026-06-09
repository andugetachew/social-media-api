from rest_framework.throttling import SimpleRateThrottle


class RegisterThrottle(SimpleRateThrottle):
    """Limit registration attempts."""

    scope = "register"

    def get_cache_key(self, request, view):
        if request.user.is_authenticated:
            return None
        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),
        }

    def allow_request(self, request, view):
        if request.user.is_authenticated:
            return True
        return super().allow_request(request, view)


class LoginThrottle(SimpleRateThrottle):
    """Limit login attempts."""

    scope = "login"

    def get_cache_key(self, request, view):
        if request.user.is_authenticated:
            return None
        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),
        }


class PostCreateThrottle(SimpleRateThrottle):
    """Limit post creation."""

    scope = "post_create"

    def get_cache_key(self, request, view):
        if not request.user.is_authenticated:
            return None
        return self.cache_format % {"scope": self.scope, "ident": str(request.user.id)}


class LikeThrottle(SimpleRateThrottle):
    """Limit like/unlike actions."""

    scope = "like"

    def get_cache_key(self, request, view):
        if not request.user.is_authenticated:
            return None
        return self.cache_format % {"scope": self.scope, "ident": str(request.user.id)}


class FollowThrottle(SimpleRateThrottle):
    """Limit follow/unfollow actions."""

    scope = "follow"

    def get_cache_key(self, request, view):
        if not request.user.is_authenticated:
            return None
        return self.cache_format % {"scope": self.scope, "ident": str(request.user.id)}


class ChatMessageThrottle(SimpleRateThrottle):
    """Limit chat messages per minute."""

    scope = "chat_message"

    def get_cache_key(self, request, view):
        if not request.user.is_authenticated:
            return None
        return self.cache_format % {"scope": self.scope, "ident": str(request.user.id)}


class BurstRateThrottle(SimpleRateThrottle):
    """High rate limit for short burst."""

    scope = "burst"

    def get_cache_key(self, request, view):
        if not request.user.is_authenticated:
            return self.cache_format % {
                "scope": self.scope,
                "ident": self.get_ident(request),
            }
        return self.cache_format % {"scope": self.scope, "ident": str(request.user.id)}


class SustainedRateThrottle(SimpleRateThrottle):
    """Lower rate limit for sustained requests."""

    scope = "sustained"

    def get_cache_key(self, request, view):
        if not request.user.is_authenticated:
            return self.cache_format % {
                "scope": self.scope,
                "ident": self.get_ident(request),
            }
        return self.cache_format % {"scope": self.scope, "ident": str(request.user.id)}
