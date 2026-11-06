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
    source_name = models.CharField(max_length=120)
    source_version = models.CharField(max_length=60)
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [models.Index(fields=["level", "parent", "is_active"])]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(level=LocationLevel.DIVISION, parent__isnull=True)
                    | Q(
                        level__in=[LocationLevel.DISTRICT, LocationLevel.UPAZILA],
                        parent__isnull=False,
                    )
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
        ]

    def clean(self):
        self.name_en = self.name_en.strip()
        self.name_bn = self.name_bn.strip() if self.name_bn else None
        expected_parent_level = {
            LocationLevel.DIVISION: None,
            LocationLevel.DISTRICT: LocationLevel.DIVISION,
            LocationLevel.UPAZILA: LocationLevel.DISTRICT,
        }.get(self.level)
        if self.level not in LocationLevel.values:
            raise ValidationError({"level": "Select a supported administrative level."})
        if expected_parent_level is None and self.parent_id is not None:
            raise ValidationError({"parent": "A division cannot have a parent."})
        if expected_parent_level and self.parent_id is None:
            raise ValidationError({"parent": "Districts and upazilas require a parent."})
        if self.parent_id and self.parent.level != expected_parent_level:
            raise ValidationError({"parent": f"A {self.level.lower()} must belong to a {expected_parent_level.lower()}."})
        if self.is_active and self.parent_id and not self.parent.is_active:
            raise ValidationError({"parent": "An active location must have an active parent."})
        if not self.source_name.strip() or not self.source_version.strip():
            raise ValidationError("Source name and source version are required.")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.name_en
