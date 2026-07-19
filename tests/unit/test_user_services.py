"""
Tests for accounts/services.py: UserService.login_user.

Covers the fixes made when this was found to have drifted from LoginView:
- supports login by username as well as email (previously email-only via
  authenticate(), which also silently failed unless USERNAME_FIELD=="email")
- raises the same generic "Invalid credentials" message for every rejection
  reason (previously distinguished "Account is disabled" from bad
  credentials, leaking account existence — the same enumeration issue
  fixed in ForgotPasswordView)
- rejects inactive accounts, matching LoginView's gating

If it turns out nothing in the codebase actually calls UserService.login_user,
this file is safe to delete along with services.py — these tests exist to
keep the two implementations from silently drifting apart again if it does
get wired in somewhere.
"""
import pytest
from django.contrib.auth import get_user_model

from accounts.services import UserService

User = get_user_model()


@pytest.fixture
def active_user(db):
    return User.objects.create_user(
        username="alice", email="alice@test.com", password="pass12345", is_active=True
    )


class TestUserServiceLogin:
    def test_login_with_email_succeeds(self, active_user):
        result = UserService.login_user("alice@test.com", "pass12345")

        assert "access" in result
        assert "refresh" in result
        assert result["user"]["email"] == "alice@test.com"

    def test_login_with_username_succeeds(self, active_user):
        result = UserService.login_user("alice", "pass12345")

        assert "access" in result
        assert result["user"]["username"] == "alice"

    def test_wrong_password_raises_generic_error(self, active_user):
        with pytest.raises(ValueError, match="Invalid credentials"):
            UserService.login_user("alice@test.com", "wrong-password")

    def test_unknown_email_raises_generic_error(self, db):
        with pytest.raises(ValueError, match="Invalid credentials"):
            UserService.login_user("nobody@test.com", "whatever")

    def test_unknown_username_raises_generic_error(self, db):
        with pytest.raises(ValueError, match="Invalid credentials"):
            UserService.login_user("nosuchuser", "whatever")

    def test_inactive_account_raises_generic_error_not_distinct_message(self, db):
        user = User.objects.create_user(
            username="bob", email="bob@test.com", password="pass12345"
        )
        user.is_active = False
        user.save()

        with pytest.raises(ValueError) as exc_info:
            UserService.login_user("bob@test.com", "pass12345")

        
        assert str(exc_info.value) == "Invalid credentials"

    def test_inactive_account_error_matches_wrong_password_error_verbatim(self, db):
        inactive_user = User.objects.create_user(
            username="carol", email="carol@test.com", password="pass12345"
        )
        inactive_user.is_active = False
        inactive_user.save()

        with pytest.raises(ValueError) as inactive_exc:
            UserService.login_user("carol@test.com", "pass12345")

        with pytest.raises(ValueError) as wrong_password_exc:
            UserService.login_user("alice-does-not-exist@test.com", "anything")

        assert str(inactive_exc.value) == str(wrong_password_exc.value)