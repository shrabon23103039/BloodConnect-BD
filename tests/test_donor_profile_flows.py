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

    def location(self, name, level, parent=None):
        return Location.objects.create(
            name_en=name,
            level=level,
            parent=parent,
            source_name="Synthetic test fixture",
            source_version="synthetic-v1",
        )

    def profile_data(self, **overrides):
        data = {
            "blood_group": BloodGroup.O_POSITIVE,
            "division": str(self.division.pk),
            "district": str(self.district.pk),
            "upazila": str(self.upazila.pk),
            "public_alias": "Kind Donor",
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

    def test_profile_editor_requires_authentication(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={self.url}")
