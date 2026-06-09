from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from unittest.mock import MagicMock
from config.permissions import (
    IsOwner,
    IsAdminOrReadOnly,
    IsOwnerOrReadOnly,
)

User = get_user_model()


def make_request(method="GET", user=None):
    factory = RequestFactory()
    request = getattr(factory, method.lower())("/")
    request.user = user or MagicMock(is_authenticated=True, is_staff=False)
    return request


def make_view():
    return MagicMock()


class IsOwnerTests(TestCase):
    """Tests for IsOwner — checks author, user, owner attrs in that order"""

    def setUp(self):
        self.perm = IsOwner()
        self.user = MagicMock(is_authenticated=True)
        self.other = MagicMock(is_authenticated=True)

    def test_owner_via_author_attr_allowed(self):
        """Object with .author == request.user passes"""
        obj = MagicMock(spec=["author"])
        obj.author = self.user
        request = make_request(user=self.user)
        self.assertTrue(self.perm.has_object_permission(request, make_view(), obj))

    def test_non_owner_via_author_attr_denied(self):
        """Object with .author != request.user is denied"""
        obj = MagicMock(spec=["author"])
        obj.author = self.other
        request = make_request(user=self.user)
        self.assertFalse(self.perm.has_object_permission(request, make_view(), obj))

    def test_owner_via_user_attr_allowed(self):
        """Object with no .author but .user == request.user passes"""
        obj = MagicMock(spec=["user"])
        obj.user = self.user
        request = make_request(user=self.user)
        self.assertTrue(self.perm.has_object_permission(request, make_view(), obj))

    def test_non_owner_via_user_attr_denied(self):
        """Object with .user != request.user is denied"""
        obj = MagicMock(spec=["user"])
        obj.user = self.other
        request = make_request(user=self.user)
        self.assertFalse(self.perm.has_object_permission(request, make_view(), obj))

    def test_owner_via_owner_attr_allowed(self):
        """Object with no .author/.user but .owner == request.user passes"""
        obj = MagicMock(spec=["owner"])
        obj.owner = self.user
        request = make_request(user=self.user)
        self.assertTrue(self.perm.has_object_permission(request, make_view(), obj))

    def test_non_owner_via_owner_attr_denied(self):
        """Object with .owner != request.user is denied"""
        obj = MagicMock(spec=["owner"])
        obj.owner = self.other
        request = make_request(user=self.user)
        self.assertFalse(self.perm.has_object_permission(request, make_view(), obj))

    def test_object_with_no_recognized_attr_denied(self):
        """Object with none of author/user/owner falls through to False"""
        obj = MagicMock(spec=[])  # no recognised attrs
        request = make_request(user=self.user)
        self.assertFalse(self.perm.has_object_permission(request, make_view(), obj))

    def test_author_attr_takes_priority_over_user(self):
        """When both .author and .user exist, .author is checked first"""
        obj = MagicMock(spec=["author", "user"])
        obj.author = self.user    # correct owner via author
        obj.user = self.other     # would deny via user
        request = make_request(user=self.user)
        # Should pass because author matches
        self.assertTrue(self.perm.has_object_permission(request, make_view(), obj))


class IsAdminOrReadOnlyTests(TestCase):
    """Tests for IsAdminOrReadOnly"""

    def setUp(self):
        self.perm = IsAdminOrReadOnly()

    def test_safe_method_allowed_for_any_user(self):
        """GET is always allowed regardless of role"""
        user = MagicMock(is_authenticated=True, is_staff=False)
        for method in ("GET", "HEAD", "OPTIONS"):
            request = make_request(method=method, user=user)
            self.assertTrue(self.perm.has_permission(request, make_view()))

    def test_admin_can_write(self):
        """Staff user can use POST/PUT/DELETE"""
        admin = MagicMock(is_authenticated=True, is_staff=True)
        for method in ("POST", "PUT", "DELETE", "PATCH"):
            request = make_request(method=method, user=admin)
            self.assertTrue(self.perm.has_permission(request, make_view()))

    def test_non_admin_cannot_write(self):
        """Non-staff user is denied on POST/PUT/DELETE"""
        user = MagicMock(is_authenticated=True, is_staff=False)
        for method in ("POST", "PUT", "DELETE", "PATCH"):
            request = make_request(method=method, user=user)
            self.assertFalse(self.perm.has_permission(request, make_view()))


class IsOwnerOrReadOnlyTests(TestCase):
    """Tests for IsOwnerOrReadOnly"""

    def setUp(self):
        self.perm = IsOwnerOrReadOnly()
        self.user = MagicMock(is_authenticated=True)
        self.other = MagicMock(is_authenticated=True)

    def test_safe_method_always_allowed(self):
        """GET/HEAD/OPTIONS are allowed for any user regardless of ownership"""
        obj = MagicMock(spec=["author"])
        obj.author = self.other  # different owner
        request = make_request(method="GET", user=self.user)
        self.assertTrue(
            self.perm.has_object_permission(request, make_view(), obj)
        )

    def test_owner_can_write_via_author(self):
        """Owner (matching .author) can use PUT/DELETE"""
        obj = MagicMock(spec=["author"])
        obj.author = self.user
        for method in ("PUT", "DELETE", "PATCH"):
            request = make_request(method=method, user=self.user)
            self.assertTrue(
                self.perm.has_object_permission(request, make_view(), obj)
            )

    def test_non_owner_cannot_write_via_author(self):
        """Non-owner is denied PUT/DELETE when .author != request.user"""
        obj = MagicMock(spec=["author"])
        obj.author = self.other
        for method in ("PUT", "DELETE", "PATCH"):
            request = make_request(method=method, user=self.user)
            self.assertFalse(
                self.perm.has_object_permission(request, make_view(), obj)
            )

    def test_owner_via_user_attr_can_write(self):
        """Object with .user == request.user (no .author) can write"""
        obj = MagicMock(spec=["user"])
        obj.user = self.user
        request = make_request(method="PUT", user=self.user)
        self.assertTrue(
            self.perm.has_object_permission(request, make_view(), obj)
        )

    def test_non_owner_via_user_attr_cannot_write(self):
        """Object with .user != request.user is denied write"""
        obj = MagicMock(spec=["user"])
        obj.user = self.other
        request = make_request(method="DELETE", user=self.user)
        self.assertFalse(
            self.perm.has_object_permission(request, make_view(), obj)
        )

    def test_no_recognised_attr_write_denied(self):
        """Object with neither .author nor .user returns False for writes"""
        obj = MagicMock(spec=[])
        request = make_request(method="PUT", user=self.user)
        self.assertFalse(
            self.perm.has_object_permission(request, make_view(), obj)
        )