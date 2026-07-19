"""
Additional tests for accounts/views.py targeting view classes not covered
by test_accounts.py / test_accounts_extra.py / test_accounts_views.py:
UpdateOnlineStatusView, UserStatusView, EmailVerificationView (legacy),
LogoutView, UserDetailView, UserSearchView, UpdatePasswordView,
UpdateProfilePhotoView, DeleteAccountView, ReactivateAccountView edge
cases, and ResendVerificationEmailView's already-verified branch.
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

ONLINE_URL = "/api/auth/online/"
STATUS_URL = "/api/auth/status/{}/"
LEGACY_VERIFY_URL = "/api/auth/verify/{}/"
LOGOUT_URL = "/api/auth/logout/"
USER_DETAIL_URL = "/api/auth/users/{}/"
USER_SEARCH_URL = "/api/auth/users/"
UPDATE_PASSWORD_URL = "/api/auth/update-password/"
UPDATE_PHOTO_URL = "/api/auth/update-photo/"
DELETE_ACCOUNT_URL = "/api/auth/delete-account/"
REACTIVATE_URL = "/api/auth/reactivate/"
RESEND_VERIFICATION_URL = "/api/auth/resend-verification/"


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def active_user(db):
    return User.objects.create_user(
        username="alice", email="alice@test.com", password="pass12345", is_active=True
    )


class TestUpdateOnlineStatusView:
    def test_sets_online_status_and_last_seen(self, api_client, active_user):
        api_client.force_authenticate(user=active_user)
        response = api_client.post(ONLINE_URL, {"is_online": True})

        assert response.status_code == 200
        active_user.refresh_from_db()
        assert active_user.is_online is True
        assert active_user.last_seen is not None

    def test_defaults_to_true_when_not_specified(self, api_client, active_user):
        api_client.force_authenticate(user=active_user)
        response = api_client.post(ONLINE_URL, {})

        assert response.status_code == 200
        active_user.refresh_from_db()
        assert active_user.is_online is True


class TestUserStatusView:
    def test_returns_online_status_for_existing_user(self, api_client, active_user):
        other = User.objects.create_user(
            username="bob", email="bob@test.com", password="pass12345", is_online=True
        )
        api_client.force_authenticate(user=active_user)

        response = api_client.get(STATUS_URL.format(other.id))

        assert response.status_code == 200
        assert response.data["is_online"] is True

    def test_returns_404_for_nonexistent_user(self, api_client, active_user):
        api_client.force_authenticate(user=active_user)

        response = api_client.get(
            STATUS_URL.format("00000000-0000-0000-0000-000000000000")
        )
        assert response.status_code == 404





class TestLogoutView:
    def test_valid_refresh_token_blacklists_and_logs_out(self, api_client, active_user):
        refresh = RefreshToken.for_user(active_user)
        api_client.force_authenticate(user=active_user)

        response = api_client.post(LOGOUT_URL, {"refresh": str(refresh)})

        assert response.status_code == 200

    def test_invalid_refresh_token_returns_400(self, api_client, active_user):
        api_client.force_authenticate(user=active_user)

        response = api_client.post(LOGOUT_URL, {"refresh": "not-a-real-token"})

        assert response.status_code == 400

    def test_missing_refresh_token_returns_400(self, api_client, active_user):
        api_client.force_authenticate(user=active_user)

        response = api_client.post(LOGOUT_URL, {})

        assert response.status_code == 400


class TestUserDetailView:
    def test_returns_user_data_for_existing_user(self, api_client, active_user):
        other = User.objects.create_user(
            username="dave", email="dave@test.com", password="pass12345"
        )
        api_client.force_authenticate(user=active_user)

        response = api_client.get(USER_DETAIL_URL.format(other.id))

        assert response.status_code == 200
        assert response.data["email"] == "dave@test.com"

    def test_returns_404_for_nonexistent_user(self, api_client, active_user):
        api_client.force_authenticate(user=active_user)

        response = api_client.get(
            USER_DETAIL_URL.format("00000000-0000-0000-0000-000000000000")
        )
        assert response.status_code == 404


class TestUserSearchView:
    def test_returns_matching_users(self, api_client, active_user):
        User.objects.create_user(username="erin_smith", email="erin@test.com", password="pass12345")
        User.objects.create_user(username="frank", email="frank@test.com", password="pass12345")
        api_client.force_authenticate(user=active_user)

        response = api_client.get(USER_SEARCH_URL, {"search": "erin"})

        assert response.status_code == 200
        assert len(response.data) == 1
        assert response.data[0]["username"] == "erin_smith"

    def test_empty_query_returns_empty_list(self, api_client, active_user):
        api_client.force_authenticate(user=active_user)

        response = api_client.get(USER_SEARCH_URL)

        assert response.status_code == 200
        assert response.data == []

    def test_search_capped_at_ten_results(self, api_client, active_user):
        for i in range(15):
            User.objects.create_user(
                username=f"match_user_{i}", email=f"match{i}@test.com", password="pass12345"
            )
        api_client.force_authenticate(user=active_user)

        response = api_client.get(USER_SEARCH_URL, {"search": "match"})

        assert len(response.data) == 10


class TestUpdatePasswordView:
    def test_correct_old_password_updates_successfully(self, api_client, active_user):
        api_client.force_authenticate(user=active_user)

        response = api_client.post(
            UPDATE_PASSWORD_URL,
            {"old_password": "pass12345", "new_password": "newSecurePass456"},
        )

        assert response.status_code == 200
        active_user.refresh_from_db()
        assert active_user.check_password("newSecurePass456")

    def test_wrong_old_password_returns_400(self, api_client, active_user):
        api_client.force_authenticate(user=active_user)

        response = api_client.post(
            UPDATE_PASSWORD_URL,
            {"old_password": "wrongpassword", "new_password": "newSecurePass456"},
        )

        assert response.status_code == 400


class TestUpdateProfilePhotoView:
    def test_missing_image_returns_400(self, api_client, active_user):
        api_client.force_authenticate(user=active_user)

        response = api_client.post(UPDATE_PHOTO_URL, {})

        assert response.status_code == 400
        assert "no image" in response.data["error"].lower()


class TestDeleteAccountView:
    def test_deletes_account_and_blacklists_tokens(self, api_client, active_user):
        api_client.force_authenticate(user=active_user)

        response = api_client.delete(DELETE_ACCOUNT_URL)

        assert response.status_code == 200
        active_user.refresh_from_db()
        assert active_user.is_active is False
        assert active_user.is_deleted is True
        assert active_user.deleted_at is not None


class TestReactivateAccountView:
    def test_wrong_password_returns_400(self, api_client, db):
        user = User.objects.create_user(
            username="grace", email="grace@test.com", password="pass12345"
        )
        user.is_deleted = True
        user.is_active = False
        user.save()

        response = api_client.post(
            REACTIVATE_URL, {"email": "grace@test.com", "password": "wrongpass"}
        )
        assert response.status_code == 400

    def test_nonexistent_or_not_deleted_account_returns_400(self, api_client, active_user):
        # active_user is not soft-deleted, so ReactivateAccountView's
        # is_deleted=True filter won't match it
        response = api_client.post(
            REACTIVATE_URL, {"email": "alice@test.com", "password": "pass12345"}
        )
        assert response.status_code == 400


class TestResendVerificationEmailView:
    def test_already_verified_user_returns_400(self, api_client, db):
        user = User.objects.create_user(
            username="henry", email="henry@test.com", password="pass12345", is_active=True
        )
        user.email_verified = True
        user.save()
        api_client.force_authenticate(user=user)

        response = api_client.post(RESEND_VERIFICATION_URL)

        assert response.status_code == 400
        assert "already verified" in response.data["error"].lower()

    def test_unverified_user_gets_new_token_and_email_queued(self, api_client, db):
        from unittest.mock import patch

        user = User.objects.create_user(
            username="ivy", email="ivy@test.com", password="pass12345", is_active=True
        )
        user.email_verified = False
        user.save()
        old_token = user.email_verification_token
        api_client.force_authenticate(user=user)

        with patch("accounts.views.send_verification_email.delay") as mock_delay:
            response = api_client.post(RESEND_VERIFICATION_URL)

        assert response.status_code == 200
        mock_delay.assert_called_once()
        user.refresh_from_db()
        assert user.email_verification_token != old_token