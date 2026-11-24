"""Local development settings. Never use this module in production."""

import os

from django.core.exceptions import ImproperlyConfigured

from config.database import database_config_from_url
from .base import *  # noqa: F403

DEBUG = os.environ.get("DJANGO_DEBUG", "true").strip().lower() in {"1", "true", "yes"}
# Local test profile only: retain a large bounded quota so repeat page loads,
# auth attempts and OAuth callbacks do not exhaust the production-sized caps.
# The limiter applies this map only when DEBUG is true; production.py never
# imports this settings module or map.
DEVELOPMENT_THROTTLE_OVERRIDES = {
    scope: (1000, 3600)
    for scope in (
        "register",
        "verification-send",
        "verification-attempt",
        "phone-reset-send",
        "phone-reset-attempt",
        "login",
        "password-reset",
        "google-oauth-start",
        "google-oauth-callback",
        "donor-search",
        "contact-create",
        "api-token-issue",
        "api-token-refresh",
        "api-token-revoke",
        "api-donor-search",
        "api-blood-request-create",
        "api-contact-create",
    )
}
DEVELOPMENT_VERIFICATION_SEND_COOLDOWN_SECONDS = 0
DEVELOPMENT_VERIFICATION_MAX_SENDS_PER_HOUR = 1000
ACCOUNT_RATE_LIMITS = {
    "change_password": "1000/h/user",
    "change_phone": "1000/h/user",
    "manage_email": "1000/h/user",
    "reset_password": "1000/h/ip,1000/h/key",
    "reauthenticate": "1000/h/user",
    "reset_password_from_key": "1000/h/ip",
    "signup": "1000/h/ip",
    "login": "1000/h/ip",
    "request_login_code": "1000/h/ip,1000/h/key",
    "login_failed": "1000/h/ip,1000/h/key",
    "confirm_email": "1000/h/key",
    "verify_phone": "1000/h/key,1000/h/ip",
}
GOOGLE_MAPS_BROWSER_API_KEY = os.environ.get("GOOGLE_MAPS_BROWSER_API_KEY", "").strip()
ALLOW_MOCK_VERIFICATION = True
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY", "django-insecure-local-development-only-not-for-production"
)
ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if host.strip()
]
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]

DATABASE_URL = os.environ.get("DATABASE_URL", "")
if not DATABASE_URL:
    raise ImproperlyConfigured("Set DATABASE_URL to the local PostgreSQL service before running Django.")
DATABASES = database_config_from_url(DATABASE_URL)
_email_backend_override = os.environ.get("EMAIL_BACKEND", "").strip()
if _email_backend_override:
    EMAIL_BACKEND = _email_backend_override
elif all((EMAIL_HOST, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, DEFAULT_FROM_EMAIL)):
    # Supplying the full SMTP configuration opts local development into real mail.
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
else:
    EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
STORAGES = {
    **STORAGES,
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
