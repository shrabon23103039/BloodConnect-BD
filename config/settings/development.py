"""Local development settings. Never use this module in production."""

import os

from django.core.exceptions import ImproperlyConfigured

from config.database import database_config_from_url
from .base import *  # noqa: F403

DEBUG = os.environ.get("DJANGO_DEBUG", "true").strip().lower() in {"1", "true", "yes"}
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
STORAGES = {
    **STORAGES,
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
