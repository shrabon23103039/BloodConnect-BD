"""Isolated settings for automated tests."""

from .development import *  # noqa: F403

DEBUG = False
SECRET_KEY = "test-only-secret-key-not-for-deployment"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
