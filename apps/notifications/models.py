"""Minimized, durable in-app notification records."""

import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone


class NotificationType(models.TextChoices):
    CONTACT_REQUEST_RECEIVED = "CONTACT_REQUEST_RECEIVED", "Contact request received"
    CONTACT_REQUEST_ACCEPTED = "CONTACT_REQUEST_ACCEPTED", "Contact request accepted"
    CONTACT_REQUEST_DECLINED = "CONTACT_REQUEST_DECLINED", "Contact request declined"
    CONTACT_REQUEST_CANCELLED = "CONTACT_REQUEST_CANCELLED", "Contact request cancelled"
    CONTACT_REQUEST_EXPIRED = "CONTACT_REQUEST_EXPIRED", "Contact request expired"


class DeliveryStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    SENT = "SENT", "Sent"
    FAILED = "FAILED", "Failed"
    SKIPPED = "SKIPPED", "Skipped"


class NotificationChannel(models.TextChoices):
    IN_APP = "IN_APP", "In app"
    EMAIL = "EMAIL", "Email"
    SMS = "SMS", "SMS"


class Notification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    notification_type = models.CharField(max_length=40, choices=NotificationType.choices)
    title = models.CharField(max_length=120)
    body = models.CharField(max_length=300)
    resource_type = models.CharField(max_length=40, null=True, blank=True)
    resource_id = models.UUIDField(null=True, blank=True)
    channel = models.CharField(
        max_length=20,
        choices=NotificationChannel.choices,
        default=NotificationChannel.IN_APP,
    )
    delivery_status = models.CharField(
        max_length=20,
        choices=DeliveryStatus.choices,
        default=DeliveryStatus.PENDING,
    )
    read_at = models.DateTimeField(null=True, blank=True)
    provider_reference = models.CharField(max_length=120, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        db_table = "notifications_notification"
        indexes = [
            models.Index(
                fields=["recipient", "read_at", "-created_at"],
                name="notify_recipient_read_idx",
            ),
            models.Index(
                fields=["delivery_status", "created_at"],
                name="notify_delivery_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(notification_type__in=NotificationType.values),
                name="notify_type_valid",
            ),
            models.CheckConstraint(
                condition=Q(delivery_status__in=DeliveryStatus.values),
                name="notify_delivery_valid",
            ),
            models.CheckConstraint(
                condition=Q(channel__in=NotificationChannel.values),
                name="notify_channel_valid",
            ),
            models.CheckConstraint(
                condition=(
                    Q(resource_type__isnull=True, resource_id__isnull=True)
                    | Q(resource_type__isnull=False, resource_id__isnull=False)
                ),
                name="notify_resource_pair_valid",
            ),
        ]
