from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import AccountStatus
from apps.locations.models import Location, LocationLevel
from apps.requests.models import BloodRequest, BloodRequestStatus

User = get_user_model()


class BloodRequestWebFlowTests(TestCase):
    def setUp(self):
        self.user = self.make_user("requester@example.test")
        self.other_user = self.make_user("other@example.test")
        self.division = self.location("Test division", LocationLevel.DIVISION)
        self.district = self.location("Test district", LocationLevel.DISTRICT, self.division)
        self.upazila = self.location("Test upazila", LocationLevel.UPAZILA, self.district)
        self.client.force_login(self.user)

    @staticmethod
    def make_user(email):
        user = User.objects.create_user(
            email=email,
            password="Synthetic-Unique-Password!947",
            display_name="Synthetic User",
        )
        user.account_status = AccountStatus.ACTIVE
        user.save(update_fields=["account_status", "updated_at"])
        return user

    @staticmethod
    def location(name, level, parent=None):
        return Location.objects.create(
            name_en=name,
            level=level,
            parent=parent,
            source_name="Synthetic test fixture",
            source_version="synthetic-v1",
        )

    def payload(self, **overrides):
        required = timezone.now() + timedelta(days=1)
        values = {
            "blood_group": "A+",
            "units_requested": "1",
            "required_at": required.strftime("%Y-%m-%dT%H:%M"),
            "division": str(self.division.pk),
            "district": str(self.district.pk),
            "upazila": str(self.upazila.pk),
            "urgency": "NORMAL",
            "facility_name": "Synthetic clinic text",
            "facility_address": "Synthetic address text",
            "description": "Synthetic coordination request",
            "public_listing_enabled": "on",
        }
        values.update(overrides)
        return values

    def test_create_publish_and_default_expiry(self):
        response = self.client.post(
            reverse("requests:create"), self.payload(action="publish")
        )
        self.assertEqual(response.status_code, 302)
        item = BloodRequest.objects.get(requester=self.user)
        self.assertEqual(item.status, BloodRequestStatus.OPEN)
        self.assertEqual(item.expires_at, item.required_at)
        detail = self.client.get(reverse("requests:detail", args=[item.pk]))
        self.assertContains(detail, "your phone and email remain private")

    def test_save_draft_then_edit_and_publish(self):
        response = self.client.post(
            reverse("requests:create"), self.payload(action="draft")
        )
        item = BloodRequest.objects.get(requester=self.user)
        self.assertEqual(item.status, BloodRequestStatus.DRAFT)
        response = self.client.post(
            reverse("requests:edit", args=[item.pk]),
            self.payload(description="Updated synthetic note", action="publish"),
        )
        self.assertEqual(response.status_code, 302)
        item.refresh_from_db()
        self.assertEqual(item.status, BloodRequestStatus.OPEN)
        self.assertEqual(item.description, "Updated synthetic note")

    def test_owner_can_cancel_or_report_outcome_only_with_post(self):
        self.client.post(reverse("requests:create"), self.payload(action="publish"))
        item = BloodRequest.objects.get(requester=self.user)
        transition_url = reverse(
            "requests:transition", args=[item.pk, BloodRequestStatus.CANCELLED]
        )
        self.assertEqual(self.client.get(transition_url).status_code, 405)
        self.assertEqual(self.client.post(transition_url).status_code, 302)
        item.refresh_from_db()
        self.assertEqual(item.status, BloodRequestStatus.CANCELLED)

    def test_owner_can_report_outcome_and_closed_request_cannot_be_edited(self):
        self.client.post(reverse("requests:create"), self.payload(action="publish"))
        item = BloodRequest.objects.get(requester=self.user)
        close_url = reverse(
            "requests:transition", args=[item.pk, BloodRequestStatus.FULFILLED]
        )
        self.assertEqual(self.client.post(close_url).status_code, 302)
        item.refresh_from_db()
        self.assertEqual(item.status, BloodRequestStatus.FULFILLED)
        self.assertEqual(
            self.client.get(reverse("requests:edit", args=[item.pk])).status_code, 302
        )

    def test_other_account_cannot_read_or_edit_request(self):
        self.client.post(reverse("requests:create"), self.payload(action="publish"))
        item = BloodRequest.objects.get(requester=self.user)
        self.client.force_login(self.other_user)
        self.assertEqual(self.client.get(reverse("requests:detail", args=[item.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("requests:edit", args=[item.pk])).status_code, 404)

    def test_list_contains_only_current_users_requests(self):
        self.client.post(reverse("requests:create"), self.payload(action="draft"))
        response = self.client.get(reverse("requests:list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["blood_requests"].values_list("requester_id", flat=True)), [self.user.pk])
