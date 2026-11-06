from django.contrib.auth import get_user_model
from django.test import TestCase
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


class DonorDiscoveryPolicyTests(TestCase):
    def setUp(self):
        self.division = self.location("Dhaka", LocationLevel.DIVISION)
        self.district = self.location("Dhaka", LocationLevel.DISTRICT, self.division)
        self.upazila = self.location("Dhamrai", LocationLevel.UPAZILA, self.district)
        self.user = self.make_user("visible@example.test")
        self.profile = self.make_profile(self.user)

    def location(self, name, level, parent=None, *, active=True):
        return Location.objects.create(
            name_en=name,
            level=level,
            parent=parent,
            is_active=active,
            source_name="Synthetic test fixture",
            source_version="synthetic-v1",
        )

    def make_user(self, email, status=AccountStatus.ACTIVE):
        user = User.objects.create_user(email=email, password="Synthetic-Unique-Password!947", display_name=email)
        user.account_status = status
        if status == AccountStatus.ACTIVE:
            user.email_verified_at = timezone.now()
            user.save(update_fields=["account_status", "email_verified_at", "updated_at"])
        else:
            user.save(update_fields=["account_status", "updated_at"])
        return user

    def make_profile(self, user, **overrides):
        values = {
            "user": user,
            "blood_group": BloodGroup.O_POSITIVE,
            "division": self.division,
            "district": self.district,
            "upazila": self.upazila,
            "availability_status": AvailabilityStatus.AVAILABLE,
            "visibility_enabled": True,
            "profile_status": DonorProfileStatus.ACTIVE,
        }
        values.update(overrides)
        return DonorProfile.objects.create(**values)

    def grant_discovery(self, user, granted=True):
        return record_consent(
            user=user,
            consent_type=ConsentType.DONOR_DISCOVERY,
            policy_version="draft-1",
            granted=granted,
        )

    def test_discoverable_queryset_requires_every_visibility_gate(self):
        self.grant_discovery(self.user)
        unavailable = self.make_profile(
            self.make_user("unavailable@example.test"),
            availability_status=AvailabilityStatus.UNAVAILABLE,
        )
        paused = self.make_profile(
            self.make_user("paused@example.test"),
            availability_status=AvailabilityStatus.PAUSED,
        )
        hidden = self.make_profile(
            self.make_user("hidden@example.test"),
            profile_status=DonorProfileStatus.HIDDEN,
        )
        hidden_unchecked = self.make_profile(
            self.make_user("unchecked@example.test"),
            visibility_enabled=False,
        )
        no_consent = self.make_profile(self.make_user("no-consent@example.test"))
        pending = self.make_profile(
            self.make_user("pending@example.test", AccountStatus.PENDING)
        )
        inactive_location = self.location(
            "Faridpur",
            LocationLevel.DISTRICT,
            self.division,
            active=False,
        )
        inactive_location_profile = DonorProfile.objects.create(
            user=self.make_user("inactive-location@example.test"),
            blood_group=BloodGroup.A_POSITIVE,
            division=self.division,
            district=inactive_location,
            availability_status=AvailabilityStatus.AVAILABLE,
            visibility_enabled=True,
            profile_status=DonorProfileStatus.ACTIVE,
        )
        self.grant_discovery(inactive_location_profile.user)

        self.assertEqual(list(DonorProfile.objects.discoverable()), [self.profile])
        self.assertEqual(
            set(DonorProfile.objects.exclude(pk=self.profile.pk).values_list("pk", flat=True)),
            {unavailable.pk, paused.pk, hidden.pk, hidden_unchecked.pk, no_consent.pk, pending.pk, inactive_location_profile.pk},
        )

    def test_consent_withdrawal_hides_stale_visible_profile_immediately(self):
        self.grant_discovery(self.user, granted=True)
        self.assertEqual(list(DonorProfile.objects.discoverable()), [self.profile])

        self.grant_discovery(self.user, granted=False)

        self.profile.refresh_from_db()
        self.assertTrue(self.profile.visibility_enabled)
        self.assertFalse(DonorProfile.objects.discoverable().exists())

    def test_owner_visibility_and_availability_controls_record_current_consent(self):
        client = self.client
        client.force_login(self.user)
        response = client.post(
            reverse("donors:profile"),
            {
                "action": "save",
                "blood_group": BloodGroup.O_POSITIVE,
                "division": str(self.division.pk),
                "district": str(self.district.pk),
                "upazila": str(self.upazila.pk),
                "availability_status": AvailabilityStatus.AVAILABLE,
                "visibility_enabled": "on",
                "public_alias": "Visible Donor",
                "preferred_contact_method": "IN_APP",
                "last_donation_date": "",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.profile_status, DonorProfileStatus.ACTIVE)
        self.assertTrue(self.profile.visibility_enabled)
        self.assertEqual(list(DonorProfile.objects.discoverable()), [self.profile])

        response = client.post(
            reverse("donors:profile"),
            {
                "action": "save",
                "blood_group": BloodGroup.O_POSITIVE,
                "division": str(self.division.pk),
                "district": str(self.district.pk),
                "upazila": str(self.upazila.pk),
                "availability_status": AvailabilityStatus.UNAVAILABLE,
                "public_alias": "Visible Donor",
                "preferred_contact_method": "IN_APP",
                "last_donation_date": "",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.availability_status, AvailabilityStatus.UNAVAILABLE)
        self.assertFalse(self.profile.visibility_enabled)
        self.assertFalse(DonorProfile.objects.discoverable().exists())
