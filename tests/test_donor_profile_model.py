from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import AccountStatus
from apps.accounts.permissions import AccountRole, has_role
from apps.donors.models import (
    AvailabilityStatus,
    BloodGroup,
    DonorAreaLocationSource,
    DonorProfile,
    DonorProfileStatus,
    PreferredContactMethod,
)
from apps.locations.models import Location, LocationLevel

User = get_user_model()


class DonorProfileModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="donor@example.test",
            password="Synthetic-Unique-Password!947",
            display_name="Donor Example",
        )
        self.user.account_status = AccountStatus.ACTIVE
        self.user.save(update_fields=["account_status", "updated_at"])
        self.division = self.location("Dhaka", LocationLevel.DIVISION)
        self.district = self.location("Dhaka", LocationLevel.DISTRICT, self.division)
        self.other_division = self.location("Chattogram", LocationLevel.DIVISION)
        self.other_district = self.location(
            "Chattogram", LocationLevel.DISTRICT, self.other_division
        )
        self.upazila = self.location("Dhamrai", LocationLevel.UPAZILA, self.district)
        self.other_upazila = self.location("Boalmari", LocationLevel.UPAZILA, self.other_district)

    def location(self, name, level, parent=None):
        return Location.objects.create(
            name_en=name,
            level=level,
            parent=parent,
            source_name="Synthetic test fixture",
            source_version="synthetic-v1",
        )

    def profile(self, **overrides):
        values = {
            "user": self.user,
            "blood_group": BloodGroup.O_POSITIVE,
            "division": self.division,
            "district": self.district,
        }
        values.update(overrides)
        return DonorProfile.objects.create(**values)

    def test_safe_defaults_and_documented_choices(self):
        profile = self.profile(upazila=self.upazila)

        self.assertEqual(profile.availability_status, AvailabilityStatus.UNAVAILABLE)
        self.assertEqual(profile.profile_status, DonorProfileStatus.DRAFT)
        self.assertFalse(profile.visibility_enabled)
        self.assertFalse(profile.share_phone_after_accept)
        self.assertFalse(profile.share_email_after_accept)
        self.assertEqual(profile.preferred_contact_method, PreferredContactMethod.IN_APP)
        self.assertIsNone(profile.last_donation_date)
        self.assertIn(profile.blood_group, BloodGroup.values)

    def test_profile_location_hierarchy_is_checked(self):
        with self.assertRaisesMessage(ValidationError, "must belong to the selected division"):
            self.profile(district=self.other_district)
        with self.assertRaisesMessage(ValidationError, "must belong to the selected district"):
            self.profile(upazila=self.other_upazila)
        with self.assertRaisesMessage(ValidationError, "division-level"):
            self.profile(division=self.district)

    def test_map_only_donation_area_is_valid_and_coordinates_are_bounded(self):
        map_profile = self.profile(
            division=None,
            district=None,
            donation_area_label="Synthetic general area",
            donation_area_latitude="23.74650000",
            donation_area_longitude="90.37600000",
            google_place_id="synthetic-place-id",
            location_source=DonorAreaLocationSource.GOOGLE_PLACE,
            location_confirmed_at=timezone.now(),
        )
        self.assertIsNone(map_profile.division_id)
        self.assertIsNone(map_profile.district_id)
        self.assertEqual(map_profile.donation_area_label, "Synthetic general area")

        invalid_user = User.objects.create_user(
            email="invalid-donation-area@example.test",
            password="Synthetic-Unique-Password!947",
            display_name="Invalid donor",
        )
        with self.assertRaises(ValidationError):
            DonorProfile(
                user=invalid_user,
                blood_group=BloodGroup.O_POSITIVE,
                donation_area_label="Synthetic general area",
                donation_area_latitude="91.00000000",
                donation_area_longitude="90.37600000",
                location_source=DonorAreaLocationSource.MAP_PIN,
                location_confirmed_at=timezone.now(),
            ).full_clean()

        with self.assertRaises(ValidationError):
            DonorProfile(
                user=invalid_user,
                blood_group=BloodGroup.O_POSITIVE,
                donation_area_label="Location without point",
            ).full_clean()

    def test_one_profile_per_user_and_reference_rows_are_protected(self):
        self.profile()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                DonorProfile.objects.bulk_create(
                    [
                        DonorProfile(
                            user=self.user,
                            blood_group=BloodGroup.A_POSITIVE,
                            division=self.division,
                            district=self.district,
                        )
                    ]
                )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.district.delete()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.user.delete()

    def test_database_rejects_blood_group_outside_schema_enum(self):
        profile = self.profile()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                DonorProfile.objects.filter(pk=profile.pk).update(blood_group="X+")

    def test_profile_creation_assigns_donor_role_only_for_active_accounts(self):
        self.assertFalse(has_role(self.user, AccountRole.DONOR))
        self.profile()
        self.assertTrue(has_role(self.user, AccountRole.DONOR))

        self.user.account_status = AccountStatus.SUSPENDED
        self.user.save(update_fields=["account_status", "updated_at"])
        self.assertFalse(has_role(self.user, AccountRole.DONOR))

    def test_schema_indexes_match_donor_search_paths(self):
        indexes = {tuple(index.fields) for index in DonorProfile._meta.indexes}
        self.assertEqual(
            indexes,
            {
                ("blood_group", "availability_status", "profile_status"),
                ("district", "blood_group", "availability_status"),
                ("upazila", "blood_group", "availability_status"),
                ("city_corporation", "ward", "blood_group"),
                ("visibility_enabled", "profile_status"),
            },
        )
