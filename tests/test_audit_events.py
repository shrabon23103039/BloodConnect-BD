from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.accounts.models import AccountStatus
from apps.audit.models import AuditEvent
from apps.audit.services import record_audit_event
from apps.governance.models import ConsentType, record_consent


User = get_user_model()


class AuditEventTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="audit-user@example.test",
            password="Synthetic-Unique-Password!947",
            display_name="Synthetic audit user",
        )
        self.user.account_status = AccountStatus.ACTIVE
        self.user.save(update_fields=["account_status", "updated_at"])

    def test_audit_metadata_has_a_strict_allowlist(self):
        with self.assertRaises(ValueError):
            record_audit_event(
                actor=self.user,
                action="privacy.consent.changed",
                resource_type="consent_record",
                metadata={"email": self.user.email},
            )

    def test_consent_changes_write_minimized_audit_events(self):
        record_consent(
            user=self.user,
            consent_type=ConsentType.OPTIONAL_NOTIFICATIONS,
            policy_version="test-v1",
            granted=True,
        )
        event = AuditEvent.objects.get(action="privacy.consent.changed")
        self.assertEqual(event.actor, self.user)
        self.assertEqual(event.metadata_redacted["reason_code"], ConsentType.OPTIONAL_NOTIFICATIONS)
        self.assertEqual(event.metadata_redacted["to_status"], "GRANTED")
        self.assertNotIn(self.user.email, str(event.metadata_redacted))

    def test_audit_events_are_append_only(self):
        event = record_audit_event(
            actor=self.user,
            action="test.event",
            resource_type="test_resource",
        )
        event.action = "changed"
        with self.assertRaises(ValueError):
            event.save()
        with self.assertRaises(ValueError):
            event.delete()
