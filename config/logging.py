"""Privacy-preserving structured request log formatting."""

import json
import logging
from datetime import datetime, timezone

_EVENTS = {"request_completed", "request_failed"}
_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}


class JsonFormatter(logging.Formatter):
    """Serialize an allowlist of operational fields; omit messages and tracebacks."""

    def format(self, record: logging.LogRecord) -> str:
        event = getattr(record, "event", "")
        method = getattr(record, "method", "")
        status_code = getattr(record, "status_code", 0)
        duration_ms = getattr(record, "duration_ms", 0)
        request_id = getattr(record, "request_id", "")

        payload = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": event if isinstance(event, str) and event in _EVENTS else "application_event",
            "request_id": request_id if isinstance(request_id, str) else "",
        }
        if method:
            payload["method"] = method if method in _METHODS else "OTHER"
        if isinstance(status_code, int) and 100 <= status_code <= 599:
            payload["status_code"] = status_code
        if isinstance(duration_ms, (int, float)) and 0 <= duration_ms < 86_400_000:
            payload["duration_ms"] = round(duration_ms, 2)
        return json.dumps(payload, separators=(",", ":"), ensure_ascii=True)


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "privacy_json": {"()": "config.logging.JsonFormatter"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "privacy_json",
        },
    },
    "root": {"handlers": ["console"], "level": "WARNING"},
    "loggers": {
        "bloodconnect.request": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "django.server": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
