"""Validate Redis URLs and select a logical database for each consumer."""

from urllib.parse import urlsplit, urlunsplit

from django.core.exceptions import ImproperlyConfigured


def redis_database_url(value: str, database: int, *, require_tls: bool = False) -> str:
    """Return a Redis URL using the requested DB index without echoing secrets."""
    try:
        parsed = urlsplit(value)
        allowed_schemes = {"rediss"} if require_tls else {"redis", "rediss"}
        if parsed.scheme not in allowed_schemes or not parsed.netloc:
            raise ValueError
        if parsed.fragment:
            raise ValueError
        return urlunsplit(parsed._replace(path=f"/{database}"))
    except (TypeError, ValueError) as error:
        message = (
            "Production REDIS_URL must use rediss://."
            if require_tls
            else "REDIS_URL must be a valid redis:// or rediss:// URL."
        )
        raise ImproperlyConfigured(message) from error
