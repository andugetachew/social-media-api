"""
Integration tests for the throttles wired onto RegisterView and LoginView.

Fix note: the original version of this file used @override_settings as a
CLASS decorator on plain pytest classes. Django's override_settings only
supports class-level decoration on subclasses of django.test.SimpleTestCase
— applying it to a plain class raises ValueError at import time, which
aborts pytest's entire collection process (not just this file's tests),
causing every other test file to report 0% coverage since nothing ran.
Fixed by using pytest-django's `settings` fixture instead, applied inside
each test function rather than at the class level.
"""
import pytest
from django.core.cache import cache
from rest_framework.throttling import SimpleRateThrottle
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

REGISTER_URL = "/api/auth/register/"
LOGIN_URL = "/api/auth/login/"

TEST_THROTTLE_RATES = {
    "register": "3/min",
    "login": "3/min",
    "post_create": "50/hour",
    "like": "200/hour",
    "follow": "100/hour",
    "chat_message": "60/minute",
    "burst": "30/minute",
    "sustained": "1000/day",
}


@pytest.fixture(autouse=True)
def clear_throttle_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture(autouse=True)
def isolate_throttle_settings(monkeypatch):

    monkeypatch.setattr(SimpleRateThrottle, "THROTTLE_RATES", TEST_THROTTLE_RATES)


def _register_payload(suffix):
    return {
        "email": f"user{suffix}@test.com",
        "username": f"user{suffix}",
        "full_name": "Test User",
        "password": "SecurePass123",
        "password2": "SecurePass123",
    }


class TestRegisterThrottle:
    def test_allows_requests_up_to_the_limit(self, db, api_client):
        for i in range(3):
            response = api_client.post(REGISTER_URL, _register_payload(i), format="json")
            assert response.status_code != 429, f"request {i} was throttled too early"

    def test_blocks_once_limit_is_exceeded(self, db, api_client):
        for i in range(3):
            api_client.post(REGISTER_URL, _register_payload(i), format="json")

        response = api_client.post(REGISTER_URL, _register_payload("overflow"), format="json")
        assert response.status_code == 429

    def test_throttle_is_scoped_by_ip(self, db, api_client):
        for i in range(3):
            api_client.post(
                REGISTER_URL, _register_payload(i), format="json", REMOTE_ADDR="10.0.0.1"
            )
        blocked = api_client.post(
            REGISTER_URL, _register_payload("x"), format="json", REMOTE_ADDR="10.0.0.1"
        )
        assert blocked.status_code == 429

        other_ip_response = api_client.post(
            REGISTER_URL, _register_payload("y"), format="json", REMOTE_ADDR="10.0.0.2"
        )
        assert other_ip_response.status_code != 429


class TestLoginThrottle:
    @pytest.fixture(autouse=True)
    def existing_user(self, db):
        return User.objects.create_user(
            username="alice", email="alice@test.com", password="pass12345"
        )

    def test_allows_failed_attempts_up_to_the_limit(self, api_client):
        for i in range(3):
            response = api_client.post(
                LOGIN_URL, {"email": "alice@test.com", "password": "wrong-password"}, format="json"
            )
            assert response.status_code != 429, f"attempt {i} was throttled too early"

    def test_blocks_once_limit_is_exceeded(self, api_client):
        for _ in range(3):
            api_client.post(
                LOGIN_URL, {"email": "alice@test.com", "password": "wrong-password"}, format="json"
            )

        response = api_client.post(
            LOGIN_URL, {"email": "alice@test.com", "password": "wrong-password"}, format="json"
        )
        assert response.status_code == 429

    def test_distributed_attempts_against_same_account_use_per_ip_buckets(self, api_client):
        for ip in ("10.0.0.1", "10.0.0.2", "10.0.0.3"):
            response = api_client.post(
                LOGIN_URL,
                {"email": "alice@test.com", "password": "wrong-password"},
                format="json",
                REMOTE_ADDR=ip,
            )
            assert response.status_code != 429, f"IP {ip} was throttled on first attempt"

    def test_successful_login_still_counts_against_the_bucket(self, api_client):
        responses = []
        for _ in range(4):
            responses.append(
                api_client.post(
                    LOGIN_URL, {"email": "alice@test.com", "password": "pass12345"}, format="json"
                )
            )
        assert responses[-1].status_code == 429