"""Request correlation and privacy-safe operational logging middleware."""

import logging
import time
import uuid

from django.http import HttpRequest, HttpResponse

logger = logging.getLogger("bloodconnect.request")


class RequestLoggingMiddleware:
    """Log method, outcome, duration and a server-generated correlation ID."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request_id = uuid.uuid4().hex
        request.request_id = request_id
        started = time.perf_counter()
        status_code = 500
        event = "request_failed"
        try:
            response = self.get_response(request)
            status_code = response.status_code
            event = "request_completed"
            response["X-Request-ID"] = request_id
            return response
        finally:
            logger.info(
                event,
                extra={
                    "event": event,
                    "request_id": request_id,
                    "method": request.method,
                    "status_code": status_code,
                    "duration_ms": (time.perf_counter() - started) * 1000,
                },
            )
