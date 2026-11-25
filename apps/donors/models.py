"""Self-reported donor profile data, separate from account identity."""

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import F, OuterRef, Q, Subquery
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
                division__level=LocationLevel.DIVISION,
                division__is_active=True,
                district__level=LocationLevel.DISTRICT,
                district__is_active=True,
                district__parent_id=F("division_id"),
                district__parent__level=LocationLevel.DIVISION,
                district__parent__is_active=True,
            )
            .filter(
                Q(upazila__isnull=True)
                | Q(
                    upazila__level=LocationLevel.UPAZILA,
                    upazila__is_active=True,
                    upazila__parent_id=F("district_id"),
                    upazila__parent__level=LocationLevel.DISTRICT,
                    upazila__parent__is_active=True,
                    upazila__parent__parent__level=LocationLevel.DIVISION,
                    upazila__parent__parent__is_active=True,
                )
            )
            .filter(
                Q(union__isnull=True)
                | Q(
                    union__level=LocationLevel.UNION,
                    union__is_active=True,
                    union__parent_id=F("upazila_id"),
                    union__parent__level=LocationLevel.UPAZILA,
                    union__parent__is_active=True,
                    union__parent__parent__is_active=True,
                    union__parent__parent__parent__is_active=True,
                )
            )
            .filter(
                Q(city_corporation__isnull=True)
                | Q(
                    city_corporation__level=LocationLevel.CITY_CORPORATION,
                    city_corporation__is_active=True,
                    city_corporation__parent_id=F("district_id"),
                    city_corporation__parent__is_active=True,
                    city_corporation__parent__parent_id=F("division_id"),
                    city_corporation__parent__parent__is_active=True,
                )
            )
            .filter(
                Q(city_corporation__isnull=False)
                | Q(city_zone__isnull=True, ward__isnull=True)
            )
            .filter(
                Q(city_zone__isnull=True)
                | Q(
                    city_zone__level=LocationLevel.ZONE,
                    city_zone__is_active=True,
                    city_zone__parent_id=F("city_corporation_id"),
                    city_zone__parent__is_active=True,
                    city_zone__parent__parent_id=F("district_id"),
                    city_zone__parent__parent__parent_id=F("division_id"),
                    city_zone__parent__parent__parent__is_active=True,
                )
            )
            .filter(
                Q(ward__isnull=True)
                | (
                    Q(
                        ward__level=LocationLevel.WARD,
                        ward__is_active=True,
                        ward__corporation_scope_id=F("city_corporation_id"),
                        ward__parent__is_active=True,
                        ward__parent__parent__is_active=True,
                    )
                    & (
                        Q(
                            city_zone__isnull=False,
                            ward__parent_id=F("city_zone_id"),
                            ward__parent__parent__is_active=True,
                            ward__parent__parent__parent__is_active=True,
                            ward__parent__parent__parent__parent__is_active=True,
                        )
                        | Q(
                            city_zone__isnull=True,
                            ward__parent_id=F("city_corporation_id"),
                            ward__parent__parent__is_active=True,
                            ward__parent__parent__parent__is_active=True,
                        )
                        | Q(
                            city_zone__isnull=True,
                            ward__parent__parent_id=F("city_corporation_id"),
                            ward__parent__is_active=True,
                            ward__parent__parent__is_active=True,
                            ward__parent__parent__parent__is_active=True,
                            ward__parent__parent__parent__parent__is_active=True,
                        )
                    )
                )
            )
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


class DonorAreaLocationSource(models.TextChoices):
    GOOGLE_PLACE = "GOOGLE_PLACE", "Google place"
    GOOGLE_GEOCODE = "GOOGLE_GEOCODE", "Google geocode"
    MAP_PIN = "MAP_PIN", "Map pin"


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
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="donor_profiles_by_division",
    )
    district = models.ForeignKey(
        Location,
        null=True,
        blank=True,
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
    union = models.ForeignKey(
        Location,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="donor_profiles_by_union",
    )
    city_corporation = models.ForeignKey(
        Location,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="donor_profiles_by_city_corporation",
    )
    city_zone = models.ForeignKey(
        Location,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="donor_profiles_by_city_zone",
    )
    ward = models.ForeignKey(
        Location,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="donor_profiles_by_ward",
    )
    thana_name = models.CharField(
        max_length=120,
        blank=True,
        help_text="Optional self-reported thana; not an official verified area or search filter.",
    )
    donation_area_label = models.CharField(max_length=180, blank=True, default="")
    donation_area_latitude = models.DecimalField(
        max_digits=11,
        decimal_places=8,
        null=True,
        blank=True,
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
    )
    donation_area_longitude = models.DecimalField(
        max_digits=11,
        decimal_places=8,
        null=True,
        blank=True,
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
    )
    google_place_id = models.CharField(max_length=256, blank=True, default="")
    location_source = models.CharField(
        max_length=20,
        choices=DonorAreaLocationSource.choices,
        blank=True,
        default="",
    )
    location_confirmed_at = models.DateTimeField(null=True, blank=True)
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
            models.Index(fields=["city_corporation", "ward", "blood_group"]),
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
            models.CheckConstraint(
                condition=(
                    Q(donation_area_latitude__isnull=True, donation_area_longitude__isnull=True)
                    | Q(
                        donation_area_latitude__gte=-90,
                        donation_area_latitude__lte=90,
                        donation_area_longitude__gte=-180,
                        donation_area_longitude__lte=180,
                    )
                ),
                name="donors_area_coordinates_in_range",
            ),
            models.CheckConstraint(
                condition=(
                    (
                        Q(donation_area_latitude__isnull=True, donation_area_longitude__isnull=True)
                        & Q(
                            donation_area_label="",
                            google_place_id="",
                            location_source="",
                            location_confirmed_at__isnull=True,
                        )
                    )
                    | (
                        Q(
                            donation_area_latitude__isnull=False,
                            donation_area_longitude__isnull=False,
                        )
                        & Q(donation_area_label__gt="")
                        & Q(location_source__in=DonorAreaLocationSource.values)
                        & Q(location_confirmed_at__isnull=False)
                    )
                ),
                name="donors_area_location_consistent",
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
        if self.union_id:
            if self.union.level != LocationLevel.UNION:
                errors["union"] = "Select a union-level location."
            elif not self.upazila_id or self.union.parent_id != self.upazila_id:
                errors["union"] = "The union must belong to the selected upazila."
        city_fields = (self.city_corporation_id, self.city_zone_id, self.ward_id)
        if any(city_fields) and (self.upazila_id or self.union_id):
            errors["city_corporation"] = "Select either a rural upazila/union or a city-corporation area."
        if self.city_corporation_id:
            if self.city_corporation.level != LocationLevel.CITY_CORPORATION:
                errors["city_corporation"] = "Select a city corporation."
            elif self.city_corporation.parent_id != self.district_id:
                errors["city_corporation"] = "The city corporation must belong to the selected district."
        if self.city_zone_id:
            if self.city_zone.level != LocationLevel.ZONE:
                errors["city_zone"] = "Select a city corporation zone."
            elif not self.city_corporation_id or self.city_zone.parent_id != self.city_corporation_id:
                errors["city_zone"] = "The zone must belong to the selected city corporation."
        if self.ward_id:
            if self.ward.level != LocationLevel.WARD:
                errors["ward"] = "Select a ward."
            elif not self.city_corporation_id:
                errors["ward"] = "Select a city corporation for this ward."
            elif self.city_zone_id:
                if self.ward.parent_id != self.city_zone_id:
                    errors["ward"] = "The ward must belong to the selected zone."
            elif self.ward.parent_id != self.city_corporation_id and self.ward.parent.parent_id != self.city_corporation_id:
                errors["ward"] = "The ward must belong to the selected city corporation."
        has_latitude = self.donation_area_latitude is not None
        has_longitude = self.donation_area_longitude is not None
        if has_latitude != has_longitude:
            errors["donation_area_latitude"] = "Provide both donation-area coordinates."
        elif has_latitude:
            if not self.donation_area_label:
                errors["donation_area_label"] = "Confirm a general donation-area label."
            if self.location_source not in DonorAreaLocationSource.values:
                errors["location_source"] = "Select a valid donation-area source."
            if not self.location_confirmed_at:
                errors["donation_area_label"] = "Confirm the donation area before saving."
        elif (
            self.donation_area_label
            or self.google_place_id
            or self.location_source
            or self.location_confirmed_at
        ):
            errors["donation_area_label"] = "Clear all donation-area details when no point is saved."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.public_alias or self.user.display_name
