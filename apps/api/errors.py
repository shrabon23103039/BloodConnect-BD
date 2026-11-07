"""Consistent, privacy-safe error envelopes for DRF endpoints."""

from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return None

    status_code = response.status_code
    code_message = {
        400: ("VALIDATION_ERROR", "Please review the submitted information."),
        401: ("AUTHENTICATION_REQUIRED", "Authentication is required or credentials are invalid."),
        403: ("PERMISSION_DENIED", "This action is not available to this account."),
        404: ("NOT_FOUND", "The requested resource is not available."),
        429: ("RATE_LIMITED", "Too many requests. Please wait before trying again."),
    }
    code, message = code_message.get(
        status_code,
        ("REQUEST_ERROR", "The request could not be completed."),
    )
    error = {"code": code, "message": message}
    if status_code == 400:
        if isinstance(response.data, dict):
            error["fields"] = response.data
        else:
            error["fields"] = {"non_field_errors": response.data}
    request = context.get("request")
    underlying_request = getattr(request, "_request", request) if request else None
    error["request_id"] = getattr(underlying_request, "request_id", "") if underlying_request else ""
    response.data = {"error": error}
    return response
