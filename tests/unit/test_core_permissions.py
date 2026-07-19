from rest_framework import permissions


class IsOwner(permissions.BasePermission):
    """
    Strict owner-only access — including reads. Mirrors
    config.permissions.IsOwner's intended semantics (confirmed by its own
    test suite: a non-owner GET is denied, not just non-owner writes). Use
    this for resources that shouldn't be visible to anyone but the owner.
    For public-read/owner-write resources, use IsAuthorOrReadOnly instead.

    An earlier revision of this file added a SAFE_METHODS bypass here,
    which was a mistake — it silently converted this into a duplicate of
    IsAuthorOrReadOnly instead of preserving its strict-owner behavior.
    Reverted.
    """

    def has_object_permission(self, request, view, obj):
        if hasattr(obj, "author"):
            return obj.author == request.user
        if hasattr(obj, "user"):
            return obj.user == request.user
        # Removed: a redundant `author_id` fallback that was unreachable —
        # any model with an `author` FK already exposes `author_id`, so
        # that branch could never be hit by a real model instance.
        return False


class IsCommentOwner(permissions.BasePermission):
    """
    Strict owner-only access for comments, same semantics as IsOwner above
    (no SAFE_METHODS bypass — that reversion applies here too).

    Previously hardcoded `obj.author` with no fallback, which raises
    AttributeError (surfacing as an unhandled 500) instead of a clean 403
    if a Comment's owner field is actually named `user`. That part of the
    fix is kept — only the SAFE_METHODS change was reverted.
    """

    def has_object_permission(self, request, view, obj):
        if hasattr(obj, "author"):
            return obj.author == request.user
        if hasattr(obj, "user"):
            return obj.user == request.user
        return False


class IsAuthorOrReadOnly(permissions.BasePermission):
    """
    Public read, owner-only write. This is the read-bypass counterpart to
    IsOwner/IsCommentOwner above — already correct as originally written,
    unchanged here.
    """

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        if hasattr(obj, "author"):
            return obj.author == request.user
        return False