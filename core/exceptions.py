from rest_framework.views import exception_handler
from rest_framework.response import Response


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        response.data["status_code"] = response.status_code
        response.data["error"] = True

        if response.status_code == 400:
            response.data["message"] = "Bad request. Please check your input."
        elif response.status_code == 401:
            response.data["message"] = "Authentication required. Please login."
        elif response.status_code == 403:
            response.data["message"] = (
                "You do not have permission to perform this action."
            )
        elif response.status_code == 404:
            response.data["message"] = "Resource not found."
        elif response.status_code == 500:
            response.data["message"] = "Internal server error. Please try again later."

    return response
