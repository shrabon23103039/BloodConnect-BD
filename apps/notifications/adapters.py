"""Email/SMS adapter contracts and safe mock implementations."""

from typing import Protocol

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from apps.notifications.models import NotificationChannel


class NotificationDeliveryError(Exception):
    """Base class for isolated notification transport failures."""


class TransientNotificationDeliveryError(NotificationDeliveryError):
    """A temporary provider failure that may succeed on bounded retry."""


class PermanentNotificationDeliveryError(NotificationDeliveryError):
    """A terminal provider/configuration error that must not be retried."""


class NotificationAdapter(Protocol):
    def send(self, *, destination: str, title: str, body: str, idempotency_key: str) -> str:
        """Send minimized copy and return a non-sensitive provider reference."""


class MockEmailAdapter:
    def send(self, *, destination, title, body, idempotency_key):
        if not destination or "@" not in destination:
            raise PermanentNotificationDeliveryError("Verified email is unavailable.")
        return f"mock-email:{idempotency_key}"


class MockSmsAdapter:
    def send(self, *, destination, title, body, idempotency_key):
        if not destination.startswith("+"):
            raise PermanentNotificationDeliveryError("Verified phone is unavailable.")
        return f"mock-sms:{idempotency_key}"


def get_notification_adapter(channel: str) -> NotificationAdapter:
    """Return only safe mock adapters until an authorized provider is reviewed."""
    if settings.NOTIFICATION_DELIVERY_MODE != "mock":
        raise ImproperlyConfigured(
            "Only mock notification delivery is enabled until a provider is authorized."
        )
    if channel == NotificationChannel.EMAIL:
        return MockEmailAdapter()
    if channel == NotificationChannel.SMS:
        return MockSmsAdapter()
    raise PermanentNotificationDeliveryError("Unsupported notification channel.")
