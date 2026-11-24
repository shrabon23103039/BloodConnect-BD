from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import AccountStatus
from apps.locations.models import Location, LocationLevel
from apps.requests.models import BloodRequest, BloodRequestStatus, RequestLocationSource
from apps.requests.services import create_blood_request

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
            "request_location_label": "Synthetic General Area",
            "request_location_latitude": "23.74650000",
            "request_location_longitude": "90.37600000",
            "request_location_place_id": "synthetic-request-place",
            "request_location_source": RequestLocationSource.GOOGLE_PLACE,
            "request_location_confirmed": "true",
            "urgency": "NORMAL",
            "facility_name": "Synthetic clinic text",
            "facility_address": "Synthetic address text",
            "description": "Synthetic coordination request",
            "public_listing_enabled": "on",
        }
        values.update(overrides)
        return values

    def test_create_form_keeps_real_fields_location_picker_and_existing_actions(self):
        response = self.client.get(reverse("requests:create"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="app-shell app-shell--redesigned-workspace"')
        self.assertContains(response, 'href="/app/requests/" aria-current="page"')
        self.assertContains(response, 'href="/app/requests/"')
        self.assertContains(response, "Create blood request")
        self.assertContains(response, "request_form.css")
        self.assertContains(response, 'data-location-picker-mode="blood-request"')
        self.assertContains(response, 'name="csrfmiddlewaretoken"')
        self.assertContains(response, 'data-role="location-input"')
        self.assertContains(response, 'data-role="confirm-location"')
        self.assertContains(response, "Google receives your search query")
        self.assertContains(response, 'name="action" value="draft"')
        self.assertContains(response, 'name="action" value="publish"')
        self.assertContains(response, "Cancel")

        form = response.context["form"]
        for field_name in (
            "blood_group",
            "units_requested",
            "required_at",
            "urgency",
        ):
            self.assertTrue(form.fields[field_name].required)
        for field_name in (
            "description",
            "facility_name",
            "facility_address",
            "expires_at",
            "public_listing_enabled",
            "request_location_label",
            "request_location_latitude",
            "request_location_longitude",
            "request_location_place_id",
            "request_location_source",
            "request_location_confirmed",
        ):
            self.assertIn(field_name, form.fields)
        self.assertEqual(BloodRequest.objects.count(), 0)

    def test_create_publish_and_default_expiry(self):
        response = self.client.post(
            reverse("requests:create"), self.payload(action="publish")
        )
        self.assertEqual(response.status_code, 302)
        item = BloodRequest.objects.get(requester=self.user)
        self.assertEqual(item.status, BloodRequestStatus.OPEN)
        self.assertEqual(item.expires_at, item.required_at)
        self.assertEqual(item.request_location_label, "Synthetic General Area")
        self.assertEqual(item.request_location_source, RequestLocationSource.GOOGLE_PLACE)
        self.assertEqual(str(item.request_location_latitude), "23.74650000")
        self.assertEqual(str(item.request_location_longitude), "90.37600000")
        self.assertIsNotNone(item.request_location_confirmed_at)
        self.assertIsNone(item.division_id)
        detail = self.client.get(reverse("requests:detail", args=[item.pk]))
        self.assertContains(detail, "your phone and email remain private")
        self.assertContains(detail, "Synthetic General Area")
        self.assertNotContains(detail, "23.74650000")
        self.assertNotContains(detail, "synthetic-request-place")

    def test_publishing_requires_blood_group_and_confirmed_request_area(self):
        response = self.client.post(
            reverse("requests:create"),
            self.payload(
                blood_group="",
                request_location_label="",
                request_location_latitude="",
                request_location_longitude="",
                request_location_place_id="",
                request_location_source="",
                request_location_confirmed="false",
                action="publish",
            ),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(BloodRequest.objects.count(), 0)
        self.assertContains(response, "This field is required.")
        self.assertContains(response, 'class="request-create-field has-errors"')

    def test_request_area_can_be_updated_and_cleared_for_a_draft(self):
        self.client.post(reverse("requests:create"), self.payload(action="draft"))
        item = BloodRequest.objects.get(requester=self.user)
        response = self.client.post(
            reverse("requests:edit", args=[item.pk]),
            self.payload(
                request_location_label="Updated Synthetic Area",
                request_location_latitude="23.75000000",
                request_location_longitude="90.38000000",
                request_location_place_id="",
                request_location_source=RequestLocationSource.MAP_PIN,
                action="draft",
            ),
        )
        self.assertEqual(response.status_code, 302)
        item.refresh_from_db()
        self.assertEqual(item.request_location_label, "Updated Synthetic Area")
        self.assertEqual(item.request_location_source, RequestLocationSource.MAP_PIN)
        self.assertEqual(item.request_location_place_id, "")
        updated_confirmation = item.request_location_confirmed_at

        response = self.client.post(
            reverse("requests:edit", args=[item.pk]),
            self.payload(
                request_location_label="",
                request_location_latitude="",
                request_location_longitude="",
                request_location_place_id="",
                request_location_source="",
                request_location_confirmed="false",
                action="draft",
            ),
        )
        self.assertEqual(response.status_code, 302)
        item.refresh_from_db()
        self.assertEqual(item.request_location_label, "")
        self.assertIsNone(item.request_location_latitude)
        self.assertIsNone(item.request_location_longitude)
        self.assertEqual(item.request_location_source, "")
        self.assertIsNone(item.request_location_confirmed_at)
        self.assertIsNotNone(updated_confirmation)

    def test_legacy_request_area_still_renders_and_is_preserved(self):
        required = timezone.now() + timedelta(days=1)
        item = create_blood_request(
            user=self.user,
            values={
                "blood_group": "B+",
                "units_requested": 1,
                "required_at": required,
                "expires_at": required,
                "division": self.division,
                "district": self.district,
                "upazila": self.upazila,
                "urgency": "NORMAL",
            },
        )
        detail = self.client.get(reverse("requests:detail", args=[item.pk]))
        self.assertContains(detail, "Test upazila, Test district, Test division")
        self.client.get(reverse("requests:list"))
        item.refresh_from_db()
        self.assertEqual(item.division_id, self.division.pk)
        self.assertEqual(item.district_id, self.district.pk)
        self.assertIsNone(item.request_location_latitude)

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
        self.assertContains(response, "Synthetic General Area")
        self.assertNotContains(response, "No blood requests yet")

    def test_request_workspace_uses_dynamic_count_safe_area_and_existing_actions(self):
        self.client.post(
            reverse("requests:create"),
            self.payload(
                action="draft",
                request_location_source=RequestLocationSource.MAP_PIN,
                request_location_place_id="",
            ),
        )
        item = BloodRequest.objects.get(requester=self.user)
        response = self.client.get(reverse("requests:list"))

        self.assertContains(response, "Blood requests")
        self.assertContains(response, 'class="app-shell app-shell--redesigned-workspace"')
        self.assertContains(response, 'href="/app/requests/" aria-current="page"')
        self.assertContains(response, "My requests")
        self.assertContains(response, "Incoming")
        self.assertContains(response, "Outgoing")
        self.assertContains(response, 'class="request-tab-count">1</span>')
        self.assertContains(response, "Synthetic General Area")
        self.assertContains(response, "General area · pin adjusted")
        self.assertContains(response, '<table class="requests-table">')
        self.assertContains(response, "<th scope=\"col\">Location</th>")
        self.assertContains(response, reverse("requests:detail", args=[item.pk]))
        self.assertContains(response, reverse("requests:edit", args=[item.pk]))
        self.assertContains(response, reverse("requests:create"))
        self.assertContains(response, "Filter by status")
        self.assertNotContains(response, "23.74650000")
        self.assertNotContains(response, "synthetic-request-place")
        self.assertNotContains(response, "No blood requests yet")
        self.assertContains(response, reverse("safety"))
