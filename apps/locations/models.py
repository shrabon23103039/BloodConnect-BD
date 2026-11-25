"""Versioned Bangladesh administrative location hierarchy."""

import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.db.models.functions import Lower


class LocationLevel(models.TextChoices):
    DIVISION = "DIVISION", "Division"
    DISTRICT = "DISTRICT", "District"
    UPAZILA = "UPAZILA", "Upazila"
    UNION = "UNION", "Union"
    CITY_CORPORATION = "CITY_CORPORATION", "City corporation"
    ZONE = "ZONE", "City corporation zone"
    WARD = "WARD", "Ward"


class Location(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name_en = models.CharField(max_length=120)
    name_bn = models.CharField(max_length=120, null=True, blank=True)
    level = models.CharField(max_length=20, choices=LocationLevel.choices)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="children",
    )
    corporation_scope = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="scoped_wards",
        help_text="City corporation scope for a ward; required only for ward rows.",
    )
    source_name = models.CharField(max_length=120)
    source_version = models.CharField(max_length=60)
    source_id = models.CharField(max_length=32, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [models.Index(fields=["level", "parent", "is_active"])]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(level=LocationLevel.DIVISION, parent__isnull=True)
                    | Q(level__in=[level for level in LocationLevel.values if level != LocationLevel.DIVISION], parent__isnull=False)
                ),
                name="locations_level_parent_shape",
            ),
            models.CheckConstraint(
                condition=~Q(name_en=""),
                name="locations_name_en_nonempty",
            ),
            models.CheckConstraint(
                condition=~Q(source_name="") & ~Q(source_version=""),
                name="locations_source_metadata_nonempty",
            ),
            models.UniqueConstraint(
                Lower("name_en"),
                F("level"),
                condition=Q(parent__isnull=True),
                name="locations_root_name_level_uniq",
            ),
            models.UniqueConstraint(
                Lower("name_en"),
                F("level"),
                F("parent"),
                condition=Q(parent__isnull=False),
                name="locations_child_name_level_parent_uniq",
            ),
            models.UniqueConstraint(
                fields=["source_name", "source_id"],
                condition=Q(source_id__isnull=False),
                name="locations_source_id_uniq",
            ),
            models.UniqueConstraint(
                Lower("name_en"),
                "corporation_scope",
                condition=Q(level=LocationLevel.WARD),
                name="locations_ward_name_corporation_uniq",
            ),
            models.CheckConstraint(
                condition=(
                    Q(level=LocationLevel.WARD, corporation_scope__isnull=False)
                    | (~Q(level=LocationLevel.WARD) & Q(corporation_scope__isnull=True))
                ),
                name="locations_ward_scope_shape",
            ),
        ]

    def clean(self):
        self.name_en = self.name_en.strip()
        self.name_bn = self.name_bn.strip() if self.name_bn else None
        if self.level not in LocationLevel.values:
            raise ValidationError({"level": "Select a supported administrative level."})
        allowed_parent_levels = {
            LocationLevel.DIVISION: set(),
            LocationLevel.DISTRICT: {LocationLevel.DIVISION},
            LocationLevel.UPAZILA: {LocationLevel.DISTRICT},
            LocationLevel.UNION: {LocationLevel.UPAZILA},
            LocationLevel.CITY_CORPORATION: {LocationLevel.DISTRICT},
            LocationLevel.ZONE: {LocationLevel.CITY_CORPORATION},
            # Some corporations publish zones; others may publish wards directly.
            LocationLevel.WARD: {LocationLevel.CITY_CORPORATION, LocationLevel.ZONE},
        }
        expected = allowed_parent_levels[self.level]
        if not expected and self.parent_id is not None:
            raise ValidationError({"parent": "A division cannot have a parent."})
        if expected and self.parent_id is None:
            raise ValidationError({"parent": f"A {self.level.lower()} requires a parent."})
        if self.parent_id and self.parent.level not in expected:
            expected_labels = ", ".join(sorted(level.lower() for level in expected))
            raise ValidationError({"parent": f"A {self.level.lower()} must belong to {expected_labels}."})
        if self.level in {LocationLevel.UNION, LocationLevel.CITY_CORPORATION}:
            if not self.parent.is_active and self.is_active:
                raise ValidationError({"parent": "An active location must have an active parent."})
        if self.level == LocationLevel.CITY_CORPORATION and self.is_active:
            if self.parent.parent.level != LocationLevel.DIVISION or not self.parent.parent.is_active:
                raise ValidationError({"parent": "An active city corporation requires an active division ancestor."})
        if self.level in {LocationLevel.ZONE, LocationLevel.WARD}:
            corporation = self.parent if self.parent.level == LocationLevel.CITY_CORPORATION else self.parent.parent
            if corporation and corporation.parent_id:
                if corporation.parent.level != LocationLevel.DISTRICT:
                    raise ValidationError({"parent": "City locations must be nested under a district."})
                if self.is_active and (not corporation.is_active or not corporation.parent.is_active or not corporation.parent.parent.is_active):
                    raise ValidationError({"parent": "An active city location requires active ancestors."})
            if self.level == LocationLevel.WARD:
                if self.corporation_scope_id != corporation.pk:
                    raise ValidationError({"corporation_scope": "A ward must be scoped to its city corporation."})
        elif self.corporation_scope_id is not None:
            raise ValidationError({"corporation_scope": "Only a ward has a city corporation scope."})
        if self.level == LocationLevel.UNION and self.is_active:
            upazila = self.parent
            if not upazila.is_active or not upazila.parent.is_active or not upazila.parent.parent.is_active:
                raise ValidationError({"parent": "An active union requires active ancestors."})
        if self.is_active and self.parent_id and not self.parent.is_active:
            raise ValidationError({"parent": "An active location must have an active parent."})
        if not self.source_name.strip() or not self.source_version.strip():
            raise ValidationError("Source name and source version are required.")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.name_en
