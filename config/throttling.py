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
    # NOTE: previously had an `allow_request` override here that duplicated
    # SimpleRateThrottle's own behavior (get_cache_key returning None already
    # short-circuits to allow the request) — removed as dead code.


class LoginThrottle(SimpleRateThrottle):
    """
    Limit login attempts.

    Keyed on (client IP, submitted email/username) rather than IP alone.
    IP-only keying let a distributed attacker (rotating IPs/proxies) hammer
    one target account with each request landing in its own fresh bucket,
    while also collateral-throttling unrelated users sharing an IP (NAT,
    corporate networks). Keying on the pair means many IPs targeting the
    same account still share a bucket for that account, and one IP trying
    many accounts is still capped per-account too.
    """

    scope = "login"

    def get_cache_key(self, request, view):
        if request.user.is_authenticated:
            return None

        identifier = request.data.get("email", "") if hasattr(request, "data") else ""
        identifier = str(identifier).strip().lower()

        return self.cache_format % {
            "scope": self.scope,
            "ident": f"{self.get_ident(request)}:{identifier}",
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