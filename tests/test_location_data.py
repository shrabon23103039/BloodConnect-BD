import json
import tempfile
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from apps.locations.models import Location, LocationLevel


def snapshot(records):
    return {
        "source": {
            "name": "Synthetic test fixture",
            "version": "synthetic-v1",
            "url": "https://example.test/location-fixture.json",
            "reviewed_by": "Test suite",
            "reviewed_at": "2026-11-06",
        },
        "records": records,
    }


def sample_records():
    return [
        {
            "name_en": "Dhaka",
            "name_bn": "ঢাকা",
            "level": "DIVISION",
            "parent_path": [],
        },
        {
            "name_en": "Dhaka",
            "name_bn": "ঢাকা",
            "level": "DISTRICT",
            "parent_path": ["Dhaka"],
        },
        {
            "name_en": "Dhamrai",
            "name_bn": "ধামরাই",
            "level": "UPAZILA",
            "parent_path": ["Dhaka", "Dhaka"],
        },
    ]


class LocationModelTests(TestCase):
    def test_model_enforces_division_district_upazila_parent_levels(self):
        division = Location.objects.create(
            name_en="Dhaka",
            level=LocationLevel.DIVISION,
            source_name="Synthetic test fixture",
            source_version="synthetic-v1",
        )
        district = Location.objects.create(
            name_en="Dhaka",
            level=LocationLevel.DISTRICT,
            parent=division,
            source_name="Synthetic test fixture",
            source_version="synthetic-v1",
        )
        wrong_parent = Location(
            name_en="Wrong",
            level=LocationLevel.UPAZILA,
            parent=division,
            source_name="Synthetic test fixture",
            source_version="synthetic-v1",
        )
        with self.assertRaises(ValidationError):
            wrong_parent.save()
        self.assertEqual(district.children.count(), 0)

    def test_names_are_case_insensitively_unique_at_the_same_level_and_parent(self):
        Location.objects.create(
            name_en="Dhaka",
            level=LocationLevel.DIVISION,
            source_name="Synthetic test fixture",
            source_version="synthetic-v1",
        )
        duplicate = Location(
            name_en="DHAKA",
            level=LocationLevel.DIVISION,
            source_name="Synthetic test fixture",
            source_version="synthetic-v1",
        )
        with self.assertRaises(ValidationError):
            duplicate.save()


class LocationImportTests(TestCase):
    def import_snapshot(self, document, *, reviewed=True):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "locations.json"
            path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
            args = ["load_locations", "--file", str(path)]
            if reviewed:
                args.append("--reviewed")
            call_command(*args)

    def test_import_is_provenance_labeled_and_idempotent(self):
        self.import_snapshot(snapshot(sample_records()))
        self.assertEqual(Location.objects.count(), 3)
        upazila = Location.objects.get(level=LocationLevel.UPAZILA)
        self.assertEqual(upazila.parent.name_en, "Dhaka")
        self.assertEqual(upazila.name_bn, "ধামরাই")
        self.assertEqual(upazila.source_name, "Synthetic test fixture")
        self.assertEqual(upazila.source_version, "synthetic-v1")

        self.import_snapshot(snapshot(sample_records()))
        self.assertEqual(Location.objects.count(), 3)

    def test_import_requires_explicit_review_confirmation(self):
        with self.assertRaisesMessage(CommandError, "--reviewed"):
            self.import_snapshot(snapshot(sample_records()), reviewed=False)
        self.assertFalse(Location.objects.exists())

    def test_import_rejects_missing_parent_and_wrong_hierarchy(self):
        missing_parent = sample_records()[1:]
        with self.assertRaisesMessage(CommandError, "missing or appears later"):
            self.import_snapshot(snapshot(missing_parent))
        self.assertFalse(Location.objects.exists())

        wrong_level = sample_records()
        wrong_level[2]["parent_path"] = ["Dhaka"]
        with self.assertRaisesMessage(CommandError, "invalid parent path"):
            self.import_snapshot(snapshot(wrong_level))
        self.assertFalse(Location.objects.exists())

    def test_import_requires_review_and_provenance_metadata(self):
        document = snapshot(sample_records())
        del document["source"]["version"]
        with self.assertRaisesMessage(CommandError, "Source name, version"):
            self.import_snapshot(document)
        self.assertFalse(Location.objects.exists())
