"""Isolated settings for automated tests."""

import secrets

from .base import *  # noqa: F403

DEBUG = False
ALLOW_MOCK_VERIFICATION = True
SECRET_KEY = secrets.token_urlsafe(48)
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "bloodconnect-tests",
    }
}
CELERY_BROKER_URL = "memory://"
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
NOTIFICATION_DELIVERY_MODE = "mock"
STORAGES = {
    **STORAGES,
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
