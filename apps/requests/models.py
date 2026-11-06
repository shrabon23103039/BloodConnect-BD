"""Requester-owned blood request coordination records."""

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.utils import timezone

from apps.donors.models import BloodGroup
from apps.locations.models import Location, LocationLevel


class RequestUrgency(models.TextChoices):
    NORMAL = "NORMAL", "Normal"
    URGENT = "URGENT", "Urgent"


class BloodRequestStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    OPEN = "OPEN", "Open"
    FULFILLED = "FULFILLED", "Fulfilled"
    CANCELLED = "CANCELLED", "Cancelled"
    EXPIRED = "EXPIRED", "Expired"


class BloodRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="blood_requests",
    )
    blood_group = models.CharField(max_length=3, choices=BloodGroup.choices)
    units_requested = models.PositiveSmallIntegerField()
    required_at = models.DateTimeField()
    division = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        related_name="blood_requests_by_division",
    )
    district = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        related_name="blood_requests_by_district",
    )
    upazila = models.ForeignKey(
        Location,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="blood_requests_by_upazila",
    )
    facility_name = models.CharField(max_length=180, null=True, blank=True)
    facility_address = models.CharField(max_length=300, null=True, blank=True)
    urgency = models.CharField(max_length=20, choices=RequestUrgency.choices)
    description = models.CharField(max_length=1000, null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=BloodRequestStatus.choices,
        default=BloodRequestStatus.DRAFT,
    )
    public_listing_enabled = models.BooleanField(default=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "requests_bloodrequest"
        indexes = [
            models.Index(
                fields=["status", "blood_group", "district", "required_at"],
                name="requests_search_idx",
            ),
            models.Index(
                fields=["requester", "status", "-created_at"],
                name="requests_owner_idx",
            ),
            models.Index(fields=["expires_at", "status"], name="requests_expiry_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(blood_group__in=BloodGroup.values),
                name="requests_blood_group_valid",
            ),
            models.CheckConstraint(
                condition=Q(units_requested__gt=0),
                name="requests_units_positive",
            ),
            models.CheckConstraint(
                condition=Q(urgency__in=RequestUrgency.values),
                name="requests_urgency_valid",
            ),
            models.CheckConstraint(
                condition=Q(status__in=BloodRequestStatus.values),
                name="requests_status_valid",
            ),
            models.CheckConstraint(
                condition=Q(expires_at__gt=F("created_at")),
                name="requests_expiry_after_create",
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
        return f"{self.blood_group} request in {self.district}"
