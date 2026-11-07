"""Validate Redis URLs and select a logical database for each consumer."""

from urllib.parse import urlsplit, urlunsplit

from django.core.exceptions import ImproperlyConfigured


def redis_database_url(value: str, database: int) -> str:
    """Return a Redis URL using the requested DB index without echoing secrets."""
    try:
        parsed = urlsplit(value)
        if parsed.scheme not in {"redis", "rediss"} or not parsed.netloc:
            raise ValueError
        if parsed.fragment:
            raise ValueError
        return urlunsplit(parsed._replace(path=f"/{database}"))
    except (TypeError, ValueError) as error:
        raise ImproperlyConfigured("REDIS_URL must be a valid redis:// or rediss:// URL.") from error
