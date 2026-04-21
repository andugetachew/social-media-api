from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.views import View


class IsOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        # Post owner check
        if hasattr(obj, "author"):
            return obj.author == request.user
        # Comment owner check
        if hasattr(obj, "user"):
            return obj.user == request.user
        if hasattr(obj, "author_id"):
            return str(obj.author_id) == str(request.user.id)
        return False


class IsCommentOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.author == request.user


class IsAuthorOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        if hasattr(obj, "author"):
            return obj.author == request.user
        return False
