"""Shared, environment-independent Django settings."""

import os
from pathlib import Path

from config.database import database_config_from_url
from config.logging import LOGGING
from config.redis import redis_database_url

BASE_DIR = Path(__file__).resolve().parents[2]

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
DEBUG = False
ALLOWED_HOSTS: list[str] = []
ALLOW_MOCK_VERIFICATION = False
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.environ.get("EMAIL_HOST", "")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT") or "587")
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "").strip()
EMAIL_USE_TLS = (os.environ.get("EMAIL_USE_TLS") or "true").strip().lower() in {
    "1",
    "true",
    "yes",
}
EMAIL_USE_SSL = os.environ.get("EMAIL_USE_SSL", "").strip().lower() in {
    "1",
    "true",
    "yes",
}
EMAIL_TIMEOUT = 10
REDIS_URL = os.environ.get("REDIS_URL", "")
NOTIFICATION_DELIVERY_MODE = os.environ.get("NOTIFICATION_DELIVERY_MODE", "mock").strip().lower()
CACHES = (
    {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": redis_database_url(REDIS_URL, 0),
        }
    }
    if REDIS_URL
    else {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "bloodconnect-default",
        }
    }
)
CELERY_BROKER_URL = redis_database_url(REDIS_URL, 1) if REDIS_URL else ""
CELERY_RESULT_BACKEND = None
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TASK_IGNORE_RESULT = True
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_SOFT_TIME_LIMIT = 45
CELERY_TASK_TIME_LIMIT = 60
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_BROKER_CONNECTION_MAX_RETRIES = 3
CELERY_TASK_PUBLISH_RETRY = True
CELERY_TASK_PUBLISH_RETRY_POLICY = {
    "max_retries": 3,
    "interval_start": 1,
    "interval_step": 2,
    "interval_max": 5,
}
CELERY_BROKER_TRANSPORT_OPTIONS = {"visibility_timeout": 90}
CELERY_BEAT_SCHEDULE = {
    "redrive-pending-notifications-every-minute": {
        "task": "apps.notifications.tasks.redrive_pending_notifications",
        "schedule": 60.0,
    },
}

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "rest_framework",
    "drf_spectacular",
    "apps.accounts.apps.AccountsConfig",
    "apps.governance.apps.GovernanceConfig",
    "apps.locations.apps.LocationsConfig",
    "apps.donors.apps.DonorsConfig",
    "apps.requests.apps.RequestsConfig",
    "apps.connections.apps.ConnectionsConfig",
    "apps.notifications.apps.NotificationsConfig",
    "apps.moderation.apps.ModerationConfig",
    "apps.audit.apps.AuditConfig",
    "apps.analytics.apps.AnalyticsConfig",
    "apps.api.apps.ApiConfig",
]
TERMS_POLICY_VERSION = "draft-1"
PRIVACY_POLICY_VERSION = "draft-1"
AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = [
    "apps.accounts.authentication.IdentifierBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]
ACCOUNT_ADAPTER = "apps.accounts.social_auth.BloodConnectAccountAdapter"
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_USER_MODEL_EMAIL_FIELD = "email"
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*"]
# Django's global default points to the optional, unmounted
# /accounts/profile/ route. Use the project's existing public home route, which
# is also the destination used by the server-rendered login view.
LOGIN_REDIRECT_URL = "home"
ACCOUNT_EMAIL_VERIFICATION = "none"
SOCIALACCOUNT_ADAPTER = "apps.accounts.social_auth.BloodConnectSocialAccountAdapter"
SOCIALACCOUNT_AUTO_SIGNUP = False
SOCIALACCOUNT_EMAIL_AUTHENTICATION = False
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = False
SOCIALACCOUNT_LOGIN_ON_GET = False
SOCIALACCOUNT_STORE_TOKENS = False
SOCIALACCOUNT_FORMS = {
    "signup": "apps.accounts.social_forms.GoogleSocialSignupForm",
}
GOOGLE_OAUTH_CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "").strip()
GOOGLE_OAUTH_CLIENT_SECRET = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", "").strip()
GOOGLE_OAUTH_ENABLED = bool(GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET)
# Conservative production defaults; local development may override these.
REGISTRATION_THROTTLE_LIMIT = 5
GOOGLE_OAUTH_START_THROTTLE_LIMIT = 10
SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "APP": {
            "client_id": GOOGLE_OAUTH_CLIENT_ID,
            "secret": GOOGLE_OAUTH_CLIENT_SECRET,
            "key": "",
        },
        "SCOPE": ["openid", "email", "profile"],
        "OAUTH_PKCE_ENABLED": True,
        "EMAIL_AUTHENTICATION": False,
        "EMAIL_AUTHENTICATION_AUTO_CONNECT": False,
    }
}
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.api.authentication.BearerTokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "EXCEPTION_HANDLER": "apps.api.errors.api_exception_handler",
}
SPECTACULAR_SETTINGS = {
    "TITLE": "BloodConnect BD API",
    "DESCRIPTION": "Versioned API for consent-aware donor coordination.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "ENUM_NAME_OVERRIDES": {
        "BloodRequestStatus": "apps.requests.models.BloodRequestStatus.choices",
        "ContactRequestStatus": "apps.connections.models.ContactRequestStatus.choices",
    },
}

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "config.middleware.RequestLoggingMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.accounts.context_processors.google_oauth",
                "apps.notifications.context_processors.unread_in_app_count",
                "apps.requests.context_processors.request_workspace_counts",
            ],
        },
    },
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Dhaka"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
    },
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
