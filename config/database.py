"""Build safe Django PostgreSQL settings from a DATABASE_URL."""

from urllib.parse import parse_qsl, unquote, urlsplit

from django.core.exceptions import ImproperlyConfigured

_ALLOWED_QUERY_OPTIONS = {"application_name", "connect_timeout", "sslmode"}
_ALLOWED_SSL_MODES = {"disable", "allow", "prefer", "require", "verify-ca", "verify-full"}


def database_config_from_url(database_url: str) -> dict[str, dict[str, object]]:
    """Parse a PostgreSQL URL without exposing credentials in errors or logs."""
    if not database_url:
        raise ImproperlyConfigured("DATABASE_URL must be configured for PostgreSQL.")

    try:
        parsed = urlsplit(database_url)
        if parsed.scheme not in {"postgres", "postgresql"}:
            raise ValueError
        if (
            not parsed.hostname
            or not parsed.username
            or not parsed.password
            or not parsed.path.strip("/")
            or parsed.fragment
        ):
            raise ValueError
        port = parsed.port if parsed.port is not None else 5432
        if not 1 <= port <= 65535:
            raise ValueError
        option_pairs = parse_qsl(parsed.query, keep_blank_values=True, strict_parsing=True)
        options = dict(option_pairs)
        if len(options) != len(option_pairs):
            raise ValueError
        if set(options) - _ALLOWED_QUERY_OPTIONS:
            raise ValueError
        if "sslmode" in options and options["sslmode"] not in _ALLOWED_SSL_MODES:
            raise ValueError
        if "connect_timeout" in options and (
            not options["connect_timeout"].isdigit() or int(options["connect_timeout"]) < 1
        ):
            raise ValueError
        options.setdefault("connect_timeout", "3")
    except (ValueError, UnicodeError):
        raise ImproperlyConfigured(
            "DATABASE_URL must be a valid PostgreSQL URL with a database name and supported options."
        ) from None

    database = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": unquote(parsed.path.lstrip("/")),
        "USER": unquote(parsed.username or ""),
        "PASSWORD": unquote(parsed.password or ""),
        "HOST": parsed.hostname,
        "PORT": str(port),
        "OPTIONS": options,
        "CONN_MAX_AGE": 60,
        "CONN_HEALTH_CHECKS": True,
    }
    return {"default": database}
