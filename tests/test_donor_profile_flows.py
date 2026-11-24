from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import AccountStatus
from apps.donors.models import (
    AvailabilityStatus,
    BloodGroup,
    DonorProfile,
    DonorProfileStatus,
    PreferredContactMethod,
)
from apps.donors.services import (
    deactivate_donor_profile,
    has_current_contact_consent,
    pause_donor_profile,
    save_donor_profile,
)
from apps.governance.models import ConsentRecord, ConsentType, record_consent
from apps.locations.models import Location, LocationLevel

User = get_user_model()
PASSWORD = "Synthetic-Unique-Password!947"


class DonorProfileFlowTests(TestCase):
    def setUp(self):
        self.user = self.make_user("owner@example.test")
        self.other_user = self.make_user("other@example.test")
        self.division = self.location("Dhaka", LocationLevel.DIVISION)
        self.district = self.location("Dhaka", LocationLevel.DISTRICT, self.division)
        self.upazila = self.location("Dhamrai", LocationLevel.UPAZILA, self.district)
        self.url = reverse("donors:profile")
        self.client.force_login(self.user)

    def make_user(self, email):
        user = User.objects.create_user(email=email, password=PASSWORD, display_name=email)
        user.account_status = AccountStatus.ACTIVE
        user.email_verified_at = timezone.now()
        user.save(update_fields=["account_status", "email_verified_at", "updated_at"])
        return user

    def location(self, name, level, parent=None, **extra):
        return Location.objects.create(
            name_en=name,
            level=level,
            parent=parent,
            source_name="Synthetic test fixture",
            source_version="synthetic-v1",
            **extra,
        )

    def profile_data(self, **overrides):
        data = {
            "blood_group": BloodGroup.O_POSITIVE,
            "donation_area_label": "Dhanmondi",
            "donation_area_latitude": "23.74650000",
            "donation_area_longitude": "90.37600000",
            "google_place_id": "synthetic-place-id",
            "location_source": "GOOGLE_PLACE",
            "location_confirmed": "on",
            "store_donation_area": "on",
            "availability_status": AvailabilityStatus.UNAVAILABLE,
            "public_alias": "Kind Donor",
            "thana_name": "",
            "preferred_contact_method": PreferredContactMethod.EMAIL_AFTER_ACCEPT,
            "share_email_after_accept": "on",
            "last_donation_date": "",
        }
        data.update(overrides)
        return data

    def test_active_owner_can_create_and_update_profile_with_versioned_contact_consent(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        response = self.client.post(self.url, self.profile_data())
        self.assertRedirects(response, self.url)

        profile = DonorProfile.objects.get(user=self.user)
        self.assertEqual(profile.profile_status, DonorProfileStatus.DRAFT)
        self.assertEqual(profile.availability_status, AvailabilityStatus.UNAVAILABLE)
        self.assertEqual(profile.donation_area_label, "Dhanmondi")
        self.assertEqual(str(profile.donation_area_latitude), "23.74650000")
        self.assertEqual(str(profile.donation_area_longitude), "90.37600000")
        self.assertEqual(profile.google_place_id, "synthetic-place-id")
        self.assertEqual(profile.location_source, "GOOGLE_PLACE")
        self.assertIsNotNone(profile.location_confirmed_at)
        self.assertIsNone(profile.division_id)
        self.assertIsNone(profile.district_id)
        self.assertTrue(profile.share_email_after_accept)
        self.assertFalse(profile.share_phone_after_accept)
        self.assertTrue(has_current_contact_consent(profile=profile, channel="email"))
        self.assertFalse(has_current_contact_consent(profile=profile, channel="phone"))
        self.assertEqual(
            ConsentRecord.objects.filter(
                user=self.user,
                consent_type=ConsentType.EMAIL_SHARE_AFTER_ACCEPT,
                granted=True,
            ).count(),
            1,
        )
        self.assertTrue(
            ConsentRecord.objects.filter(
                user=self.user,
                consent_type=ConsentType.DONOR_AREA_STORAGE,
                granted=True,
            ).exists()
        )

        record_consent(
            user=self.user,
            consent_type=ConsentType.EMAIL_SHARE_AFTER_ACCEPT,
            policy_version="draft-1",
            granted=False,
        )
        self.assertTrue(profile.share_email_after_accept)
        self.assertFalse(has_current_contact_consent(profile=profile, channel="email"))
        privacy_response = self.client.get(self.url)
        self.assertFalse(privacy_response.context["form"].initial["share_email_after_accept"])

        self.client.post(
            self.url,
            self.profile_data(
                preferred_contact_method=PreferredContactMethod.IN_APP,
                share_email_after_accept="",
            ),
        )
        profile.refresh_from_db()
        self.assertFalse(profile.share_email_after_accept)
        self.assertFalse(has_current_contact_consent(profile=profile, channel="email"))
        events = ConsentRecord.objects.filter(
            user=self.user,
            consent_type=ConsentType.EMAIL_SHARE_AFTER_ACCEPT,
        ).order_by("captured_at")
        self.assertEqual(events.count(), 2)
        self.assertFalse(events.last().granted)
        self.assertIsNotNone(events.last().withdrawn_at)

    def test_profile_page_shows_saved_status_and_privacy_safe_search_preview(self):
        profile = DonorProfile.objects.create(
            user=self.user,
            blood_group=BloodGroup.O_POSITIVE,
            division=self.division,
            district=self.district,
            upazila=self.upazila,
            public_alias="Kind Donor",
            availability_status=AvailabilityStatus.UNAVAILABLE,
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Edit Donor Profile")
        self.assertContains(response, "Quick tips")
        self.assertContains(response, "Back to Find Donors")
        self.assertContains(response, f'href="{reverse("donors:search")}"')
        self.assertContains(response, "Your contact details are shared only after you accept a request")
        self.assertContains(response, "Map search is unavailable right now.")
        self.assertNotContains(response, "GOOGLE_MAPS_BROWSER_API_KEY")
        self.assertContains(response, 'aria-describedby="profile-contact-help"')
        self.assertContains(response, "(required)")
        self.assertContains(response, "Kind Donor")
        self.assertContains(response, profile.get_profile_status_display())
        self.assertContains(response, profile.get_availability_status_display())
        self.assertContains(response, "Not listed in search")
        self.assertContains(response, "Preview your public profile")
        self.assertContains(response, 'class="donor-search__result card"')
        self.assertContains(response, "Blood &amp; location")
        self.assertContains(response, "Contact preference")
        self.assertContains(response, "Donation history")
        self.assertNotContains(response, "Area choices are temporarily unavailable")
        self.assertNotContains(response, 'name="division"')
        self.assertNotContains(response, 'name="district"')
        self.assertNotContains(response, "phone_e164")
        self.assertContains(response, "Cancel")

    def test_map_area_updates_legacy_area_and_places_reversibly(self):
        profile = DonorProfile.objects.create(
            user=self.user,
            blood_group=BloodGroup.O_POSITIVE,
            division=self.division,
            district=self.district,
            upazila=self.upazila,
        )
        record_consent(
            user=self.user,
            consent_type=ConsentType.DONOR_AREA_STORAGE,
            policy_version="draft-1",
            granted=True,
        )

        response = self.client.post(
            self.url,
            self.profile_data(
                donation_area_label="Uttara",
                donation_area_latitude="23.87590000",
                donation_area_longitude="90.37950000",
                google_place_id="updated-synthetic-place",
                location_source="GOOGLE_GEOCODE",
                preferred_contact_method=PreferredContactMethod.IN_APP,
                share_email_after_accept="",
            ),
        )
        self.assertRedirects(response, self.url)
        profile.refresh_from_db()
        self.assertEqual(profile.donation_area_label, "Uttara")
        self.assertEqual(str(profile.donation_area_latitude), "23.87590000")
        self.assertEqual(profile.google_place_id, "updated-synthetic-place")
        self.assertEqual(profile.location_source, "GOOGLE_GEOCODE")
        self.assertIsNotNone(profile.location_confirmed_at)
        self.assertIsNone(profile.division_id)
        self.assertIsNone(profile.district_id)
        self.assertIsNone(profile.upazila_id)

    def test_saving_without_a_map_area_preserves_existing_administrative_location(self):
        profile = DonorProfile.objects.create(
            user=self.user,
            blood_group=BloodGroup.O_POSITIVE,
            division=self.division,
            district=self.district,
            upazila=self.upazila,
        )
        response = self.client.post(
            self.url,
            self.profile_data(
                donation_area_label="",
                donation_area_latitude="",
                donation_area_longitude="",
                google_place_id="",
                location_source="",
                location_confirmed="",
                store_donation_area="",
                preferred_contact_method=PreferredContactMethod.IN_APP,
                share_email_after_accept="",
            ),
        )

        self.assertRedirects(response, self.url)
        profile.refresh_from_db()
        self.assertEqual(profile.division_id, self.division.id)
        self.assertEqual(profile.district_id, self.district.id)
        self.assertEqual(profile.upazila_id, self.upazila.id)

    def test_clearing_donation_area_removes_point_and_withdraws_consent(self):
        self.client.post(self.url, self.profile_data())
        profile = DonorProfile.objects.get(user=self.user)
        clear_data = self.profile_data(
            donation_area_label="",
            donation_area_latitude="",
            donation_area_longitude="",
            google_place_id="",
            location_source="",
            location_confirmed="",
            store_donation_area="",
            preferred_contact_method=PreferredContactMethod.IN_APP,
            share_email_after_accept="",
        )

        response = self.client.post(self.url, clear_data)

        self.assertRedirects(response, self.url)
        profile.refresh_from_db()
        self.assertIsNone(profile.donation_area_latitude)
        self.assertIsNone(profile.donation_area_longitude)
        self.assertEqual(profile.donation_area_label, "")
        self.assertEqual(profile.google_place_id, "")
        self.assertEqual(profile.location_source, "")
        self.assertIsNone(profile.location_confirmed_at)
        latest_consent = ConsentRecord.objects.filter(
            user=self.user,
            consent_type=ConsentType.DONOR_AREA_STORAGE,
        ).latest("captured_at")
        self.assertFalse(latest_consent.granted)
        self.assertIsNotNone(latest_consent.withdrawn_at)

    def test_blood_group_is_required_and_location_requires_confirmation_and_consent(self):
        response = self.client.post(self.url, self.profile_data(blood_group=""))
        self.assertEqual(response.status_code, 200)
        self.assertIn("blood_group", response.context["form"].errors)
        self.assertContains(response, 'href="#id_blood_group"')
        self.assertFalse(DonorProfile.objects.filter(user=self.user).exists())

        response = self.client.post(
            self.url,
            self.profile_data(location_confirmed="", store_donation_area=""),
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("location_confirmed", response.context["form"].errors)
        self.assertIn("store_donation_area", response.context["form"].errors)
        self.assertContains(response, 'href="#donor-area-search"')
        self.assertContains(response, 'aria-invalid="true"')
        self.assertContains(response, 'aria-describedby="donor-area-help donor-area-errors"')
        self.assertContains(response, 'aria-describedby="id_store_donation_area-help id_store_donation_area-errors"')
        self.assertFalse(DonorProfile.objects.filter(user=self.user).exists())

    def test_profile_updates_are_owner_scoped(self):
        other_profile = DonorProfile.objects.create(
            user=self.other_user,
            blood_group=BloodGroup.A_POSITIVE,
            division=self.division,
            district=self.district,
        )
        with self.assertRaises(PermissionDenied):
            save_donor_profile(
                user=self.user,
                profile=other_profile,
                values={
                    "blood_group": BloodGroup.O_POSITIVE,
                    "division": self.division,
                    "district": self.district,
                    "upazila": self.upazila,
                    "public_alias": "Changed",
                    "preferred_contact_method": PreferredContactMethod.IN_APP,
                    "last_donation_date": None,
                },
                consent_fields=set(),
            )
        other_profile.refresh_from_db()
        self.assertEqual(other_profile.blood_group, BloodGroup.A_POSITIVE)

    def test_only_verified_contact_methods_are_offered(self):
        self.user.email_verified_at = None
        self.user.phone_e164 = None
        self.user.email = None
        self.user.phone_e164 = "+8801700000000"
        self.user.phone_verified_at = timezone.now()
        self.user.save(
            update_fields=["email", "phone_e164", "phone_verified_at", "email_verified_at", "updated_at"]
        )

        response = self.client.get(self.url)
        form = response.context["form"]
        self.assertNotIn("share_email_after_accept", form.fields)
        self.assertIn("share_phone_after_accept", form.fields)
        self.assertEqual(
            [value for value, label in form.fields["preferred_contact_method"].choices],
            [PreferredContactMethod.IN_APP, PreferredContactMethod.PHONE_AFTER_ACCEPT],
        )

    def test_pause_and_deactivation_hide_the_profile_and_revoke_discovery(self):
        profile = DonorProfile.objects.create(
            user=self.user,
            blood_group=BloodGroup.O_POSITIVE,
            division=self.division,
            district=self.district,
            availability_status=AvailabilityStatus.AVAILABLE,
            profile_status=DonorProfileStatus.ACTIVE,
            visibility_enabled=True,
        )
        record_consent(
            user=self.user,
            consent_type=ConsentType.DONOR_DISCOVERY,
            policy_version="draft-1",
            granted=True,
        )

        pause_donor_profile(user=self.user, profile=profile)
        profile.refresh_from_db()
        self.assertEqual(profile.availability_status, AvailabilityStatus.PAUSED)
        self.assertEqual(profile.profile_status, DonorProfileStatus.ACTIVE)

        deactivate_donor_profile(user=self.user, profile=profile)
        profile.refresh_from_db()
        self.assertEqual(profile.profile_status, DonorProfileStatus.HIDDEN)
        self.assertEqual(profile.availability_status, AvailabilityStatus.UNAVAILABLE)
        self.assertFalse(profile.visibility_enabled)
        latest_discovery = ConsentRecord.objects.filter(
            user=self.user,
            consent_type=ConsentType.DONOR_DISCOVERY,
        ).latest("captured_at")
        self.assertFalse(latest_discovery.granted)

    def test_deactivation_does_not_clear_moderator_suspension(self):
        profile = DonorProfile.objects.create(
            user=self.user,
            blood_group=BloodGroup.O_POSITIVE,
            division=self.division,
            district=self.district,
            profile_status=DonorProfileStatus.SUSPENDED,
            visibility_enabled=False,
        )

        deactivate_donor_profile(user=self.user, profile=profile)

        profile.refresh_from_db()
        self.assertEqual(profile.profile_status, DonorProfileStatus.SUSPENDED)
        self.assertEqual(profile.availability_status, AvailabilityStatus.UNAVAILABLE)

    def test_profile_editor_requires_authentication(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={self.url}")
