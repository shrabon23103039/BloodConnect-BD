import os
import subprocess
import sys

from django.conf import settings


def test_test_profile_isolated_and_debug_disabled():
    assert settings.DEBUG is False
    assert settings.SECRET_KEY
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


def test_production_profile_accepts_synthetic_secure_environment():
    environment = os.environ.copy()
    environment.update(
        {
            "DJANGO_SETTINGS_MODULE": "config.settings.production",
            "DJANGO_SECRET_KEY": "synthetic-test-only-secret-value",
            "DJANGO_ALLOWED_HOSTS": "bloodconnect.example.test",
            "DJANGO_CSRF_TRUSTED_ORIGINS": "https://bloodconnect.example.test",
            "DATABASE_URL": "postgresql://test:test@db:5432/bloodconnect?sslmode=require",
            "EMAIL_HOST": "smtp.example.test",
            "EMAIL_HOST_USER": "synthetic-user",
            "EMAIL_HOST_PASSWORD": "synthetic-password",
            "EMAIL_USE_TLS": "true",
        }
    )

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import django; django.setup(); from django.conf import settings; "
            "assert settings.DEBUG is False; "
            "assert settings.DATABASES['default']['ENGINE'] == 'django.db.backends.postgresql'; "
            "assert settings.SESSION_COOKIE_SECURE",
        ],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )

    assert result.returncode == 0, result.stderr


def test_production_profile_rejects_plaintext_smtp():
    environment = os.environ.copy()
    environment.update(
        {
            "DJANGO_SETTINGS_MODULE": "config.settings.production",
            "DJANGO_SECRET_KEY": "synthetic-test-only-secret-value",
            "DJANGO_ALLOWED_HOSTS": "bloodconnect.example.test",
            "DJANGO_CSRF_TRUSTED_ORIGINS": "https://bloodconnect.example.test",
            "DATABASE_URL": "postgresql://test:test@db:5432/bloodconnect?sslmode=require",
            "EMAIL_HOST": "smtp.example.test",
            "EMAIL_HOST_USER": "synthetic-user",
            "EMAIL_HOST_PASSWORD": "synthetic-password",
            "EMAIL_USE_TLS": "false",
            "EMAIL_USE_SSL": "false",
        }
    )

    result = subprocess.run(
        [sys.executable, "-c", "import django; django.setup()"],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )

    assert result.returncode != 0
    assert "Production SMTP must use TLS or SSL." in result.stderr


def test_database_url_configures_postgres_without_leaking_credentials():
    from config.database import database_config_from_url

    config = database_config_from_url(
        "postgresql://bloodconnect:synthetic%40pass@db:5433/bloodconnect?sslmode=require&connect_timeout=5"
    )["default"]

    assert config["ENGINE"] == "django.db.backends.postgresql"
    assert config["NAME"] == "bloodconnect"
    assert config["PASSWORD"] == "synthetic@pass"
    assert config["HOST"] == "db"
    assert config["PORT"] == "5433"
    assert config["OPTIONS"] == {"sslmode": "require", "connect_timeout": "5"}


def test_database_url_rejects_non_postgres_and_unsupported_options():
    import pytest
    from django.core.exceptions import ImproperlyConfigured

    from config.database import database_config_from_url

    with pytest.raises(ImproperlyConfigured, match="valid PostgreSQL URL"):
        database_config_from_url("sqlite:///db.sqlite3")
    with pytest.raises(ImproperlyConfigured, match="valid PostgreSQL URL"):
        database_config_from_url(
            "postgresql://test:supersecret@db/bloodconnect?options=-csearch_path=public"
        )


def test_database_url_errors_do_not_echo_credentials():
    import pytest
    from django.core.exceptions import ImproperlyConfigured

    from config.database import database_config_from_url

    with pytest.raises(ImproperlyConfigured) as error:
        database_config_from_url(
            "postgresql://test:supersecret@db/bloodconnect?options=-csearch_path=public"
        )
    assert "supersecret" not in str(error.value)


def test_test_profile_uses_isolated_database():
    assert settings.DATABASES["default"]["ENGINE"] == "django.db.backends.sqlite3"
    assert settings.DATABASES["default"]["NAME"].startswith("file:memorydb_default")
