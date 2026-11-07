from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import AccountStatus
from apps.connections.models import (
    Connection,
    ContactRequest,
    ContactRequestStatus,
)
from apps.connections.services import (
    create_contact_request,
    get_disclosed_contact_channels,
    transition_contact_request,
)
from apps.donors.models import (
    AvailabilityStatus,
    BloodGroup,
    DonorProfile,
    DonorProfileStatus,
)
from apps.governance.models import ConsentType, record_consent
from apps.locations.models import Location, LocationLevel
from apps.moderation.services import create_user_block
from apps.notifications.models import (
    Notification,
    NotificationChannel,
    NotificationType,
)
from apps.notifications.tasks import process_notification, redrive_pending_notifications
from apps.requests.models import BloodRequestStatus, RequestUrgency
from apps.requests.services import create_blood_request

User = get_user_model()


class ContactRequestServiceTests(TestCase):
    def setUp(self):
        cache.clear()
        self.recipient = self.make_user("recipient@example.test")
        self.donor_user = self.make_user("donor@example.test")
        self.other_user = self.make_user("other@example.test")
        division = self.location("Synthetic division", LocationLevel.DIVISION)
        district = self.location("Synthetic district", LocationLevel.DISTRICT, division)
        self.donor = DonorProfile.objects.create(
            user=self.donor_user,
            blood_group=BloodGroup.O_POSITIVE,
            division=division,
            district=district,
            availability_status=AvailabilityStatus.AVAILABLE,
            visibility_enabled=True,
            profile_status=DonorProfileStatus.ACTIVE,
        )
        record_consent(
            user=self.donor_user,
            consent_type=ConsentType.DONOR_DISCOVERY,
            policy_version="draft-1",
            granted=True,
        )
        self.blood_request = create_blood_request(
            user=self.recipient,
            values={
                "blood_group": BloodGroup.O_POSITIVE,
                "units_requested": 1,
                "required_at": timezone.now() + timedelta(days=4),
                "division": division,
                "district": district,
                "urgency": RequestUrgency.NORMAL,
            },
            publish=True,
        )

    @staticmethod
    def make_user(email):
        user = User.objects.create_user(
            email=email,
            password="Synthetic-Unique-Password!947",
            display_name="Synthetic user",
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

    def create(self, **overrides):
        values = {
            "recipient": self.recipient,
            "donor_profile_id": self.donor.pk,
            "blood_request_id": self.blood_request.pk,
            "message": "Synthetic request message",
        }
        values.update(overrides)
        return create_contact_request(**values)

    def test_create_requires_discoverable_donor_and_owned_open_request(self):
        contact_request = self.create()
        self.assertEqual(contact_request.status, ContactRequestStatus.PENDING)
        self.assertEqual(contact_request.recipient, self.recipient)
        self.assertEqual(contact_request.message, "Synthetic request message")
        self.assertLessEqual(
            contact_request.expires_at,
            timezone.now() + timedelta(hours=48, seconds=2),
        )

        with self.assertRaises(ValidationError):
            self.create(recipient=self.other_user)
        with self.assertRaises(ValidationError):
            self.create(donor_profile_id="00000000-0000-0000-0000-000000000000")

    def test_duplicate_pending_request_is_rejected(self):
        first = self.create()
        with self.assertRaisesMessage(ValidationError, "already pending"):
            self.create()
        self.assertEqual(ContactRequest.objects.count(), 1)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ContactRequest.objects.bulk_create(
                    [
                        ContactRequest(
                            recipient=first.recipient,
                            donor_profile=first.donor_profile,
                            blood_request=first.blood_request,
                            status=ContactRequestStatus.PENDING,
                            expires_at=first.expires_at,
                        )
                    ]
                )

    def test_recipient_cannot_contact_own_donor_profile(self):
        own_profile = DonorProfile.objects.create(
            user=self.recipient,
            blood_group=BloodGroup.O_POSITIVE,
            division=self.donor.division,
            district=self.donor.district,
            availability_status=AvailabilityStatus.AVAILABLE,
            visibility_enabled=True,
            profile_status=DonorProfileStatus.ACTIVE,
        )
        record_consent(
            user=self.recipient,
            consent_type=ConsentType.DONOR_DISCOVERY,
            policy_version="draft-1",
            granted=True,
        )
        with self.assertRaisesMessage(ValidationError, "own donor profile"):
            self.create(donor_profile_id=own_profile.pk)

    def test_only_addressed_donor_accepts_or_declines(self):
        contact_request = self.create()
        with self.assertRaises(PermissionDenied):
            transition_contact_request(
                user=self.other_user,
                contact_request_id=contact_request.pk,
                target_status=ContactRequestStatus.ACCEPTED,
            )
        contact_request.refresh_from_db()
        self.assertEqual(contact_request.status, ContactRequestStatus.PENDING)

        accepted = transition_contact_request(
            user=self.donor_user,
            contact_request_id=contact_request.pk,
            target_status=ContactRequestStatus.ACCEPTED,
        )
        repeated = transition_contact_request(
            user=self.donor_user,
            contact_request_id=contact_request.pk,
            target_status=ContactRequestStatus.ACCEPTED,
        )
        self.assertEqual(accepted.status, ContactRequestStatus.ACCEPTED)
        self.assertEqual(repeated.pk, contact_request.pk)
        self.assertIsNotNone(repeated.decided_at)
        with self.assertRaises(PermissionDenied):
            transition_contact_request(
                user=self.other_user,
                contact_request_id=contact_request.pk,
                target_status=ContactRequestStatus.ACCEPTED,
            )
        with self.assertRaises(ValidationError):
            transition_contact_request(
                user=self.donor_user,
                contact_request_id=contact_request.pk,
                target_status=ContactRequestStatus.DECLINED,
            )

    def test_only_recipient_cancels_and_expired_decision_is_terminal(self):
        contact_request = self.create()
        with self.assertRaises(PermissionDenied):
            transition_contact_request(
                user=self.other_user,
                contact_request_id=contact_request.pk,
                target_status=ContactRequestStatus.CANCELLED,
            )
        cancelled = transition_contact_request(
            user=self.recipient,
            contact_request_id=contact_request.pk,
            target_status=ContactRequestStatus.CANCELLED,
        )
        self.assertEqual(cancelled.status, ContactRequestStatus.CANCELLED)

        expired_request = self.create()
        now = expired_request.expires_at + timedelta(seconds=1)
        expired = transition_contact_request(
            user=self.donor_user,
            contact_request_id=expired_request.pk,
            target_status=ContactRequestStatus.ACCEPTED,
            now=now,
        )
        self.assertEqual(expired.status, ContactRequestStatus.EXPIRED)
        with self.assertRaises(ValidationError):
            transition_contact_request(
                user=self.recipient,
                contact_request_id=expired_request.pk,
                target_status=ContactRequestStatus.CANCELLED,
                now=now,
            )

    def test_requester_must_own_an_open_unexpired_blood_request(self):
        self.blood_request.status = BloodRequestStatus.CANCELLED
        self.blood_request.save(update_fields=["status", "updated_at"])
        with self.assertRaisesMessage(ValidationError, "open, current"):
            self.create()

    def test_blocks_in_either_direction_prevent_new_contact_requests(self):
        create_user_block(blocker=self.recipient, blocked_user_id=self.donor_user.pk)
        with self.assertRaisesMessage(ValidationError, "not available for contact"):
            self.create()

        from apps.moderation.models import UserBlock

        UserBlock.objects.all().delete()
        create_user_block(blocker=self.donor_user, blocked_user_id=self.recipient.pk)
        with self.assertRaisesMessage(ValidationError, "not available for contact"):
            self.create()

    def test_composer_and_detail_pages_keep_private_contact_fields_hidden(self):
        self.client.force_login(self.recipient)
        response = self.client.get(
            reverse("connections:create"), {"donor": str(self.donor.pk)}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Blood donor — Synthetic district")
        self.assertNotContains(response, self.donor_user.email)
        self.assertNotContains(response, "phone_e164")

        response = self.client.post(
            reverse("connections:create"),
            {
                "donor_profile": str(self.donor.pk),
                "blood_request": str(self.blood_request.pk),
                "message": "Synthetic request message",
            },
        )
        contact_request = ContactRequest.objects.get()
        self.assertRedirects(
            response,
            reverse(
                "connections:outgoing_detail",
                kwargs={"contact_request_id": contact_request.pk},
            ),
        )
        self.assertNotContains(
            self.client.get(response.url), self.donor_user.email
        )

    def test_incoming_decision_actions_are_owner_scoped_and_post_only(self):
        contact_request = self.create()
        detail_url = reverse(
            "connections:incoming_detail",
            kwargs={"contact_request_id": contact_request.pk},
        )
        self.client.force_login(self.other_user)
        self.assertEqual(self.client.get(detail_url).status_code, 404)
        self.assertEqual(
            self.client.get(
                reverse(
                    "connections:action",
                    kwargs={"contact_request_id": contact_request.pk, "action": "accept"},
                )
            ).status_code,
            405,
        )

        self.client.force_login(self.donor_user)
        response = self.client.post(
            reverse(
                "connections:action",
                kwargs={"contact_request_id": contact_request.pk, "action": "accept"},
            )
        )
        self.assertEqual(response.status_code, 302)
        contact_request.refresh_from_db()
        self.assertEqual(contact_request.status, ContactRequestStatus.ACCEPTED)

    def test_expiry_service_expires_only_due_pending_requests_idempotently(self):
        from apps.connections.services import expire_due_contact_requests

        contact_request = self.create()
        now = contact_request.created_at + timedelta(seconds=2)
        ContactRequest.objects.filter(pk=contact_request.pk).update(
            expires_at=contact_request.created_at + timedelta(seconds=1)
        )
        self.assertEqual(expire_due_contact_requests(now=now), 1)
        self.assertEqual(expire_due_contact_requests(now=now), 0)
        contact_request.refresh_from_db()
        self.assertEqual(contact_request.status, ContactRequestStatus.EXPIRED)

    def test_connection_discloses_only_currently_consented_verified_channels(self):
        contact_request = self.create()
        with self.assertRaises(PermissionDenied):
            get_disclosed_contact_channels(
                recipient=self.recipient,
                connection_id=contact_request.pk,
            )

        transition_contact_request(
            user=self.donor_user,
            contact_request_id=contact_request.pk,
            target_status=ContactRequestStatus.ACCEPTED,
        )
        connection = Connection.objects.get(contact_request=contact_request)
        self.assertEqual(
            get_disclosed_contact_channels(
                recipient=self.recipient,
                connection_id=connection.pk,
            ),
            {},
        )

        self.donor_user.email_verified_at = timezone.now()
        self.donor_user.save(update_fields=["email_verified_at", "updated_at"])
        self.donor.refresh_from_db()
        self.donor.share_email_after_accept = True
        self.donor.save(update_fields=["share_email_after_accept", "updated_at"])
        record_consent(
            user=self.donor_user,
            consent_type=ConsentType.EMAIL_SHARE_AFTER_ACCEPT,
            policy_version="draft-1",
            granted=True,
        )
        channels = get_disclosed_contact_channels(
            recipient=self.recipient,
            connection_id=connection.pk,
        )
        self.assertEqual(channels, {"email": self.donor_user.email})
        with self.assertRaises(PermissionDenied):
            get_disclosed_contact_channels(
                recipient=self.other_user,
                connection_id=connection.pk,
            )

        record_consent(
            user=self.donor_user,
            consent_type=ConsentType.EMAIL_SHARE_AFTER_ACCEPT,
            policy_version="draft-1",
            granted=False,
        )
        self.assertEqual(
            get_disclosed_contact_channels(
                recipient=self.recipient,
                connection_id=connection.pk,
            ),
            {},
        )

    def test_connection_page_renders_only_after_acceptance_and_recipient_scope(self):
        contact_request = self.create()
        transition_contact_request(
            user=self.donor_user,
            contact_request_id=contact_request.pk,
            target_status=ContactRequestStatus.ACCEPTED,
        )
        connection = Connection.objects.get(contact_request=contact_request)
        self.donor_user.email_verified_at = timezone.now()
        self.donor_user.save(update_fields=["email_verified_at", "updated_at"])
        self.donor.refresh_from_db()
        self.donor.share_email_after_accept = True
        self.donor.save(update_fields=["share_email_after_accept", "updated_at"])
        record_consent(
            user=self.donor_user,
            consent_type=ConsentType.EMAIL_SHARE_AFTER_ACCEPT,
            policy_version="draft-1",
            granted=True,
        )

        url = reverse("connection_detail", kwargs={"connection_id": connection.pk})
        self.client.force_login(self.recipient)
        response = self.client.get(url)
        self.assertContains(response, self.donor_user.email)
        self.client.force_login(self.other_user)
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_contact_event_notifications_are_durable_minimized_and_idempotent(self):
        contact_request = self.create(message="Private synthetic message")
        received = Notification.objects.get(
            recipient=self.donor_user,
            notification_type=NotificationType.CONTACT_REQUEST_RECEIVED,
        )
        self.assertEqual(received.delivery_status, "PENDING")
        self.assertEqual(received.channel, "IN_APP")
        self.assertEqual(received.resource_id, contact_request.pk)
        self.assertNotIn("Private synthetic message", received.body)
        self.assertNotIn(self.recipient.email, received.body)
        self.assertEqual(process_notification.run(str(received.pk)), "sent")
        self.assertEqual(process_notification.run(str(received.pk)), "sent")
        received.refresh_from_db()
        self.assertEqual(received.delivery_status, "SENT")

        transition_contact_request(
            user=self.donor_user,
            contact_request_id=contact_request.pk,
            target_status=ContactRequestStatus.ACCEPTED,
        )
        transition_contact_request(
            user=self.donor_user,
            contact_request_id=contact_request.pk,
            target_status=ContactRequestStatus.ACCEPTED,
        )
        accepted = Notification.objects.get(
            recipient=self.recipient,
            notification_type=NotificationType.CONTACT_REQUEST_ACCEPTED,
        )
        self.assertNotIn(self.donor_user.email, accepted.body)
        self.assertEqual(Notification.objects.count(), 2)

    def test_pending_notifications_are_redriven_with_bounded_batch_and_stable_task_id(self):
        self.create()
        notification = Notification.objects.get(
            recipient=self.donor_user,
            notification_type=NotificationType.CONTACT_REQUEST_RECEIVED,
        )
        self.assertEqual(notification.delivery_status, "PENDING")
        self.assertEqual(redrive_pending_notifications.run(batch_size=1), 1)
        notification.refresh_from_db()
        self.assertEqual(notification.delivery_status, "SENT")
        self.assertEqual(redrive_pending_notifications.run(batch_size=1), 0)

    def test_notification_queue_failure_does_not_rollback_contact_creation(self):
        from unittest.mock import patch

        with patch(
            "apps.notifications.tasks.process_notification.apply_async",
            side_effect=ConnectionError("synthetic broker outage"),
        ):
            with self.captureOnCommitCallbacks(execute=True):
                contact_request = self.create()

        self.assertTrue(ContactRequest.objects.filter(pk=contact_request.pk).exists())
        notification = Notification.objects.get(
            recipient=self.donor_user,
            notification_type=NotificationType.CONTACT_REQUEST_RECEIVED,
        )
        self.assertEqual(notification.delivery_status, "PENDING")
        self.assertEqual(process_notification.max_retries, 3)
        self.assertEqual(redrive_pending_notifications.max_retries, 3)

    def test_notification_is_enqueued_after_commit_with_stable_uuid_task_id(self):
        from unittest.mock import patch

        with patch("apps.notifications.tasks.process_notification.apply_async") as enqueue:
            with self.captureOnCommitCallbacks(execute=True):
                contact_request = self.create()

        notification = Notification.objects.get(
            recipient=self.donor_user,
            notification_type=NotificationType.CONTACT_REQUEST_RECEIVED,
        )
        enqueue.assert_called_once_with(
            args=[str(notification.pk)],
            task_id=str(notification.pk),
        )
        self.assertEqual(contact_request.status, ContactRequestStatus.PENDING)

    def test_optional_email_delivery_uses_mock_and_rechecks_consent(self):
        self.donor_user.email_verified_at = timezone.now()
        self.donor_user.save(update_fields=["email_verified_at", "updated_at"])
        record_consent(
            user=self.donor_user,
            consent_type=ConsentType.OPTIONAL_NOTIFICATIONS,
            policy_version="draft-1",
            granted=True,
        )
        self.create()
        notification = Notification.objects.get(
            recipient=self.donor_user,
            notification_type=NotificationType.CONTACT_REQUEST_RECEIVED,
            channel=NotificationChannel.EMAIL,
        )
        self.assertEqual(notification.delivery_status, "PENDING")
        self.assertEqual(process_notification.run(str(notification.pk)), "sent")
        notification.refresh_from_db()
        self.assertEqual(notification.provider_reference, f"mock-email:{notification.pk}")
        self.assertNotIn(self.donor_user.email, notification.body)

    def test_optional_email_delivery_skips_after_consent_is_withdrawn(self):
        self.donor_user.email_verified_at = timezone.now()
        self.donor_user.save(update_fields=["email_verified_at", "updated_at"])
        record_consent(
            user=self.donor_user,
            consent_type=ConsentType.OPTIONAL_NOTIFICATIONS,
            policy_version="draft-1",
            granted=True,
        )
        self.create()
        notification = Notification.objects.get(
            recipient=self.donor_user,
            notification_type=NotificationType.CONTACT_REQUEST_RECEIVED,
            channel=NotificationChannel.EMAIL,
        )
        record_consent(
            user=self.donor_user,
            consent_type=ConsentType.OPTIONAL_NOTIFICATIONS,
            policy_version="draft-1",
            granted=False,
        )
        self.assertEqual(process_notification.run(str(notification.pk)), "skipped")

    def test_permanent_mock_provider_failure_is_recorded_without_rolling_back_request(self):
        from unittest.mock import patch

        self.donor_user.email_verified_at = timezone.now()
        self.donor_user.save(update_fields=["email_verified_at", "updated_at"])
        record_consent(
            user=self.donor_user,
            consent_type=ConsentType.OPTIONAL_NOTIFICATIONS,
            policy_version="draft-1",
            granted=True,
        )
        contact_request = self.create()
        notification = Notification.objects.get(
            recipient=self.donor_user,
            notification_type=NotificationType.CONTACT_REQUEST_RECEIVED,
            channel=NotificationChannel.EMAIL,
        )
        from apps.notifications.adapters import PermanentNotificationDeliveryError

        class FailingAdapter:
            def send(self, **kwargs):
                raise PermanentNotificationDeliveryError("synthetic provider rejection")

        with patch("apps.notifications.tasks.get_notification_adapter", return_value=FailingAdapter()):
            self.assertEqual(process_notification.run(str(notification.pk)), "failed")
        notification.refresh_from_db()
        self.assertEqual(notification.delivery_status, "FAILED")
        self.assertTrue(ContactRequest.objects.filter(pk=contact_request.pk).exists())

    @override_settings(NOTIFICATION_DELIVERY_MODE="disabled")
    def test_production_disabled_mode_never_creates_external_delivery_rows(self):
        self.donor_user.email_verified_at = timezone.now()
        self.donor_user.save(update_fields=["email_verified_at", "updated_at"])
        record_consent(
            user=self.donor_user,
            consent_type=ConsentType.OPTIONAL_NOTIFICATIONS,
            policy_version="draft-1",
            granted=True,
        )
        self.create()
        self.assertEqual(
            list(
                Notification.objects.filter(recipient=self.donor_user).values_list(
                    "channel", flat=True
                )
            ),
            [NotificationChannel.IN_APP],
        )

    def test_notification_list_and_read_action_are_owner_scoped(self):
        contact_request = self.create()
        notification = Notification.objects.get(
            recipient=self.donor_user,
            notification_type=NotificationType.CONTACT_REQUEST_RECEIVED,
        )
        list_url = reverse("notifications:list")
        self.client.force_login(self.donor_user)
        response = self.client.get(list_url)
        self.assertContains(response, "New contact request")
        self.assertContains(response, "Open contact request")

        read_url = reverse("notifications:read", kwargs={"notification_id": notification.pk})
        self.client.force_login(self.other_user)
        self.assertEqual(self.client.post(read_url).status_code, 404)
        self.client.force_login(self.donor_user)
        self.assertEqual(self.client.post(read_url).status_code, 302)
        notification.refresh_from_db()
        self.assertIsNotNone(notification.read_at)

    def test_contact_creation_endpoint_is_rate_limited(self):
        self.client.force_login(self.recipient)
        url = reverse("connections:create")
        payload = {
            "donor_profile": str(self.donor.pk),
            "blood_request": str(self.blood_request.pk),
            "message": "Synthetic request message",
        }
        for _ in range(12):
            self.assertEqual(self.client.get(url).status_code, 200)
        for _ in range(10):
            response = self.client.post(url, payload)
            self.assertNotEqual(response.status_code, 429)

        throttled = self.client.post(url, payload)
        self.assertEqual(throttled.status_code, 429)
        self.assertEqual(throttled["Retry-After"], "3600")
