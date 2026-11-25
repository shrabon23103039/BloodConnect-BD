import io
import json
import tempfile
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.urls import resolve, reverse
from django.utils import timezone

from apps.accounts.models import AccountStatus, User
from apps.donors.models import AvailabilityStatus, BloodGroup, DonorProfile
from apps.donors.forms import DonorProfileForm
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
            "source_id": "SYN-DIV-01",
            "name_en": "Test Division A",
            "name_bn": "পরীক্ষা বিভাগ ক",
            "level": "DIVISION",
            "parent_path": [],
        },
        {
            "source_id": "SYN-DIST-01",
            "name_en": "Test District A",
            "name_bn": "পরীক্ষা জেলা ক",
            "level": "DISTRICT",
            "parent_path": ["Test Division A"],
        },
        {
            "source_id": "SYN-UPA-01",
            "name_en": "Test Upazila A",
            "name_bn": "পরীক্ষা উপজেলা ক",
            "level": "UPAZILA",
            "parent_path": ["Test Division A", "Test District A"],
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

    def test_city_hierarchy_and_ward_names_are_scoped_to_corporation(self):
        division = Location.objects.create(
            name_en="Synthetic Dhaka Division", level=LocationLevel.DIVISION,
            source_name="Synthetic fixture", source_version="test",
        )
        district = Location.objects.create(
            name_en="Synthetic Dhaka District", level=LocationLevel.DISTRICT,
            parent=division, source_name="Synthetic fixture", source_version="test",
        )
        north = Location.objects.create(
            name_en="Synthetic DNCC", level=LocationLevel.CITY_CORPORATION,
            parent=district, source_name="Synthetic fixture", source_version="test",
        )
        south = Location.objects.create(
            name_en="Synthetic DSCC", level=LocationLevel.CITY_CORPORATION,
            parent=district, source_name="Synthetic fixture", source_version="test",
        )
        north_zone = Location.objects.create(
            name_en="Synthetic North Zone", level=LocationLevel.ZONE,
            parent=north, source_name="Synthetic fixture", source_version="test",
        )
        north_zone_2 = Location.objects.create(
            name_en="Synthetic North Zone 2", level=LocationLevel.ZONE,
            parent=north, source_name="Synthetic fixture", source_version="test",
        )
        south_zone = Location.objects.create(
            name_en="Synthetic South Zone", level=LocationLevel.ZONE,
            parent=south, source_name="Synthetic fixture", source_version="test",
        )
        Location.objects.create(
            name_en="Ward 1", level=LocationLevel.WARD, parent=north_zone,
            corporation_scope=north, source_name="Synthetic fixture", source_version="test",
        )
        Location.objects.create(
            name_en="Ward 1", level=LocationLevel.WARD, parent=south_zone,
            corporation_scope=south, source_name="Synthetic fixture", source_version="test",
        )
        with self.assertRaises(ValidationError):
            Location.objects.create(
                name_en="Ward 1", level=LocationLevel.WARD, parent=north_zone_2,
                corporation_scope=north, source_name="Synthetic fixture", source_version="test",
            )
        wrong_parent = Location(
            name_en="Bad city ward", level=LocationLevel.WARD, parent=district,
            corporation_scope=north, source_name="Synthetic fixture", source_version="test",
        )
        with self.assertRaises(ValidationError):
            wrong_parent.save()

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
    def import_snapshot(self, document, *, reviewed=True, activate=False):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "locations.json"
            path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
            args = ["load_locations", "--file", str(path)]
            if reviewed:
                args.append("--reviewed")
            if activate:
                args.append("--activate")
            call_command(*args)

    def test_import_is_provenance_labeled_and_idempotent(self):
        self.import_snapshot(snapshot(sample_records()))
        self.assertEqual(Location.objects.count(), 3)
        self.assertEqual(Location.objects.filter(is_active=True).count(), 0)
        Location.objects.update(is_active=False)
        self.import_snapshot(snapshot(sample_records()))
        self.assertEqual(Location.objects.filter(is_active=True).count(), 0)
        upazila = Location.objects.get(level=LocationLevel.UPAZILA)
        self.assertEqual(upazila.parent.name_en, "Test District A")
        self.assertEqual(upazila.name_bn, "পরীক্ষা উপজেলা ক")
        self.assertEqual(upazila.source_name, "Synthetic test fixture")
        self.assertEqual(upazila.source_version, "synthetic-v1")
        self.assertEqual(upazila.source_id, "SYN-UPA-01")

        self.import_snapshot(snapshot(sample_records()))
        self.assertEqual(Location.objects.count(), 3)

    def test_import_activates_only_with_explicit_flag(self):
        self.import_snapshot(snapshot(sample_records()), activate=True)
        self.assertEqual(Location.objects.filter(is_active=True).count(), 3)

    def test_import_supports_synthetic_city_hierarchy_without_activating_it(self):
        records = [
            {"source_id": "CITY-DIV", "name_en": "Synthetic Division", "level": "DIVISION", "parent_path": []},
            {"source_id": "CITY-DIST", "name_en": "Synthetic Dhaka District", "level": "DISTRICT", "parent_path": ["Synthetic Division"]},
            {"source_id": "CITY-CORP", "name_en": "Synthetic DNCC", "level": "CITY_CORPORATION", "parent_path": ["Synthetic Division", "Synthetic Dhaka District"]},
            {"source_id": "CITY-ZONE", "name_en": "Synthetic Zone 1", "level": "ZONE", "parent_path": ["Synthetic Division", "Synthetic Dhaka District", "Synthetic DNCC"]},
            {"source_id": "CITY-WARD", "name_en": "Ward 1", "level": "WARD", "parent_path": ["Synthetic Division", "Synthetic Dhaka District", "Synthetic DNCC", "Synthetic Zone 1"]},
        ]
        self.import_snapshot(snapshot(records))
        ward = Location.objects.get(level=LocationLevel.WARD)
        self.assertEqual(ward.corporation_scope.name_en, "Synthetic DNCC")
        self.assertFalse(ward.is_active)
        self.import_snapshot(snapshot(records))
        self.assertEqual(Location.objects.filter(level=LocationLevel.WARD).count(), 1)

    def test_import_rejects_name_match_from_a_different_source(self):
        existing = Location.objects.create(
            name_en="Test Division A",
            level=LocationLevel.DIVISION,
            source_name="Previously reviewed source",
            source_version="old-v1",
            source_id="OLD-DIV-01",
        )
        document = snapshot([sample_records()[0]])
        document["source"]["name"] = "New synthetic source"

        with self.assertRaisesMessage(CommandError, "cannot be matched by name"):
            self.import_snapshot(document)

        existing.refresh_from_db()
        self.assertEqual(Location.objects.count(), 1)
        self.assertEqual(existing.source_name, "Previously reviewed source")
        self.assertEqual(existing.source_version, "old-v1")
        self.assertEqual(existing.source_id, "OLD-DIV-01")

    def test_import_rejects_replacing_an_existing_source_id(self):
        existing = Location.objects.create(
            name_en="Test Division A",
            level=LocationLevel.DIVISION,
            source_name="Synthetic test fixture",
            source_version="synthetic-v0",
            source_id="SYN-DIV-OLD",
        )

        with self.assertRaisesMessage(CommandError, "cannot be matched by name"):
            self.import_snapshot(snapshot([sample_records()[0]]))

        existing.refresh_from_db()
        self.assertEqual(Location.objects.count(), 1)
        self.assertEqual(existing.source_id, "SYN-DIV-OLD")
        self.assertEqual(existing.source_version, "synthetic-v0")

    def test_same_source_identity_allows_metadata_update_without_replacing_id(self):
        records = sample_records()
        self.import_snapshot(snapshot(records))
        division = Location.objects.get(source_id="SYN-DIV-01")
        original_pk = division.pk

        updated_document = snapshot(records)
        updated_document["source"]["version"] = "synthetic-v2"
        updated_document["records"][0]["name_bn"] = "পরীক্ষিত বিভাগ ক"
        self.import_snapshot(updated_document)

        division.refresh_from_db()
        self.assertEqual(division.pk, original_pk)
        self.assertEqual(division.source_name, "Synthetic test fixture")
        self.assertEqual(division.source_id, "SYN-DIV-01")
        self.assertEqual(division.source_version, "synthetic-v2")
        self.assertEqual(division.name_bn, "পরীক্ষিত বিভাগ ক")
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
        wrong_level[2]["parent_path"] = ["Test Division A"]
        with self.assertRaisesMessage(CommandError, "wrong level"):
            self.import_snapshot(snapshot(wrong_level))
        self.assertFalse(Location.objects.exists())

    def test_import_requires_review_and_provenance_metadata(self):
        document = snapshot(sample_records())
        del document["source"]["version"]
        with self.assertRaisesMessage(CommandError, "Source name, version"):
            self.import_snapshot(document)
        self.assertFalse(Location.objects.exists())


class LocationDropdownEndpointTests(TestCase):
    def setUp(self):
        self.division = Location.objects.create(
            name_en="Synthetic Division", level=LocationLevel.DIVISION,
            source_name="Synthetic", source_version="test",
        )
        self.district = Location.objects.create(
            name_en="Synthetic District", level=LocationLevel.DISTRICT,
            parent=self.division, source_name="Synthetic", source_version="test",
        )
        self.upazila = Location.objects.create(
            name_en="Synthetic Upazila", level=LocationLevel.UPAZILA,
            parent=self.district, source_name="Synthetic", source_version="test",
        )

    def test_options_endpoint_returns_only_active_correct_hierarchy(self):
        response = self.client.get(reverse("locations:child_options", args=[LocationLevel.DISTRICT]), {
            "parent": str(self.division.pk),
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("no-store", response["Cache-Control"])
        self.assertEqual([item["id"] for item in response.json()["results"]], [str(self.district.pk)])
        self.assertEqual(set(response.json()["results"][0]), {"id", "name_en"})
        response = self.client.get(reverse("locations:child_options", args=[LocationLevel.UPAZILA]), {
            "parent": str(self.district.pk),
        })
        self.assertEqual([item["id"] for item in response.json()["results"]], [str(self.upazila.pk)])
        union = Location.objects.create(
            name_en="Synthetic Union", level=LocationLevel.UNION,
            parent=self.upazila, source_name="Synthetic", source_version="test",
        )
        response = self.client.get(
            reverse("locations:child_options", args=[LocationLevel.UNION]),
            {"parent": str(self.upazila.pk)},
        )
        self.assertEqual([item["id"] for item in response.json()["results"]], [str(union.pk)])

    def test_location_options_route_is_public_and_returns_only_active_public_fields(self):
        inactive_district = Location.objects.create(
            name_en="Inactive Synthetic District",
            level=LocationLevel.DISTRICT,
            parent=self.division,
            source_name="Synthetic",
            source_version="test",
            is_active=False,
        )
        url = reverse("locations:child_options", args=[LocationLevel.DISTRICT])
        self.assertEqual(resolve(url).view_name, "locations:child_options")

        anonymous_response = self.client.get(url, {"parent": str(self.division.pk)})
        self.assertEqual(anonymous_response.status_code, 200)
        public_rows = anonymous_response.json()["results"]
        self.assertEqual(public_rows, [{"id": str(self.district.pk), "name_en": self.district.name_en}])
        self.assertNotIn(str(inactive_district.pk), {row["id"] for row in public_rows})
        self.assertEqual(set(public_rows[0]), {"id", "name_en"})
        self.assertFalse(
            {"latitude", "longitude", "coordinates", "place_id", "source_id", "corporation_scope"}
            & set(public_rows[0])
        )

        authenticated_user = User.objects.create_user(
            email="location-options@example.test",
            password="safe-test-pass",
            display_name="Synthetic Location User",
        )
        self.client.force_login(authenticated_user)
        authenticated_response = self.client.get(url, {"parent": str(self.division.pk)})
        self.assertEqual(authenticated_response.status_code, 200)
        self.assertEqual(authenticated_response.json(), anonymous_response.json())

        mismatched_parent = self.client.get(url, {"parent": str(self.district.pk)})
        self.assertEqual(mismatched_parent.status_code, 200)
        self.assertEqual(mismatched_parent.json(), {"results": []})
        malformed_parent = self.client.get(url, {"parent": "not-a-uuid"})
        self.assertEqual(malformed_parent.status_code, 200)
        self.assertEqual(malformed_parent.json(), {"results": []})

    def test_options_endpoint_supports_city_corporation_zone_and_ward(self):
        north = Location.objects.create(
            name_en="Synthetic DNCC", level=LocationLevel.CITY_CORPORATION,
            parent=self.district, source_name="Synthetic", source_version="test",
        )
        zone = Location.objects.create(
            name_en="Synthetic Zone", level=LocationLevel.ZONE,
            parent=north, source_name="Synthetic", source_version="test",
        )
        ward = Location.objects.create(
            name_en="Ward 1", level=LocationLevel.WARD, parent=zone,
            corporation_scope=north, source_name="Synthetic", source_version="test",
        )
        response = self.client.get(
            reverse("locations:child_options", args=[LocationLevel.CITY_CORPORATION]),
            {"parent": str(self.district.pk)},
        )
        self.assertEqual([row["id"] for row in response.json()["results"]], [str(north.pk)])
        response = self.client.get(
            reverse("locations:child_options", args=[LocationLevel.ZONE]),
            {"parent": str(north.pk)},
        )
        self.assertEqual([row["id"] for row in response.json()["results"]], [str(zone.pk)])
        response = self.client.get(
            reverse("locations:child_options", args=[LocationLevel.WARD]),
            {"parent": str(zone.pk)},
        )
        self.assertEqual([row["id"] for row in response.json()["results"]], [str(ward.pk)])

    def test_options_endpoint_is_public_read_only_and_validates_parent_ids(self):
        url = reverse("locations:child_options", args=[LocationLevel.DISTRICT])
        self.assertEqual(self.client.get(url, {"parent": "not-a-uuid"}).json()["results"], [])
        self.assertEqual(self.client.get(url, {"parent": str(self.upazila.pk)}).json()["results"], [])
        self.assertEqual(self.client.post(url, {"parent": str(self.division.pk)}).status_code, 405)

        Location.objects.filter(pk=self.district.pk).update(is_active=False)
        response = self.client.get(
            reverse("locations:child_options", args=[LocationLevel.UPAZILA]),
            {"parent": str(self.district.pk)},
        )
        self.assertEqual(response.json()["results"], [])

    def test_options_endpoint_rejects_a_parent_with_an_invalid_ancestor_level(self):
        invalid_district = Location.objects.create(
            name_en="Synthetic Nested District", level=LocationLevel.DISTRICT,
            parent=self.division, source_name="Synthetic", source_version="test",
        )
        invalid_upazila = Location.objects.create(
            name_en="Synthetic Nested Upazila", level=LocationLevel.UPAZILA,
            parent=invalid_district, source_name="Synthetic", source_version="test",
        )
        Location.objects.filter(pk=invalid_district.pk).update(parent_id=self.district.pk)
        response = self.client.get(
            reverse("locations:child_options", args=[LocationLevel.UPAZILA]),
            {"parent": str(invalid_district.pk)},
        )
        self.assertEqual(response.json()["results"], [])

    def test_options_endpoint_gracefully_ignores_invalid_inactive_and_wrong_level_parents(self):
        invalid = self.client.get(reverse("locations:child_options", args=[LocationLevel.DISTRICT]))
        self.assertEqual(invalid.status_code, 200)
        self.assertEqual(invalid.json()["results"], [])
        wrong_parent = self.client.get(reverse("locations:child_options", args=[LocationLevel.DISTRICT]), {
            "parent": str(self.district.pk),
        })
        self.assertEqual(wrong_parent.json()["results"], [])
        Location.objects.filter(pk=self.division.pk).update(is_active=False)
        hidden_ancestor = self.client.get(reverse("locations:child_options", args=[LocationLevel.UPAZILA]), {
            "parent": str(self.district.pk),
        })
        self.assertEqual(hidden_ancestor.json()["results"], [])
        invalid_level = self.client.get(reverse("locations:child_options", args=["DIVISION"]))
        self.assertEqual(invalid_level.status_code, 400)

    def test_dropdown_forms_and_discovery_exclude_active_descendants_of_inactive_ancestors(self):
        from apps.donors.search_forms import DonorSearchForm

        Location.objects.filter(pk=self.division.pk).update(is_active=False)
        profile_form = DonorProfileForm({}, user=User.objects.create_user(
            email="dropdown@example.test", password="safe-test-pass", display_name="Synthetic Dropdown"
        ))
        self.assertNotIn("division", profile_form.fields)
        self.assertNotIn("district", profile_form.fields)
        search_form = DonorSearchForm({"division": str(self.division.pk), "district": str(self.district.pk)})
        self.assertFalse(search_form.fields["district"].queryset.exists())

    def test_profile_and_finder_render_cascade_endpoint_even_when_dataset_is_empty(self):
        Location.objects.update(is_active=False)
        user = User.objects.create_user(
            email="empty-dropdown@example.test", password="safe-test-pass", display_name="Synthetic Empty"
        )
        user.account_status = AccountStatus.ACTIVE
        user.email_verified_at = timezone.now()
        user.save(update_fields=["account_status", "email_verified_at", "updated_at"])
        self.client.force_login(user)
        profile = self.client.get(reverse("donors:profile"))
        finder = self.client.get(reverse("donors:search"))
        self.assertContains(profile, "data-location-picker-mode=\"donor-profile\"")
        self.assertContains(profile, "Map search is unavailable")
        self.assertContains(finder, "data-location-options-url")
        self.assertContains(finder, "Any district")

    def test_empty_location_notice_does_not_claim_existing_profile_was_never_created(self):
        user = User.objects.create_user(
            email="existing-empty-dropdown@example.test",
            password="safe-test-pass",
            display_name="Synthetic Existing Profile",
        )
        DonorProfile.objects.create(
            user=user,
            blood_group=BloodGroup.O_POSITIVE,
            division=self.division,
            district=self.district,
        )
        Location.objects.update(is_active=False)
        user.account_status = AccountStatus.ACTIVE
        user.email_verified_at = timezone.now()
        user.save(update_fields=["account_status", "email_verified_at", "updated_at"])
        self.client.force_login(user)

        response = self.client.get(reverse("donors:profile"))

        self.assertContains(response, "Edit Donor Profile")
        self.assertContains(response, "No donation area selected")
        self.assertNotContains(response, "You cannot create or update a donor profile")

    def test_profile_save_remains_login_protected_and_csrf_protected(self):
        user = User.objects.create_user(
            email="csrf-location@example.test", password="safe-test-pass", display_name="Synthetic CSRF"
        )
        user.account_status = AccountStatus.ACTIVE
        user.email_verified_at = timezone.now()
        user.save(update_fields=["account_status", "email_verified_at", "updated_at"])
        csrf_client = self.client_class(enforce_csrf_checks=True)
        csrf_client.force_login(user)
        profile_url = reverse("donors:profile")
        page = csrf_client.get(profile_url)
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, 'name="csrfmiddlewaretoken"')
        rejected = csrf_client.post(profile_url, {"action": "save"})
        self.assertEqual(rejected.status_code, 403)
        token = page.cookies["csrftoken"].value
        accepted = csrf_client.post(
            profile_url, {"action": "save"}, HTTP_X_CSRFTOKEN=token
        )
        self.assertEqual(accepted.status_code, 200)

class SyntheticLocationWorkflowTests(TestCase):
    def setUp(self):
        records = sample_records() + [
            {
                "source_id": "SYN-DIV-02", "name_en": "Test Division B", "name_bn": None,
                "level": "DIVISION", "parent_path": [],
            },
            {
                "source_id": "SYN-DIST-02", "name_en": "Test District B", "name_bn": None,
                "level": "DISTRICT", "parent_path": ["Test Division B"],
            },
            {
                "source_id": "SYN-UPA-02", "name_en": "Test Upazila B", "name_bn": None,
                "level": "UPAZILA", "parent_path": ["Test Division B", "Test District B"],
            },
        ]
        self.snapshot_document = snapshot(records)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "synthetic-locations.json"
            path.write_text(json.dumps(self.snapshot_document), encoding="utf-8")
            output = io.StringIO()
            call_command("load_locations", file=path, reviewed=True, activate=True, stdout=output)
            self.assertIn("6 created", output.getvalue())
            output = io.StringIO()
            call_command("load_locations", file=path, reviewed=True, activate=True, stdout=output)
            self.assertIn("6 unchanged", output.getvalue())
        self.user = User.objects.create_user(
            email="synthetic-smoke@example.test",
            password="Synthetic-Unique-Password!947",
            display_name="Synthetic Snapshot Donor",
        )
        self.user.account_status = AccountStatus.ACTIVE
        self.user.email_verified_at = timezone.now()
        self.user.save(update_fields=["account_status", "email_verified_at", "updated_at"])

    def test_synthetic_import_cascade_profile_edit_and_combined_donor_search(self):
        self.assertEqual(Location.objects.filter(level=LocationLevel.DIVISION).count(), 2)
        self.assertEqual(Location.objects.filter(level=LocationLevel.DISTRICT).count(), 2)
        self.assertEqual(Location.objects.filter(level=LocationLevel.UPAZILA).count(), 2)
        self.assertEqual(Location.objects.exclude(source_id__isnull=True).count(), 6)

        division = Location.objects.get(name_en="Test Division A")
        other_division = Location.objects.get(name_en="Test Division B")
        district = Location.objects.get(name_en="Test District A")
        upazila = Location.objects.get(name_en="Test Upazila A")
        other_district = Location.objects.get(name_en="Test District B")
        other_upazila = Location.objects.get(name_en="Test Upazila B")

        unbound = DonorProfileForm(user=self.user)
        self.assertNotIn("division", unbound.fields)
        self.assertNotIn("district", unbound.fields)
        self.assertNotIn("upazila", unbound.fields)

        self.client.force_login(self.user)
        profile_url = reverse("donors:profile")
        self.assertEqual(self.client.get(profile_url).status_code, 200)
        data = {
            "blood_group": BloodGroup.O_POSITIVE,
            "availability_status": AvailabilityStatus.AVAILABLE,
            "visibility_enabled": "on",
            "public_alias": "Synthetic Snapshot Donor",
            "preferred_contact_method": "IN_APP",
            "share_email_after_accept": "",
            "last_donation_date": "",
        }
        self.assertEqual(self.client.post(profile_url, data).status_code, 302)
        profile = DonorProfile.objects.get(user=self.user)
        self.assertIsNone(profile.division_id)
        self.assertIsNone(profile.district_id)
        self.assertIsNone(profile.upazila_id)

        edited = dict(data, public_alias="Synthetic Edited Donor")
        self.assertEqual(self.client.post(profile_url, edited).status_code, 302)
        profile.refresh_from_db()
        self.assertIsNone(profile.division_id)
        profile.division = other_division
        profile.district = other_district
        profile.upazila = other_upazila
        profile.save(update_fields=["division", "district", "upazila"])

        search = self.client.get(reverse("donors:search"), {
            "blood_group": BloodGroup.O_POSITIVE,
            "division": str(other_division.pk),
            "district": str(other_district.pk),
            "upazila": str(other_upazila.pk),
            "availability": AvailabilityStatus.AVAILABLE,
        })
        self.assertEqual(search.status_code, 200)
        self.assertEqual(search.context["page_obj"].paginator.count, 1)
        self.assertContains(search, "Synthetic Edited Donor")
