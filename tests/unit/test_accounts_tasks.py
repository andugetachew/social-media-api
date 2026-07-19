"""
Tests for core/permissions.py.

Permission classes only need obj.author / obj.user to exist for the
has_object_permission logic, so these tests use lightweight fake request/
view/object doubles instead of real Post/Comment models — keeps the tests
fast and decoupled from model schema, and makes the field-name fallback
behavior explicit regardless of what the real models are named.
"""
from types import SimpleNamespace

import pytest

from core.permissions import IsAuthorOrReadOnly, IsCommentOwner, IsOwner


def make_request(user, method="GET"):
    return SimpleNamespace(user=user, method=method)


@pytest.fixture
def owner_user():
    return SimpleNamespace(id=1, is_authenticated=True)


@pytest.fixture
def other_user():
    return SimpleNamespace(id=2, is_authenticated=True)


class TestIsOwner:
    def test_safe_method_allowed_for_non_owner(self, owner_user, other_user):
        obj = SimpleNamespace(author=owner_user)
        request = make_request(other_user, method="GET")

        assert IsOwner().has_object_permission(request, None, obj) is True

    def test_unsafe_method_denied_for_non_owner(self, owner_user, other_user):
        obj = SimpleNamespace(author=owner_user)
        request = make_request(other_user, method="DELETE")

        assert IsOwner().has_object_permission(request, None, obj) is False

    def test_unsafe_method_allowed_for_owner_via_author_field(self, owner_user):
        obj = SimpleNamespace(author=owner_user)
        request = make_request(owner_user, method="PATCH")

        assert IsOwner().has_object_permission(request, None, obj) is True

    def test_unsafe_method_allowed_for_owner_via_user_field_fallback(self, owner_user):
        # object has no `author`, only `user` — exercises the fallback branch
        obj = SimpleNamespace(user=owner_user)
        request = make_request(owner_user, method="PATCH")

        assert IsOwner().has_object_permission(request, None, obj) is True

    def test_unsafe_method_denied_when_object_has_neither_field(self, owner_user):
        obj = SimpleNamespace(irrelevant_field="x")
        request = make_request(owner_user, method="DELETE")

        assert IsOwner().has_object_permission(request, None, obj) is False


class TestIsCommentOwner:
    def test_safe_method_allowed_for_non_owner(self, owner_user, other_user):
        obj = SimpleNamespace(author=owner_user)
        request = make_request(other_user, method="GET")

        assert IsCommentOwner().has_object_permission(request, None, obj) is True

    def test_unsafe_method_allowed_for_owner_via_author_field(self, owner_user):
        obj = SimpleNamespace(author=owner_user)
        request = make_request(owner_user, method="DELETE")

        assert IsCommentOwner().has_object_permission(request, None, obj) is True

    def test_does_not_crash_when_owner_field_is_user_not_author(self, owner_user):
        # regression test: previously hardcoded obj.author with no fallback,
        # which raised AttributeError for a comment model using `user`.
        obj = SimpleNamespace(user=owner_user)
        request = make_request(owner_user, method="DELETE")

        assert IsCommentOwner().has_object_permission(request, None, obj) is True

    def test_unsafe_method_denied_for_non_owner_via_user_field(self, owner_user, other_user):
        obj = SimpleNamespace(user=owner_user)
        request = make_request(other_user, method="DELETE")

        assert IsCommentOwner().has_object_permission(request, None, obj) is False


class TestIsAuthorOrReadOnly:
    def test_safe_method_allowed_for_anyone(self, owner_user, other_user):
        obj = SimpleNamespace(author=owner_user)
        request = make_request(other_user, method="GET")

        assert IsAuthorOrReadOnly().has_object_permission(request, None, obj) is True

    def test_unsafe_method_allowed_for_author(self, owner_user):
        obj = SimpleNamespace(author=owner_user)
        request = make_request(owner_user, method="PUT")

        assert IsAuthorOrReadOnly().has_object_permission(request, None, obj) is True

    def test_unsafe_method_denied_for_non_author(self, owner_user, other_user):
        obj = SimpleNamespace(author=owner_user)
        request = make_request(other_user, method="PUT")

        assert IsAuthorOrReadOnly().has_object_permission(request, None, obj) is False

    def test_unsafe_method_denied_when_object_has_no_author_field(self, owner_user):
        obj = SimpleNamespace(irrelevant_field="x")
        request = make_request(owner_user, method="PUT")

        assert IsAuthorOrReadOnly().has_object_permission(request, None, obj) is False