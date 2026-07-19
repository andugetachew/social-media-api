from rest_framework import permissions


class IsOwner(permissions.BasePermission):
    """
    Object-level ownership check. Reads are allowed for any authenticated
    user; only the owner can write. Requires pairing with IsAuthenticated
    (has_permission is left at the DRF default of True) since object-level
    checks alone don't cover unauthenticated requests to list endpoints.
    """

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True

        # Post owner check
        if hasattr(obj, "author"):
            return obj.author == request.user
        # Comment owner check (some models use `user` instead of `author`)
        if hasattr(obj, "user"):
            return obj.user == request.user
        # Removed: a redundant `author_id` fallback that was unreachable —
        # any model with an `author` FK already exposes `author_id`, so
        # that branch could never be hit by a real model instance.
        return False


class IsCommentOwner(permissions.BasePermission):
    """
    Same defensive attribute check as IsOwner — previously hardcoded
    `obj.author`, which raises AttributeError (surfacing as an unhandled
    500) instead of a clean 403 if Comment's owner field is actually named
    `user`. Made consistent with IsOwner's lookup and SAFE_METHODS bypass.
    """

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True

        if hasattr(obj, "author"):
            return obj.author == request.user
        if hasattr(obj, "user"):
            return obj.user == request.user
        return False


class IsAuthorOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        if hasattr(obj, "author"):
            return obj.author == request.user
        return False