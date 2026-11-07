"""Private, consent-gated contact request records."""

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.donors.models import DonorProfile
from apps.requests.models import BloodRequest


class ContactRequestStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    ACCEPTED = "ACCEPTED", "Accepted"
    DECLINED = "DECLINED", "Declined"
    CANCELLED = "CANCELLED", "Cancelled"
    EXPIRED = "EXPIRED", "Expired"


class ConnectionStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    CLOSED = "CLOSED", "Closed"
    REPORTED = "REPORTED", "Reported"


class ContactRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="outgoing_contact_requests",
    )
    donor_profile = models.ForeignKey(
        DonorProfile,
        on_delete=models.PROTECT,
        related_name="contact_requests",
    )
    blood_request = models.ForeignKey(
        BloodRequest,
        on_delete=models.PROTECT,
        related_name="contact_requests",
    )
    message = models.CharField(max_length=500, null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=ContactRequestStatus.choices,
        default=ContactRequestStatus.PENDING,
    )
    expires_at = models.DateTimeField()
    decided_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "connections_contactrequest"
        indexes = [
            models.Index(
                fields=["donor_profile", "status", "-created_at"],
                name="contact_donor_status_idx",
            ),
            models.Index(
                fields=["recipient", "status", "-created_at"],
                name="contact_recipient_idx",
            ),
            models.Index(
                fields=["blood_request", "status"],
                name="contact_request_status_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(status__in=ContactRequestStatus.values),
                name="contact_status_valid",
            ),
            models.CheckConstraint(
                condition=Q(expires_at__gt=models.F("created_at")),
                name="contact_expiry_after_create",
            ),
            models.UniqueConstraint(
                fields=["recipient", "donor_profile", "blood_request"],
                condition=Q(status=ContactRequestStatus.PENDING),
                name="contact_one_pending_uniq",
            ),
        ]

    def clean(self):
        errors = {}
        if self.recipient_id and self.donor_profile_id:
            if self.recipient_id == self.donor_profile.user_id:
                errors["donor_profile"] = "You cannot contact your own donor profile."
        if self.blood_request_id and self.recipient_id:
            if self.blood_request.requester_id != self.recipient_id:
                errors["blood_request"] = "Choose one of your own blood requests."
        if self.status == ContactRequestStatus.PENDING and self.blood_request_id:
            if self.blood_request.status != "OPEN":
                errors["blood_request"] = "Contact requests require an open blood request."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"Contact request {self.id} ({self.status})"


class Connection(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contact_request = models.OneToOneField(
        ContactRequest,
        on_delete=models.PROTECT,
        related_name="connection",
    )
    status = models.CharField(
        max_length=20,
        choices=ConnectionStatus.choices,
        default=ConnectionStatus.ACTIVE,
    )
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "connections_connection"
        constraints = [
            models.CheckConstraint(
                condition=Q(status__in=ConnectionStatus.values),
                name="connection_status_valid",
            ),
        ]
