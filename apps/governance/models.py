"""Append-only account consent history."""

import uuid

from django.conf import settings
from django.db import models, transaction
from django.utils import timezone


class ConsentType(models.TextChoices):
    TERMS_ACCEPTED = "terms_accepted", "Terms acceptance"
    PRIVACY_ACKNOWLEDGED = "privacy_acknowledged", "Privacy notice acknowledgement"
    DONOR_DISCOVERY = "donor_discovery", "Donor profile discoverability"
    PHONE_SHARE_AFTER_ACCEPT = "phone_share_after_accept", "Phone sharing after donor acceptance"
    EMAIL_SHARE_AFTER_ACCEPT = "email_share_after_accept", "Email sharing after donor acceptance"
    OPTIONAL_NOTIFICATIONS = "optional_notifications", "Optional notifications"
    LOCATION_DISPLAY = "location_display", "Optional generalized location display"
    ORGANIZATION_SHARING = "organization_sharing", "Future organization sharing"


class ConsentSource(models.TextChoices):
    WEB = "WEB", "Web"
    MOBILE = "MOBILE", "Mobile"
    ADMIN = "ADMIN", "Admin"


class ConsentRecord(models.Model):
    """One consent grant or withdrawal event; prior events are never updated."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="consent_records",
    )
    consent_type = models.CharField(max_length=50, choices=ConsentType.choices)
    policy_version = models.CharField(max_length=30)
    granted = models.BooleanField()
    captured_at = models.DateTimeField(default=timezone.now)
    withdrawn_at = models.DateTimeField(null=True, blank=True)
    source = models.CharField(max_length=30, choices=ConsentSource.choices)

    class Meta:
        ordering = ("-captured_at", "-id")
        indexes = [models.Index(fields=["user", "consent_type", "-captured_at"])]
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(policy_version=""),
                name="governance_consent_policy_version_nonempty",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(granted=True, withdrawn_at__isnull=True)
                    | models.Q(granted=False)
                ),
                name="governance_consent_withdrawal_consistent",
            ),
        ]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValueError("Consent records are append-only and cannot be edited.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Consent records are append-only and cannot be deleted.")


def current_consent_state(user):
    """Return each consent purpose's most recent recorded grant state."""
    state = {}
    records = ConsentRecord.objects.filter(user=user).order_by(
        "consent_type", "-captured_at", "-id"
    )
    for record in records:
        state.setdefault(record.consent_type, record.granted)
    return state


def record_consent(*, user, consent_type, policy_version, granted, source=ConsentSource.WEB):
    """Append a consent event while serializing updates for the account."""
    if not policy_version or len(policy_version) > 30:
        raise ValueError("A policy version of 1 to 30 characters is required.")
    with transaction.atomic():
        # Locking the owning account serializes state changes even when no consent row exists yet.
        user.__class__.objects.select_for_update().get(pk=user.pk)
        latest = (
            ConsentRecord.objects.filter(user=user, consent_type=consent_type)
            .order_by("-captured_at", "-id")
            .first()
        )
        if latest and latest.granted == granted and latest.policy_version == policy_version:
            return latest, False
        now = timezone.now()
        was_granted = bool(latest and latest.granted)
        record = ConsentRecord.objects.create(
            user=user,
            consent_type=consent_type,
            policy_version=policy_version,
            granted=granted,
            captured_at=now,
            withdrawn_at=now if was_granted and not granted else None,
            source=source,
        )
        return record, True
