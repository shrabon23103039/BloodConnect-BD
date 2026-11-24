"""Fail-closed settings for production deployment."""

import os

from django.core.exceptions import ImproperlyConfigured

from config.database import database_config_from_url
from config.redis import redis_database_url
from .base import *  # noqa: F403

DEBUG = False
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    raise RuntimeError("DJANGO_SECRET_KEY must be set in production.")

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",")
    if host.strip()
]
if not ALLOWED_HOSTS:
    raise RuntimeError("DJANGO_ALLOWED_HOSTS must contain at least one host in production.")

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]
if not CSRF_TRUSTED_ORIGINS:
    raise RuntimeError("DJANGO_CSRF_TRUSTED_ORIGINS must contain HTTPS origins in production.")
if any(not origin.startswith("https://") for origin in CSRF_TRUSTED_ORIGINS):
    raise RuntimeError("Production CSRF trusted origins must use HTTPS.")

DATABASE_URL = os.environ.get("DATABASE_URL", "")
if not DATABASE_URL:
    raise ImproperlyConfigured("DATABASE_URL must be set in production.")
DATABASES = database_config_from_url(DATABASE_URL)
database_sslmode = os.environ.get("DATABASE_SSLMODE", "require").strip().lower()
tls_sslmodes = {"require", "verify-ca", "verify-full"}
if database_sslmode not in tls_sslmodes:
    raise ImproperlyConfigured("DATABASE_SSLMODE must require PostgreSQL TLS.")
configured_sslmode = DATABASES["default"]["OPTIONS"].get("sslmode")
if configured_sslmode and configured_sslmode not in tls_sslmodes:
    raise ImproperlyConfigured("Production DATABASE_URL must require PostgreSQL TLS with sslmode.")
DATABASES["default"]["OPTIONS"].setdefault("sslmode", database_sslmode)
REDIS_URL = os.environ.get("REDIS_URL", "")
if not REDIS_URL:
    raise ImproperlyConfigured("REDIS_URL must be set in production.")
redis_database_url(REDIS_URL, 0)
CELERY_BROKER_URL = redis_database_url(REDIS_URL, 1)
NOTIFICATION_DELIVERY_MODE = "disabled"
if DATABASES["default"]["OPTIONS"].get("sslmode") not in {"require", "verify-ca", "verify-full"}:
    raise ImproperlyConfigured("Production DATABASE_URL must require PostgreSQL TLS with sslmode.")

PROCESS_ROLE = os.environ.get("BLOODCONNECT_PROCESS_ROLE", "web").strip().lower()
if PROCESS_ROLE not in {"web", "worker", "scheduler"}:
    raise RuntimeError("BLOODCONNECT_PROCESS_ROLE must be web, worker or scheduler.")
if PROCESS_ROLE == "web":
    if not EMAIL_HOST or not EMAIL_HOST_USER or not EMAIL_HOST_PASSWORD:
        raise ImproperlyConfigured(
            "EMAIL_HOST, EMAIL_HOST_USER and EMAIL_HOST_PASSWORD must be set for the web service."
        )
    if not DEFAULT_FROM_EMAIL:
        raise ImproperlyConfigured(
            "DEFAULT_FROM_EMAIL must be set to an authorized sender for the web service."
        )
    if EMAIL_USE_TLS and EMAIL_USE_SSL:
        raise ImproperlyConfigured("Configure SMTP with TLS or SSL, not both.")
    if not EMAIL_USE_TLS and not EMAIL_USE_SSL:
        raise ImproperlyConfigured("Production SMTP must use TLS or SSL.")

SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_HSTS_SECONDS = 31_536_000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
