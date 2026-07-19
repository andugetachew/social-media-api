"""
Tests for core/exceptions.py: custom_exception_handler.

Covers:
- non-dict response.data (list-shaped, e.g. from Throttled) no longer
  crashes the handler itself
- every status code the API actually returns gets a "message" key,
  including 429 (relevant given the throttling work earlier this session)
- original DRF-provided detail (field errors etc.) is preserved, not
  discarded, alongside the added "message"
"""
import pytest
from rest_framework.exceptions import NotAuthenticated, PermissionDenied, Throttled, ValidationError
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView

from core.exceptions import custom_exception_handler


def make_context():
    factory = APIRequestFactory()
    request = factory.get("/")
    return {"request": request, "view": APIView()}


class TestCustomExceptionHandler:
    def test_validation_error_dict_shape_preserved_alongside_message(self):
        exc = ValidationError({"email": ["This field is required."]})
        response = custom_exception_handler(exc, make_context())

        assert response.status_code == 400
        assert response.data["email"] == ["This field is required."]
        assert response.data["message"] == "Bad request. Please check your input."
        assert response.data["error"] is True
        assert response.data["status_code"] == 400

    def test_list_shaped_response_data_does_not_crash(self):
        # ValidationError with a plain list of non-field errors produces
        # list-shaped response.data in some DRF versions/configurations —
        # this previously raised TypeError when the handler tried
        # response.data["status_code"] = ... on a list.
        exc = ValidationError(["Non-field error one", "Non-field error two"])
        response = custom_exception_handler(exc, make_context())

        assert response.status_code == 400
        assert isinstance(response.data, dict)
        assert response.data["message"] == "Bad request. Please check your input."

    def test_throttled_exception_gets_429_message(self):
        exc = Throttled(wait=30)
        response = custom_exception_handler(exc, make_context())

        assert response.status_code == 429
        assert response.data["message"] == (
            "Too many requests. Please slow down and try again shortly."
        )
        assert "detail" in response.data or "wait" in response.data

    def test_permission_denied_gets_403_message(self):
        exc = PermissionDenied()
        response = custom_exception_handler(exc, make_context())

        assert response.status_code == 403
        assert response.data["message"] == (
            "You do not have permission to perform this action."
        )

    def test_not_authenticated_gets_401_message(self):
        exc = NotAuthenticated()
        response = custom_exception_handler(exc, make_context())

        assert response.status_code == 401
        assert response.data["message"] == "Authentication required. Please login."

    def test_unlisted_status_code_gets_default_message_not_missing_key(self):
        from rest_framework.exceptions import APIException

        class WeirdException(APIException):
            status_code = 418
            default_detail = "I'm a teapot"

        exc = WeirdException()
        response = custom_exception_handler(exc, make_context())

        # previously: no "message" key at all for anything not in the
        # explicit if/elif chain
        assert "message" in response.data
        assert response.data["message"]  # non-empty fallback, not undefined