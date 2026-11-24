import os
import subprocess
import sys

from django.conf import settings


def test_test_profile_isolated_and_debug_disabled():
    assert settings.DEBUG is False
    assert settings.SECRET_KEY
    assert settings.PASSWORD_HASHERS == ["django.contrib.auth.hashers.MD5PasswordHasher"]
    assert "django.middleware.csrf.CsrfViewMiddleware" in settings.MIDDLEWARE


def test_development_selects_smtp_only_when_full_configuration_is_present():
    environment = os.environ.copy()
    environment.update(
        {
            "DJANGO_SETTINGS_MODULE": "config.settings.development",
            "DATABASE_URL": "postgresql://test:test@db:5432/bloodconnect",
            "EMAIL_BACKEND": "",
            "EMAIL_HOST": "smtp-relay.brevo.com",
            "EMAIL_PORT": "587",
            "EMAIL_USE_TLS": "true",
            "EMAIL_USE_SSL": "false",
            "EMAIL_HOST_USER": "synthetic-smtp-user",
            "EMAIL_HOST_PASSWORD": "synthetic-smtp-key",
            "DEFAULT_FROM_EMAIL": "verified@example.test",
        }
    )
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import django; django.setup(); from django.conf import settings; "
            "assert settings.EMAIL_BACKEND == 'django.core.mail.backends.smtp.EmailBackend'; "
            "assert settings.ALLOW_MOCK_VERIFICATION",
        ],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )
    assert result.returncode == 0, result.stderr


def test_development_keeps_mock_backend_when_smtp_configuration_is_incomplete():
    environment = os.environ.copy()
    environment.update(
        {
            "DJANGO_SETTINGS_MODULE": "config.settings.development",
            "DATABASE_URL": "postgresql://test:test@db:5432/bloodconnect",
            "EMAIL_BACKEND": "",
            "EMAIL_HOST": "smtp-relay.brevo.com",
            "EMAIL_HOST_USER": "",
            "EMAIL_HOST_PASSWORD": "",
            "DEFAULT_FROM_EMAIL": "",
        }
    )
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import django; django.setup(); from django.conf import settings; "
            "assert settings.EMAIL_BACKEND == 'django.core.mail.backends.locmem.EmailBackend'",
        ],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )
    assert result.returncode == 0, result.stderr


def test_development_throttle_overrides_are_large_and_production_does_not_load_them():
    development_environment = os.environ.copy()
    development_environment.update(
        {
            "DJANGO_SETTINGS_MODULE": "config.settings.development",
            "DATABASE_URL": "postgresql://test:test@db:5432/bloodconnect",
            "EMAIL_BACKEND": "django.core.mail.backends.locmem.EmailBackend",
        }
    )
    development_result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import django; django.setup(); from django.conf import settings; "
            "assert settings.DEBUG; "
            "assert len(settings.DEVELOPMENT_THROTTLE_OVERRIDES) == 17; "
            "assert all(v == (1000, 3600) for v in settings.DEVELOPMENT_THROTTLE_OVERRIDES.values()); "
            "assert settings.DEVELOPMENT_VERIFICATION_SEND_COOLDOWN_SECONDS == 0; "
            "assert settings.DEVELOPMENT_VERIFICATION_MAX_SENDS_PER_HOUR == 1000; "
            "assert len(settings.ACCOUNT_RATE_LIMITS) == 12; "
            "assert all(v.startswith('1000/h') for v in settings.ACCOUNT_RATE_LIMITS.values())",
        ],
        check=False,
        capture_output=True,
        text=True,
        env=development_environment,
    )
    assert development_result.returncode == 0, development_result.stderr

    production_environment = os.environ.copy()
    production_environment.update(
        {
            "DJANGO_SETTINGS_MODULE": "config.settings.production",
            "DJANGO_SECRET_KEY": "synthetic-test-only-secret-value",
            "DJANGO_ALLOWED_HOSTS": "bloodconnect.example.test",
            "DJANGO_CSRF_TRUSTED_ORIGINS": "https://bloodconnect.example.test",
            "DATABASE_URL": "postgresql://test:test@db:5432/bloodconnect?sslmode=require",
            "DATABASE_SSLMODE": "require",
            "REDIS_URL": "redis://cache:6379/0",
            "BLOODCONNECT_PROCESS_ROLE": "worker",
        }
    )
    production_result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import django; django.setup(); from django.conf import settings; "
            "assert settings.DEBUG is False; "
            "assert not hasattr(settings, 'DEVELOPMENT_THROTTLE_OVERRIDES'); "
            "assert not hasattr(settings, 'DEVELOPMENT_VERIFICATION_MAX_SENDS_PER_HOUR'); "
            "from allauth.account import app_settings; "
            "assert app_settings.RATE_LIMITS['signup'] == '20/m/ip'; "
            "assert app_settings.RATE_LIMITS['login_failed'] == '10/m/ip,5/300s/key'; "
            "assert settings.REGISTRATION_THROTTLE_LIMIT == 5",
        ],
        check=False,
        capture_output=True,
        text=True,
        env=production_environment,
    )
    assert production_result.returncode == 0, production_result.stderr


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
            "DEFAULT_FROM_EMAIL": "verification@example.test",
            "EMAIL_USE_TLS": "true",
            "REDIS_URL": "redis://cache:6379/0",
            "DATABASE_SSLMODE": "require",
            "BLOODCONNECT_PROCESS_ROLE": "web",
        }
    )

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import django; django.setup(); from django.conf import settings; "
            "assert settings.DEBUG is False; "
            "assert settings.DATABASES['default']['ENGINE'] == 'django.db.backends.postgresql'; "
            "assert settings.SESSION_COOKIE_SECURE; "
            "assert settings.CACHES['default']['LOCATION'] == 'redis://cache:6379/0'; "
            "assert settings.CELERY_BROKER_URL == 'redis://cache:6379/1'; "
            "assert settings.CELERY_RESULT_BACKEND is None; "
            "assert settings.CELERY_TASK_ACKS_LATE; "
            "assert settings.NOTIFICATION_DELIVERY_MODE == 'disabled'",
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
            "DEFAULT_FROM_EMAIL": "verification@example.test",
            "EMAIL_USE_TLS": "false",
            "EMAIL_USE_SSL": "false",
            "REDIS_URL": "redis://cache:6379/0",
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


def test_production_worker_profile_does_not_require_web_smtp_credentials():
    environment = os.environ.copy()
    for name in ("EMAIL_HOST", "EMAIL_HOST_USER", "EMAIL_HOST_PASSWORD"):
        environment.pop(name, None)
    environment.update(
        {
            "DJANGO_SETTINGS_MODULE": "config.settings.production",
            "DJANGO_SECRET_KEY": "synthetic-test-only-secret-value",
            "DJANGO_ALLOWED_HOSTS": "bloodconnect.example.test",
            "DJANGO_CSRF_TRUSTED_ORIGINS": "https://bloodconnect.example.test",
            "DATABASE_URL": "postgresql://test:test@db:5432/bloodconnect",
            "DATABASE_SSLMODE": "require",
            "REDIS_URL": "redis://cache:6379/0",
            "BLOODCONNECT_PROCESS_ROLE": "worker",
        }
    )

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import django; django.setup(); from django.conf import settings; "
            "assert settings.PROCESS_ROLE == 'worker'; "
            "assert settings.DATABASES['default']['OPTIONS']['sslmode'] == 'require'",
        ],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )

    assert result.returncode == 0, result.stderr


def test_production_profile_rejects_database_tls_disabled():
    environment = os.environ.copy()
    environment.update(
        {
            "DJANGO_SETTINGS_MODULE": "config.settings.production",
            "DJANGO_SECRET_KEY": "synthetic-test-only-secret-value",
            "DJANGO_ALLOWED_HOSTS": "bloodconnect.example.test",
            "DJANGO_CSRF_TRUSTED_ORIGINS": "https://bloodconnect.example.test",
            "DATABASE_URL": "postgresql://test:test@db:5432/bloodconnect?sslmode=disable",
            "DATABASE_SSLMODE": "require",
            "EMAIL_HOST": "smtp.example.test",
            "EMAIL_HOST_USER": "synthetic-user",
            "EMAIL_HOST_PASSWORD": "synthetic-password",
            "EMAIL_USE_TLS": "true",
            "REDIS_URL": "redis://cache:6379/0",
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
    assert "Production DATABASE_URL must require PostgreSQL TLS" in result.stderr


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


def test_redis_database_urls_validate_and_separate_consumers():
    import pytest
    from django.core.exceptions import ImproperlyConfigured

    from config.redis import redis_database_url

    assert redis_database_url("rediss://user:secret@cache.example.test:6380/0?ssl_cert_reqs=required", 0) == (
        "rediss://user:secret@cache.example.test:6380/0?ssl_cert_reqs=required"
    )
    assert redis_database_url("redis://cache:6379/0", 1) == "redis://cache:6379/1"
    with pytest.raises(ImproperlyConfigured) as error:
        redis_database_url("postgresql://user:secret@db/name", 0)
    assert "secret" not in str(error.value)


def test_test_profile_uses_isolated_database():
    assert settings.DATABASES["default"]["ENGINE"] == "django.db.backends.sqlite3"
    assert settings.DATABASES["default"]["NAME"].startswith("file:memorydb_default")
