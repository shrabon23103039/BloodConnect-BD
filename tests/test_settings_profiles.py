import os
import subprocess
import sys

from django.conf import settings


def test_test_profile_isolated_and_debug_disabled():
    assert settings.DEBUG is False
    assert settings.SECRET_KEY == "test-only-secret-key-not-for-deployment"
    assert settings.PASSWORD_HASHERS == ["django.contrib.auth.hashers.MD5PasswordHasher"]
    assert "django.middleware.csrf.CsrfViewMiddleware" in settings.MIDDLEWARE


def test_production_profile_fails_closed_without_required_environment():
    environment = os.environ.copy()
    for name in (
        "DJANGO_SECRET_KEY",
        "DJANGO_ALLOWED_HOSTS",
        "DJANGO_CSRF_TRUSTED_ORIGINS",
    ):
        environment.pop(name, None)
    environment["DJANGO_SETTINGS_MODULE"] = "config.settings.production"

    result = subprocess.run(
        [sys.executable, "-c", "import django; django.setup()"],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )

    assert result.returncode != 0
    assert "DJANGO_SECRET_KEY must be set in production." in result.stderr
