from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import AccountStatus
from apps.donors.models import (
    AvailabilityStatus,
    BloodGroup,
    DonorAreaLocationSource,
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
    def location(name, level, parent=None, **extra):
        return Location.objects.create(
            name_en=name,
            level=level,
            parent=parent,
            source_name="Synthetic test fixture",
            source_version="synthetic-v1",
            **extra,
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
        rural_union = self.location("Synthetic Rural Union", LocationLevel.UNION, self.upazila)
        match = self.make_profile(1, union=rural_union)
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
                "union": str(rural_union.pk),
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["page_obj"].object_list), [match])
        self.assertContains(response, "Public Alias 1")
        self.assertContains(response, "potential donor found")
        self.assertNotContains(response, "Public Alias 2")

    def test_filters_and_displays_city_corporation_zone_and_ward(self):
        north = self.location("Synthetic DNCC", LocationLevel.CITY_CORPORATION, self.district)
        south = self.location("Synthetic DSCC", LocationLevel.CITY_CORPORATION, self.district)
        north_zone = self.location("Synthetic North Zone", LocationLevel.ZONE, north)
        south_zone = self.location("Synthetic South Zone", LocationLevel.ZONE, south)
        north_ward = self.location(
            "Ward 1", LocationLevel.WARD, north_zone, corporation_scope=north
        )
        self.location("Ward 1", LocationLevel.WARD, south_zone, corporation_scope=south)
        city_profile = self.make_profile(
            50,
            upazila=None,
            city_corporation=north,
            city_zone=north_zone,
            ward=north_ward,
        )
        response = self.client.get(
            reverse("donors:search"),
            {
                "division": str(self.division.pk),
                "district": str(self.district.pk),
                "city_corporation": str(north.pk),
                "city_zone": str(north_zone.pk),
                "ward": str(north_ward.pk),
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["page_obj"].object_list), [city_profile])
        self.assertContains(response, "Synthetic DNCC")
        self.assertContains(response, "Ward 1")
        invalid = self.client.get(
            reverse("donors:search"),
            {
                "division": str(self.division.pk),
                "district": str(self.district.pk),
                "city_corporation": str(north.pk),
                "city_zone": str(north_zone.pk),
                "ward": str(Location.objects.get(name_en="Ward 1", corporation_scope=south).pk),
            },
        )
        self.assertTrue(invalid.context["invalid_filters"])
        self.assertEqual(invalid.context["page_obj"].paginator.count, 0)

    def test_synthetic_corporation_counts_can_be_represented(self):
        north = self.location("Synthetic DNCC counts", LocationLevel.CITY_CORPORATION, self.district)
        south = self.location("Synthetic DSCC counts", LocationLevel.CITY_CORPORATION, self.district)
        north_zones = [
            self.location(f"North Zone {index}", LocationLevel.ZONE, north)
            for index in range(1, 11)
        ]
        south_zones = [
            self.location(f"South Zone {index}", LocationLevel.ZONE, south)
            for index in range(1, 11)
        ]
        for corporation, zones, ward_count in ((north, north_zones, 54), (south, south_zones, 75)):
            for number in range(1, ward_count + 1):
                zone = zones[(number - 1) % len(zones)]
                self.location(
                    f"Ward {number}", LocationLevel.WARD, zone,
                    corporation_scope=corporation,
                )
        self.assertEqual(Location.objects.filter(parent=north, level=LocationLevel.ZONE).count(), 10)
        self.assertEqual(Location.objects.filter(corporation_scope=north, level=LocationLevel.WARD).count(), 54)
        self.assertEqual(Location.objects.filter(corporation_scope=south, level=LocationLevel.WARD).count(), 75)

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
        profile = self.make_profile(
            1,
            donation_area_label="Private synthetic general area",
            donation_area_latitude="23.74650000",
            donation_area_longitude="90.37600000",
            google_place_id="private-synthetic-place-id",
            location_source=DonorAreaLocationSource.GOOGLE_PLACE,
            location_confirmed_at=timezone.now(),
        )
        response = self.client.get(reverse("donors:search"))
        content = response.content.decode()
        self.assertContains(response, profile.public_alias)
        self.assertNotContains(response, profile.user.email)
        self.assertNotContains(response, "Private Name 1")
        self.assertNotContains(response, "PHONE_AFTER_ACCEPT")
        self.assertNotContains(response, "share_phone_after_accept")
        self.assertNotIn("phone_e164", content)
        self.assertNotIn("23.74650000", content)
        self.assertNotIn("90.37600000", content)
        self.assertNotIn("Private synthetic general area", content)
        self.assertNotIn("private-synthetic-place-id", content)
        api_response = self.client.get(reverse("api_v1:donor_list"))
        self.assertEqual(api_response.status_code, 200)
        api_result = api_response.json()["results"][0]
        self.assertNotIn("donation_area_latitude", api_result)
        self.assertNotIn("donation_area_longitude", api_result)
        self.assertNotIn("google_place_id", api_result)
        self.assertNotIn("location_source", api_result)
        self.assertNotIn("Private synthetic general area", str(api_result))

    def test_map_only_profile_is_not_added_to_existing_discovery_results(self):
        map_only_user = self.make_user(82)
        map_only_profile = DonorProfile.objects.create(
            user=map_only_user,
            blood_group=BloodGroup.O_POSITIVE,
            donation_area_label="Private synthetic area",
            donation_area_latitude="23.74650000",
            donation_area_longitude="90.37600000",
            location_source=DonorAreaLocationSource.MAP_PIN,
            location_confirmed_at=timezone.now(),
            availability_status=AvailabilityStatus.AVAILABLE,
            visibility_enabled=True,
            profile_status=DonorProfileStatus.ACTIVE,
        )
        record_consent(
            user=map_only_user,
            consent_type=ConsentType.DONOR_DISCOVERY,
            policy_version="draft-1",
            granted=True,
        )
        self.assertFalse(DonorProfile.objects.discoverable().filter(pk=map_only_profile.pk).exists())

        html_response = self.client.get(reverse("donors:search"))
        api_response = self.client.get(reverse("api_v1:donor_list"))

        self.assertEqual(html_response.context["page_obj"].paginator.count, 0)
        self.assertNotContains(html_response, "Private synthetic area")
        self.assertEqual(api_response.json()["count"], 0)

    def test_search_exposes_list_and_location_preview_without_donor_markers(self):
        profile = self.make_profile(2)

        response = self.client.get(reverse("donors:search"))
        content = response.content.decode()

        self.assertContains(response, "List view")
        self.assertContains(response, "Map view")
        self.assertContains(response, "Donor locations are not plotted")
        self.assertContains(response, "No donor markers or distances are available")
        self.assertContains(response, profile.get_availability_status_display())
        self.assertContains(response, profile.public_alias)
        self.assertNotContains(response, "data-donor-marker")
        self.assertNotContains(response, profile.user.email)
        self.assertNotIn("phone_e164", content)
        self.assertNotIn("latitude", content)
        self.assertNotIn("longitude", content)

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

    def test_location_first_page_keeps_location_and_radius_out_of_admin_get(self):
        response = self.client.get(reverse("donors:search"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(reverse("donors:search"), "/app/")
        content = response.content.decode()
        self.assertIn('class="donor-search__dashboard"', content)
        dashboard_start = content.index('class="donor-search__dashboard"')
        search_card = content.index('class="donor-search__search-card card"', dashboard_start)
        advanced_filters = content.index('class="donor-search__advanced"', search_card)
        results_toolbar = content.index('class="donor-search__results-toolbar"', search_card)
        results = content.index('id="donor-search-results"')
        map_column = content.index('class="donor-search__map-column"', results)
        form_end = content.index("</form>", dashboard_start)
        self.assertLess(dashboard_start, search_card)
        self.assertLess(search_card, advanced_filters)
        self.assertLess(advanced_filters, results_toolbar)
        self.assertLess(results_toolbar, results)
        self.assertLess(results, map_column)
        self.assertLess(map_column, form_end)
        self.assertLess(results, form_end)
        self.assertEqual(content[dashboard_start:form_end].count('type="submit"'), 1)
        self.assertIn('id="donor-search-results"', content)
        self.assertIn(
            '<span class="donor-search__count-badge">0</span> potential donors found',
            content,
        )
        self.assertIn("Clear search", content)
        self.assertIn('id="donor-blood-group"', content)
        for value in ("A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"):
            self.assertIn(f'<option value="{value}"', content)
        self.assertIn('<option value="" selected>', content)
        self.assertIn('data-radius="5"', content)
        self.assertIn('data-radius="10"', content)
        self.assertIn('data-radius="20"', content)
        self.assertIn('data-radius="50"', content)
        self.assertIn("Radius preview", content)
        self.assertIn("Visual preview only", content)
        self.assertIn("do not change donor results", content)
        self.assertIn('type="search"', content)
        self.assertIn('placeholder="Search address or area"', content)
        self.assertIn('data-role="search-address"', content)
        self.assertIn('data-role="place-suggestions"', content)
        self.assertIn('data-role="use-my-location"', content)
        self.assertIn('data-role="confirm-location"', content)
        self.assertIn('type="submit"', content)
        self.assertIn("Search donors", content)
        self.assertIn('name="division"', content)
        self.assertIn('name="availability"', content)
        self.assertRegex(content, r'<details class="donor-search__advanced"[^>]*>')
        self.assertNotIn('name="latitude"', content)
        self.assertNotIn('name="longitude"', content)
        self.assertNotIn('name="radius_km"', content)
        self.assertNotIn('name="hospital"', content)
        self.assertNotIn("donor-search-latitude", content)

    def test_empty_results_show_zero_count_and_helpful_state(self):
        response = self.client.get(reverse("donors:search"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "potential donors found")
        self.assertContains(response, "No donors found")

    @override_settings(DEBUG=True, GOOGLE_MAPS_BROWSER_API_KEY="synthetic-restricted-browser-key")
    def test_find_donor_page_uses_only_the_configured_browser_key(self):
        response = self.client.get(reverse("donors:search"))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('data-google-maps-api-key="synthetic-restricted-browser-key"', content)
        self.assertEqual(content.count("synthetic-restricted-browser-key"), 1)

    @override_settings(DEBUG=False, GOOGLE_MAPS_BROWSER_API_KEY="must-not-be-rendered")
    def test_find_donor_page_does_not_render_browser_key_outside_development(self):
        response = self.client.get(reverse("donors:search"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "must-not-be-rendered")

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
