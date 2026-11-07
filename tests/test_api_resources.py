from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import AccountStatus
from apps.api.token_services import issue_token_pair
from apps.connections.models import ContactRequest, ContactRequestStatus
from apps.donors.models import (
    AvailabilityStatus,
    BloodGroup,
    DonorProfile,
    DonorProfileStatus,
)
from apps.governance.models import ConsentType, record_consent
from apps.locations.models import Location, LocationLevel
from apps.requests.models import BloodRequest
from apps.requests.services import create_blood_request


User = get_user_model()


class ApiResourceTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.division = self.location("Synthetic division", LocationLevel.DIVISION)
        self.district = self.location("Synthetic district", LocationLevel.DISTRICT, self.division)
        self.upazila = self.location("Synthetic upazila", LocationLevel.UPAZILA, self.district)
        self.recipient = self.make_user("api-recipient@example.test")
        self.donor_user = self.make_user("api-donor@example.test", verified_email=True)
        self.other = self.make_user("api-other@example.test")
        self.donor = DonorProfile.objects.create(
            user=self.donor_user,
            blood_group=BloodGroup.O_POSITIVE,
            division=self.division,
            district=self.district,
            upazila=self.upazila,
            availability_status=AvailabilityStatus.AVAILABLE,
            visibility_enabled=True,
            profile_status=DonorProfileStatus.ACTIVE,
            public_alias="Public synthetic alias",
            share_email_after_accept=True,
        )
        record_consent(
            user=self.donor_user,
            consent_type=ConsentType.DONOR_DISCOVERY,
            policy_version="draft-1",
            granted=True,
        )
        record_consent(
            user=self.donor_user,
            consent_type=ConsentType.EMAIL_SHARE_AFTER_ACCEPT,
            policy_version="draft-1",
            granted=True,
        )
        self.blood_request = create_blood_request(
            user=self.recipient,
            values=self.request_values(),
            publish=True,
        )

    @staticmethod
    def location(name, level, parent=None):
        return Location.objects.create(
            name_en=name,
            level=level,
            parent=parent,
            source_name="Synthetic API fixture",
            source_version="synthetic-v1",
        )

    @staticmethod
    def make_user(email, *, verified_email=False):
        user = User.objects.create_user(
            email=email,
            password="Synthetic-Unique-Password!947",
            display_name="Synthetic API person",
        )
        user.account_status = AccountStatus.ACTIVE
        if verified_email:
            user.email_verified_at = timezone.now()
        user.save(update_fields=["account_status", "email_verified_at", "updated_at"])
        return user

    def request_values(self):
        return {
            "blood_group": BloodGroup.O_POSITIVE,
            "units_requested": 1,
            "required_at": timezone.now() + timedelta(days=2),
            "division": self.division,
            "district": self.district,
            "upazila": self.upazila,
            "facility_name": "Private synthetic facility",
            "facility_address": "Private synthetic address",
            "urgency": "NORMAL",
            "description": "Private synthetic description",
            "public_listing_enabled": True,
            "expires_at": timezone.now() + timedelta(days=3),
        }

    def authenticate(self, user):
        token_pair = issue_token_pair(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token_pair['access_token']}")
        return token_pair

    def test_guest_donor_search_is_paginated_and_consent_gated(self):
        response = self.client.get(reverse("api_v1:donor_list"))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["count"], 1)
        donor = payload["results"][0]
        self.assertEqual(donor["public_alias"], "Public synthetic alias")
        self.assertNotIn("email", donor)
        self.assertNotIn("phone_e164", donor)
        self.assertNotIn("user", donor)
        self.assertNotIn(self.donor_user.email, str(payload))

        private_user = self.make_user("no-consent@example.test")
        DonorProfile.objects.create(
            user=private_user,
            blood_group=BloodGroup.A_POSITIVE,
            division=self.division,
            district=self.district,
            availability_status=AvailabilityStatus.AVAILABLE,
            visibility_enabled=True,
            profile_status=DonorProfileStatus.ACTIVE,
        )
        self.assertEqual(self.client.get(reverse("api_v1:donor_list")).json()["count"], 1)

    def test_blood_request_public_and_owner_serialization_and_permissions(self):
        list_response = self.client.get(reverse("api_v1:blood_request_list"))
        self.assertEqual(list_response.status_code, 200)
        public_item = list_response.json()["results"][0]
        self.assertNotIn("facility_address", public_item)
        self.assertNotIn("description", public_item)
        self.assertNotIn(self.recipient.email, str(public_item))

        detail_url = reverse("api_v1:blood_request_detail", args=[self.blood_request.pk])
        self.assertNotIn("facility_address", self.client.get(detail_url).json())
        self.authenticate(self.recipient)
        owner_response = self.client.get(detail_url)
        self.assertEqual(owner_response.status_code, 200)
        self.assertEqual(owner_response.json()["facility_address"], "Private synthetic address")
        self.assertEqual(owner_response.json()["description"], "Private synthetic description")

        # Keep the model's expiry-after-creation invariant while making the
        # request expired relative to the time the API reads it.
        BloodRequest.objects.filter(pk=self.blood_request.pk).update(
            expires_at=self.blood_request.created_at + timedelta(microseconds=1)
        )
        self.client.credentials()
        self.assertEqual(self.client.get(detail_url).status_code, 404)
        self.authenticate(self.recipient)
        self.assertEqual(self.client.get(detail_url).status_code, 200)

        self.client.credentials()
        unauthenticated = self.client.post(
            reverse("api_v1:blood_request_list"),
            {"blood_group": "O+", "units_requested": 1},
            format="json",
        )
        self.assertEqual(unauthenticated.status_code, 401)

        self.authenticate(self.other)
        forbidden_update = self.client.patch(
            detail_url,
            {"description": "Attempted unauthorized change"},
            format="json",
        )
        self.assertEqual(forbidden_update.status_code, 403)

    def test_blood_request_create_update_and_close_use_domain_lifecycle(self):
        self.authenticate(self.recipient)
        values = self.request_values()
        values["division"] = str(self.division.pk)
        values["district"] = str(self.district.pk)
        values["upazila"] = str(self.upazila.pk)
        values["required_at"] = values["required_at"].isoformat()
        values["expires_at"] = values["expires_at"].isoformat()
        created = self.client.post(reverse("api_v1:blood_request_list"), values, format="json")
        self.assertEqual(created.status_code, 201, created.data)
        request_id = created.data["id"]
        self.assertEqual(created.data["status"], "OPEN")
        self.assertEqual(created.data["facility_address"], "Private synthetic address")

        updated = self.client.patch(
            reverse("api_v1:blood_request_detail", args=[request_id]),
            {"description": "Updated private synthetic description"},
            format="json",
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.data["description"], "Updated private synthetic description")

        closed = self.client.post(
            reverse("api_v1:blood_request_transition", args=[request_id, "close"]),
            {},
            format="json",
        )
        self.assertEqual(closed.status_code, 200)
        self.assertEqual(closed.data["status"], "FULFILLED")

    def test_contact_request_participants_and_post_accept_consent_disclosure(self):
        create_url = reverse("api_v1:contact_request_list")
        self.authenticate(self.recipient)
        created = self.client.post(
            create_url,
            {
                "donor_id": str(self.donor.pk),
                "blood_request_id": str(self.blood_request.pk),
                "message": "Synthetic private contact message",
            },
            format="json",
        )
        self.assertEqual(created.status_code, 201)
        contact_request_id = created.json()["id"]
        detail_url = reverse("api_v1:contact_request_detail", args=[contact_request_id])
        pending = self.client.get(detail_url)
        self.assertEqual(pending.json()["contact"], None)
        self.assertEqual(pending.json()["message"], "Synthetic private contact message")
        self.assertNotIn(self.donor_user.email, str(pending.json()))

        self.authenticate(self.other)
        self.assertEqual(self.client.get(detail_url).status_code, 404)
        self.authenticate(self.donor_user)
        accepted = self.client.post(
            reverse("api_v1:contact_request_action", args=[contact_request_id, "accept"]),
            {},
            format="json",
        )
        self.assertEqual(accepted.status_code, 200)
        self.assertEqual(accepted.json()["status"], ContactRequestStatus.ACCEPTED)
        self.assertIsNone(accepted.json()["contact"])

        self.authenticate(self.recipient)
        disclosed = self.client.get(detail_url)
        self.assertEqual(disclosed.json()["contact"], {"email": self.donor_user.email})
        self.assertEqual(ContactRequest.objects.get(pk=contact_request_id).status, ContactRequestStatus.ACCEPTED)
        connection = self.client.get(reverse("api_v1:connection_list"))
        self.assertEqual(connection.status_code, 200)
        connection_id = connection.json()["results"][0]["id"]
        connection_detail_url = reverse("api_v1:connection_detail", args=[connection_id])
        self.assertEqual(
            self.client.get(connection_detail_url).json()["contact"],
            {"email": self.donor_user.email},
        )
        self.authenticate(self.other)
        self.assertEqual(self.client.get(connection_detail_url).status_code, 404)
        self.authenticate(self.recipient)
        record_consent(
            user=self.donor_user,
            consent_type=ConsentType.EMAIL_SHARE_AFTER_ACCEPT,
            policy_version="draft-1",
            granted=False,
        )
        self.assertIsNone(self.client.get(detail_url).json()["contact"])
        close = self.client.post(
            reverse("api_v1:connection_action", args=[connection_id, "close"]),
            {},
            format="json",
        )
        self.assertEqual(close.status_code, 200)
        self.assertEqual(close.json()["status"], "CLOSED")
        self.assertIsNone(close.json()["contact"])

    def test_validation_errors_use_request_correlated_safe_envelope(self):
        self.authenticate(self.recipient)
        response = self.client.post(
            reverse("api_v1:contact_request_list"),
            {},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"]["code"], "VALIDATION_ERROR")
        self.assertIn("donor_id", response.data["error"]["fields"])
        self.assertEqual(response.data["error"]["request_id"], response["X-Request-ID"])

    def test_api_search_throttle_uses_safe_error_envelope(self):
        url = reverse("api_v1:donor_list")
        for _ in range(30):
            self.assertEqual(self.client.get(url).status_code, 200)
        throttled = self.client.get(url)
        self.assertEqual(throttled.status_code, 429)
        self.assertEqual(throttled.json()["error"]["code"], "RATE_LIMITED")
        self.assertEqual(throttled["Retry-After"], "60")
        self.assertEqual(throttled.json()["error"]["request_id"], throttled["X-Request-ID"])
