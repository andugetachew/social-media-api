from rest_framework.response import Response
from rest_framework.views import exception_handler

STATUS_MESSAGES = {
    400: "Bad request. Please check your input.",
    401: "Authentication required. Please login.",
    403: "You do not have permission to perform this action.",
    404: "Resource not found.",
    405: "This method is not allowed for this endpoint.",
    415: "Unsupported media type.",
    429: "Too many requests. Please slow down and try again shortly.",
    500: "Internal server error. Please try again later.",
}

DEFAULT_MESSAGE = "An error occurred while processing your request."


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is None:
        return response

   
    if isinstance(response.data, dict):
        original_detail = response.data
    else:
        original_detail = {"detail": response.data}

    original_detail["status_code"] = response.status_code
    original_detail["error"] = True
  
    original_detail["message"] = STATUS_MESSAGES.get(response.status_code, DEFAULT_MESSAGE)

    response.data = original_detail
    return response