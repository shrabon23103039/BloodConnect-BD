from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import AccountStatus
from apps.locations.models import Location, LocationLevel
from apps.requests.models import BloodRequest, BloodRequestStatus, RequestUrgency
from apps.requests.services import (
    create_blood_request,
    expire_due_blood_requests,
    transition_blood_request,
    update_blood_request,
)

User = get_user_model()


class BloodRequestLifecycleTests(TestCase):
    def setUp(self):
        self.user = self.make_user("requester@example.test")
        self.other_user = self.make_user("other@example.test")
        self.division = self.location("Synthetic division", LocationLevel.DIVISION)
        self.district = self.location(
            "Synthetic district", LocationLevel.DISTRICT, self.division
        )
        self.upazila = self.location(
            "Synthetic upazila", LocationLevel.UPAZILA, self.district
        )
        self.values = {
            "blood_group": "O+",
            "units_requested": 2,
            "required_at": timezone.now() + timedelta(hours=2),
            "division": self.division,
            "district": self.district,
            "upazila": self.upazila,
            "urgency": RequestUrgency.NORMAL,
        }

    def make_user(self, email):
        user = User.objects.create_user(
            email=email,
            password="Synthetic-Unique-Password!947",
            display_name="Synthetic Requester",
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

    def test_create_draft_default_expiry_and_publish(self):
        draft = create_blood_request(user=self.user, values=self.values)
        self.assertEqual(draft.status, BloodRequestStatus.DRAFT)
        self.assertEqual(draft.expires_at, draft.required_at)
        opened = create_blood_request(user=self.user, values=self.values, publish=True)
        self.assertEqual(opened.status, BloodRequestStatus.OPEN)

    def test_publish_rejects_past_required_or_expiry(self):
        values = {**self.values, "required_at": timezone.now() - timedelta(minutes=1)}
        values["expires_at"] = values["required_at"]
        with self.assertRaises(ValidationError):
            create_blood_request(user=self.user, values=values, publish=True)

    def test_owner_can_edit_open_request_but_other_user_cannot(self):
        request = create_blood_request(user=self.user, values=self.values, publish=True)
        updated = update_blood_request(
            user=self.user,
            blood_request_id=request.pk,
            values={"description": "Synthetic coordination note"},
        )
        self.assertEqual(updated.description, "Synthetic coordination note")
        with self.assertRaises(PermissionDenied):
            update_blood_request(
                user=self.other_user,
                blood_request_id=request.pk,
                values={"description": "Unauthorized"},
            )

    def test_owner_can_fulfill_or_cancel_and_terminal_state_cannot_change(self):
        request = create_blood_request(user=self.user, values=self.values, publish=True)
        fulfilled = transition_blood_request(
            user=self.user,
            blood_request_id=request.pk,
            target_status=BloodRequestStatus.FULFILLED,
        )
        self.assertEqual(fulfilled.status, BloodRequestStatus.FULFILLED)
        with self.assertRaises(ValidationError):
            update_blood_request(
                user=self.user,
                blood_request_id=request.pk,
                values={"description": "Too late"},
            )
        another = create_blood_request(user=self.user, values=self.values, publish=True)
        cancelled = transition_blood_request(
            user=self.user,
            blood_request_id=another.pk,
            target_status=BloodRequestStatus.CANCELLED,
        )
        self.assertEqual(cancelled.status, BloodRequestStatus.CANCELLED)

    def test_only_due_requests_expire_and_expiry_is_idempotent(self):
        due = create_blood_request(user=self.user, values=self.values, publish=True)
        future = create_blood_request(user=self.user, values=self.values, publish=True)
        now = due.created_at + timedelta(seconds=2)
        BloodRequest.objects.filter(pk=due.pk).update(
            expires_at=due.created_at + timedelta(seconds=1)
        )
        self.assertEqual(expire_due_blood_requests(now=now), 1)
        self.assertEqual(expire_due_blood_requests(now=now), 0)
        due.refresh_from_db()
        future.refresh_from_db()
        self.assertEqual(due.status, BloodRequestStatus.EXPIRED)
        self.assertEqual(future.status, BloodRequestStatus.OPEN)

    def test_expiry_transition_requires_due_open_request_and_owner(self):
        request = create_blood_request(user=self.user, values=self.values, publish=True)
        with self.assertRaises(ValidationError):
            transition_blood_request(
                user=self.user,
                blood_request_id=request.pk,
                target_status=BloodRequestStatus.EXPIRED,
            )
        with self.assertRaises(PermissionDenied):
            transition_blood_request(
                user=self.other_user,
                blood_request_id=request.pk,
                target_status=BloodRequestStatus.CANCELLED,
            )

    def test_schema_constraints_and_location_hierarchy(self):
        with self.assertRaises(ValidationError):
            create_blood_request(
                user=self.user,
                values={**self.values, "division": self.district},
            )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                BloodRequest.objects.bulk_create(
                    [
                        BloodRequest(
                            requester=self.user,
                            **{**self.values, "units_requested": 0},
                            expires_at=self.values["required_at"],
                        )
                    ]
                )
