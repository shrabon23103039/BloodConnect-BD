from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import AccountStatus
from apps.donors.models import (
    AvailabilityStatus,
    BloodGroup,
    DonorProfile,
    DonorProfileStatus,
)
from apps.governance.models import ConsentType, record_consent
from apps.locations.models import Location, LocationLevel

User = get_user_model()


class DonorSearchTests(TestCase):
    def setUp(self):
        cache.clear()
        self.division = self.location("Test division", LocationLevel.DIVISION)
        self.other_division = self.location("Other division", LocationLevel.DIVISION)
        self.district = self.location(
            "Test district", LocationLevel.DISTRICT, self.division
        )
        self.other_district = self.location(
            "Other district", LocationLevel.DISTRICT, self.other_division
        )
        self.upazila = self.location(
            "Test upazila", LocationLevel.UPAZILA, self.district
        )
        self.user = self.make_user(0)
        self.client.force_login(self.user)

    @staticmethod
    def location(name, level, parent=None):
        return Location.objects.create(
            name_en=name,
            level=level,
            parent=parent,
            source_name="Synthetic test fixture",
            source_version="synthetic-v1",
        )

    @staticmethod
    def make_user(index):
        user = User.objects.create_user(
            email=f"private-{index}@example.test",
            password="Synthetic-Unique-Password!947",
            display_name=f"Private Name {index}",
        )
        user.account_status = AccountStatus.ACTIVE
        user.email_verified_at = timezone.now()
        user.save(update_fields=["account_status", "email_verified_at", "updated_at"])
        return user

    def make_profile(self, index, **overrides):
        user = self.make_user(index)
        values = {
            "user": user,
            "blood_group": BloodGroup.O_POSITIVE,
            "division": self.division,
            "district": self.district,
            "upazila": self.upazila,
            "availability_status": AvailabilityStatus.AVAILABLE,
            "visibility_enabled": True,
            "public_alias": f"Public Alias {index}",
            "profile_status": DonorProfileStatus.ACTIVE,
        }
        values.update(overrides)
        profile = DonorProfile.objects.create(**values)
        record_consent(
            user=user,
            consent_type=ConsentType.DONOR_DISCOVERY,
            policy_version="draft-1",
            granted=True,
        )
        return profile

    def test_filters_use_exact_blood_group_and_hierarchical_locations(self):
        match = self.make_profile(1)
        self.make_profile(2, blood_group=BloodGroup.A_POSITIVE)
        self.make_profile(
            3,
            district=self.other_district,
            division=self.other_division,
            upazila=None,
        )
        response = self.client.get(
            reverse("donors:search"),
            {
                "blood_group": BloodGroup.O_POSITIVE,
                "division": str(self.division.pk),
                "district": str(self.district.pk),
                "upazila": str(self.upazila.pk),
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["page_obj"].object_list), [match])
        self.assertContains(response, "Public Alias 1")
        self.assertNotContains(response, "Public Alias 2")

    def test_guest_search_shows_only_profiles_with_discovery_consent(self):
        no_consent = self.make_user(1)
        DonorProfile.objects.create(
            user=no_consent,
            blood_group=BloodGroup.O_POSITIVE,
            division=self.division,
            district=self.district,
            availability_status=AvailabilityStatus.AVAILABLE,
            visibility_enabled=True,
            profile_status=DonorProfileStatus.ACTIVE,
        )
        self.client.logout()
        response = self.client.get(reverse("donors:search"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page_obj"].paginator.count, 0)

    def test_search_card_omits_private_account_and_profile_fields(self):
        profile = self.make_profile(1)
        response = self.client.get(reverse("donors:search"))
        content = response.content.decode()
        self.assertContains(response, profile.public_alias)
        self.assertNotContains(response, profile.user.email)
        self.assertNotContains(response, "Private Name 1")
        self.assertNotContains(response, "PHONE_AFTER_ACCEPT")
        self.assertNotContains(response, "share_phone_after_accept")
        self.assertNotIn("phone_e164", content)

    def test_pagination_is_fixed_and_filter_query_is_preserved(self):
        for index in range(1, 22):
            self.make_profile(index)
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(
                reverse("donors:search"), {"blood_group": BloodGroup.O_POSITIVE}
            )
        self.assertEqual(response.context["page_obj"].paginator.per_page, 20)
        self.assertEqual(len(response.context["page_obj"].object_list), 20)
        self.assertLessEqual(len(queries), 10)
        self.assertContains(response, "page=2")
        second_page = self.client.get(
            reverse("donors:search"),
            {"blood_group": BloodGroup.O_POSITIVE, "page": "2"},
        )
        self.assertEqual(second_page.context["page_obj"].number, 2)
        self.assertEqual(len(second_page.context["page_obj"].object_list), 1)

    def test_invalid_filter_values_show_error_without_broadening_results(self):
        self.make_profile(1)
        response = self.client.get(
            reverse("donors:search"), {"blood_group": "X+", "division": "not-a-uuid"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["invalid_filters"])
        self.assertEqual(response.context["page_obj"].paginator.count, 0)

    def test_search_is_throttled_per_ip_after_thirty_requests_per_minute(self):
        self.client.logout()
        for _ in range(30):
            response = self.client.get(reverse("donors:search"))
            self.assertEqual(response.status_code, 200)

        throttled = self.client.get(reverse("donors:search"))
        self.assertEqual(throttled.status_code, 429)
        self.assertEqual(throttled["Retry-After"], "60")
        self.assertNotContains(throttled, "donor", status_code=429)

    def test_search_throttle_uses_hmac_ip_key_and_separate_scope(self):
        from unittest.mock import patch

        with patch("apps.accounts.throttling.cache.add", wraps=cache.add) as cache_add:
            self.client.get(reverse("donors:search"), REMOTE_ADDR="203.0.113.42")

        key = cache_add.call_args.args[0]
        self.assertTrue(key.startswith("accounts:throttle:donor-search:"))
        self.assertNotIn("203.0.113.42", key)

        for _ in range(29):
            self.client.get(reverse("donors:search"), REMOTE_ADDR="203.0.113.42")
        other_ip_response = self.client.get(
            reverse("donors:search"), REMOTE_ADDR="203.0.113.43"
        )
        self.assertEqual(other_ip_response.status_code, 200)
