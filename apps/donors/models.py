"""Self-reported donor profile data, separate from account identity."""

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import OuterRef, Q, Subquery
from django.utils import timezone

from apps.accounts.models import AccountStatus
from apps.locations.models import Location, LocationLevel


class DonorProfileQuerySet(models.QuerySet):
    def discoverable(self):
        """Return profiles meeting current visibility, availability and consent gates."""
        from apps.governance.models import ConsentRecord, ConsentType

        latest_discovery_consent = (
            ConsentRecord.objects.filter(
                user_id=OuterRef("user_id"),
                consent_type=ConsentType.DONOR_DISCOVERY,
            )
            .order_by("-captured_at", "-id")
            .values("granted")[:1]
        )
        return (
            self.filter(
                user__account_status=AccountStatus.ACTIVE,
                profile_status=DonorProfileStatus.ACTIVE,
                availability_status=AvailabilityStatus.AVAILABLE,
                visibility_enabled=True,
                division__is_active=True,
                district__is_active=True,
            )
            .filter(Q(upazila__isnull=True) | Q(upazila__is_active=True))
            .annotate(current_discovery_consent=Subquery(latest_discovery_consent))
            .filter(current_discovery_consent=True)
        )


class BloodGroup(models.TextChoices):
    A_POSITIVE = "A+", "A+"
    A_NEGATIVE = "A-", "A-"
    B_POSITIVE = "B+", "B+"
    B_NEGATIVE = "B-", "B-"
    AB_POSITIVE = "AB+", "AB+"
    AB_NEGATIVE = "AB-", "AB-"
    O_POSITIVE = "O+", "O+"
    O_NEGATIVE = "O-", "O-"


class AvailabilityStatus(models.TextChoices):
    UNAVAILABLE = "UNAVAILABLE", "Unavailable"
    AVAILABLE = "AVAILABLE", "Available"
    PAUSED = "PAUSED", "Paused"


class PreferredContactMethod(models.TextChoices):
    IN_APP = "IN_APP", "In app"
    PHONE_AFTER_ACCEPT = "PHONE_AFTER_ACCEPT", "Phone after acceptance"
    EMAIL_AFTER_ACCEPT = "EMAIL_AFTER_ACCEPT", "Email after acceptance"


class DonorProfileStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    ACTIVE = "ACTIVE", "Active"
    HIDDEN = "HIDDEN", "Hidden"
    SUSPENDED = "SUSPENDED", "Suspended"


class DonorProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="donor_profile",
    )
    blood_group = models.CharField(max_length=3, choices=BloodGroup.choices)
    division = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        related_name="donor_profiles_by_division",
    )
    district = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        related_name="donor_profiles_by_district",
    )
    upazila = models.ForeignKey(
        Location,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="donor_profiles_by_upazila",
    )
    availability_status = models.CharField(
        max_length=20,
        choices=AvailabilityStatus.choices,
        default=AvailabilityStatus.UNAVAILABLE,
    )
    public_alias = models.CharField(max_length=80, null=True, blank=True)
    visibility_enabled = models.BooleanField(default=False)
    preferred_contact_method = models.CharField(
        max_length=20,
        choices=PreferredContactMethod.choices,
        default=PreferredContactMethod.IN_APP,
    )
    share_phone_after_accept = models.BooleanField(default=False)
    share_email_after_accept = models.BooleanField(default=False)
    last_donation_date = models.DateField(null=True, blank=True)
    profile_status = models.CharField(
        max_length=20,
        choices=DonorProfileStatus.choices,
        default=DonorProfileStatus.DRAFT,
    )
    availability_updated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    objects = DonorProfileQuerySet.as_manager()

    class Meta:
        indexes = [
            models.Index(fields=["blood_group", "availability_status", "profile_status"]),
            models.Index(fields=["district", "blood_group", "availability_status"]),
            models.Index(fields=["upazila", "blood_group", "availability_status"]),
            models.Index(fields=["visibility_enabled", "profile_status"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(blood_group__in=BloodGroup.values),
                name="donors_blood_group_valid",
            ),
            models.CheckConstraint(
                condition=Q(availability_status__in=AvailabilityStatus.values),
                name="donors_availability_valid",
            ),
            models.CheckConstraint(
                condition=Q(preferred_contact_method__in=PreferredContactMethod.values),
                name="donors_contact_method_valid",
            ),
            models.CheckConstraint(
                condition=Q(profile_status__in=DonorProfileStatus.values),
                name="donors_profile_status_valid",
            ),
        ]

    def clean(self):
        errors = {}
        if self.division_id and self.division.level != LocationLevel.DIVISION:
            errors["division"] = "Select a division-level location."
        if self.district_id:
            if self.district.level != LocationLevel.DISTRICT:
                errors["district"] = "Select a district-level location."
            elif self.division_id and self.district.parent_id != self.division_id:
                errors["district"] = "The district must belong to the selected division."
        if self.upazila_id:
            if self.upazila.level != LocationLevel.UPAZILA:
                errors["upazila"] = "Select an upazila-level location."
            elif self.district_id and self.upazila.parent_id != self.district_id:
                errors["upazila"] = "The upazila must belong to the selected district."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.public_alias or self.user.display_name
