from rest_framework import permissions


class IsOwner(permissions.BasePermission):
    """Allow access only to the owner of the object."""

    def has_object_permission(self, request, view, obj):

        if hasattr(obj, "author"):
            return obj.author == request.user

        if hasattr(obj, "user"):
            return obj.user == request.user

        if hasattr(obj, "owner"):
            return obj.owner == request.user
        return False


class IsAdminOrReadOnly(permissions.BasePermission):
    """Admins can do anything, others can only read."""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_staff


class IsOwnerOrReadOnly(permissions.BasePermission):
    """Owners can edit/delete, others can only read."""

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True

        if hasattr(obj, "author"):
            return obj.author == request.user
        if hasattr(obj, "user"):
            return obj.user == request.user
        return False


class IsEmployer(permissions.BasePermission):
    """Job Board: Only employers can post jobs."""

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and getattr(request.user, "role", None) == "employer"
        )


class IsCandidate(permissions.BasePermission):
    """Job Board: Only candidates can apply to jobs."""

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and getattr(request.user, "role", None) == "candidate"
        )
