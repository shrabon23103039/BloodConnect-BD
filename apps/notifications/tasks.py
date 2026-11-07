"""Bounded, idempotent notification worker tasks."""

from celery import shared_task
from django.db import OperationalError, transaction
from kombu.exceptions import OperationalError as BrokerOperationalError

from apps.accounts.models import AccountStatus
from apps.governance.models import ConsentType, current_consent_state
from apps.notifications.adapters import (
    PermanentNotificationDeliveryError,
    TransientNotificationDeliveryError,
    get_notification_adapter,
)
from apps.notifications.models import (
    DeliveryStatus,
    Notification,
    NotificationChannel,
)


@shared_task(
    bind=True,
    name="apps.notifications.tasks.process_notification",
    autoretry_for=(OperationalError,),
    retry_backoff=2,
    retry_backoff_max=60,
    retry_jitter=True,
    max_retries=3,
    acks_late=True,
)
def process_notification(self, notification_id):
    """Deliver one committed outbox row; stable keys and row state guard retries."""
    with transaction.atomic():
        notification = Notification.objects.select_for_update().filter(
            pk=notification_id
        ).select_related("recipient").first()
        if notification is None:
            return "missing"
        if notification.delivery_status != DeliveryStatus.PENDING:
            return notification.delivery_status.lower()
        if notification.channel == NotificationChannel.IN_APP:
            notification.delivery_status = DeliveryStatus.SENT
            notification.save(update_fields=["delivery_status"])
            return "sent"
        recipient = notification.recipient
        consent_state = current_consent_state(recipient)
        if (
            recipient.account_status != AccountStatus.ACTIVE
            or not consent_state.get(ConsentType.OPTIONAL_NOTIFICATIONS, False)
        ):
            notification.delivery_status = DeliveryStatus.SKIPPED
            notification.save(update_fields=["delivery_status"])
            return "skipped"
        if notification.channel == NotificationChannel.EMAIL:
            destination = recipient.email
            verified = recipient.email_verified_at
        elif notification.channel == NotificationChannel.SMS:
            destination = recipient.phone_e164
            verified = recipient.phone_verified_at
        else:
            notification.delivery_status = DeliveryStatus.SKIPPED
            notification.save(update_fields=["delivery_status"])
            return "skipped"
        if not destination or not verified:
            notification.delivery_status = DeliveryStatus.SKIPPED
            notification.save(update_fields=["delivery_status"])
            return "skipped"
        delivery = {
            "channel": notification.channel,
            "destination": destination,
            "title": notification.title,
            "body": notification.body,
            "notification_id": str(notification.pk),
        }

    try:
        adapter = get_notification_adapter(delivery["channel"])
        provider_reference = adapter.send(
            destination=delivery["destination"],
            title=delivery["title"],
            body=delivery["body"],
            idempotency_key=delivery["notification_id"],
        )
    except TransientNotificationDeliveryError as error:
        if self.request.retries >= self.max_retries:
            _mark_delivery_failed(notification_id)
            return "failed"
        raise self.retry(exc=error, countdown=min(5 * (2**self.request.retries), 60))
    except PermanentNotificationDeliveryError:
        _mark_delivery_failed(notification_id)
        return "failed"

    with transaction.atomic():
        notification = Notification.objects.select_for_update().get(pk=notification_id)
        if notification.delivery_status != DeliveryStatus.PENDING:
            return notification.delivery_status.lower()
        notification.delivery_status = DeliveryStatus.SENT
        notification.provider_reference = provider_reference
        notification.save(update_fields=["delivery_status", "provider_reference"])
    return "sent"


def _mark_delivery_failed(notification_id):
    with transaction.atomic():
        Notification.objects.select_for_update().filter(
            pk=notification_id,
            delivery_status=DeliveryStatus.PENDING,
        ).update(delivery_status=DeliveryStatus.FAILED)


@shared_task(
    bind=True,
    name="apps.notifications.tasks.redrive_pending_notifications",
    autoretry_for=(BrokerOperationalError,),
    retry_backoff=5,
    retry_backoff_max=60,
    retry_jitter=True,
    max_retries=3,
)
def redrive_pending_notifications(self, batch_size=100):
    """Enqueue a bounded set of pending outbox rows with stable task IDs."""
    if batch_size < 1 or batch_size > 500:
        raise ValueError("batch_size must be between 1 and 500")
    notification_ids = list(
        Notification.objects.filter(delivery_status=DeliveryStatus.PENDING)
        .order_by("created_at", "id")
        .values_list("id", flat=True)[:batch_size]
    )
    for notification_id in notification_ids:
        process_notification.apply_async(
            args=[str(notification_id)],
            task_id=str(notification_id),
        )
    return len(notification_ids)
