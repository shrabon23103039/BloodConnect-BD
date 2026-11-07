from django.apps import AppConfig


class ApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.api"
    label = "api"
    verbose_name = "Versioned API"

    def ready(self):
        from apps.api import schema  # noqa: F401
