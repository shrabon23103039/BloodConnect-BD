"""Isolated settings for automated tests."""

import secrets

from .base import *  # noqa: F403

DEBUG = False
SECRET_KEY = secrets.token_urlsafe(48)
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
STORAGES = {
    **STORAGES,
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
