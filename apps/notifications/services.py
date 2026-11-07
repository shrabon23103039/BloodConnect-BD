"""Create minimized in-app events from controlled notification templates."""

import logging

from django.conf import settings
from django.db import transaction

from apps.notifications.models import (
    Notification,
    NotificationChannel,
    NotificationType,
)
from apps.governance.models import ConsentType, current_consent_state

logger = logging.getLogger(__name__)

CONTACT_EVENT_COPY = {
    NotificationType.CONTACT_REQUEST_RECEIVED: (
        "New contact request",
        "A potential recipient has sent you a contact request. Open your incoming requests to respond.",
    ),
    NotificationType.CONTACT_REQUEST_ACCEPTED: (
        "Contact request accepted",
        "Your contact request was accepted. Open the connection to see donor-approved contact methods.",
    ),
    NotificationType.CONTACT_REQUEST_DECLINED: (
        "Contact request declined",
        "Your contact request was declined. You can review its status in your outgoing requests.",
    ),
    NotificationType.CONTACT_REQUEST_CANCELLED: (
        "Contact request cancelled",
        "A pending contact request was cancelled. Review your incoming requests for details.",
    ),
    NotificationType.CONTACT_REQUEST_EXPIRED: (
        "Contact request expired",
        "A pending contact request expired. Open your requests to review its status.",
    ),
}


def notify_contact_event(*, recipient, notification_type, contact_request_id):
    """Persist a fixed-copy notification without contact or request details."""
    try:
        title, body = CONTACT_EVENT_COPY[notification_type]
    except KeyError as error:
        raise ValueError("Unsupported contact notification type.") from error
    notification = Notification.objects.create(
        recipient=recipient,
        notification_type=notification_type,
        title=title,
        body=body,
        resource_type="contact_request",
        resource_id=contact_request_id,
        channel=NotificationChannel.IN_APP,
    )
    transaction.on_commit(lambda: _enqueue_after_commit(notification.pk))

    if (
        settings.NOTIFICATION_DELIVERY_MODE == "mock"
        and current_consent_state(recipient).get(
            ConsentType.OPTIONAL_NOTIFICATIONS, False
        )
    ):
        for channel, identifier, verified_at in (
            (NotificationChannel.EMAIL, recipient.email, recipient.email_verified_at),
            (NotificationChannel.SMS, recipient.phone_e164, recipient.phone_verified_at),
        ):
            if identifier and verified_at:
                outbound = Notification.objects.create(
                    recipient=recipient,
                    notification_type=notification_type,
                    title=title,
                    body=body,
                    resource_type="contact_request",
                    resource_id=contact_request_id,
                    channel=channel,
                )
                transaction.on_commit(lambda notification_id=outbound.pk: _enqueue_after_commit(notification_id))
    return notification


def _enqueue_after_commit(notification_id):
    """Queue committed work without failing its contact transaction if Redis is down."""
    if not settings.CELERY_BROKER_URL:
        return
    from apps.notifications.tasks import process_notification

    try:
        process_notification.apply_async(
            args=[str(notification_id)],
            task_id=str(notification_id),
        )
    except Exception:
        logger.warning(
            "Notification enqueue failed; pending row will be redriven.",
            extra={"notification_id": str(notification_id)},
        )
