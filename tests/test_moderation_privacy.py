from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import AccountStatus
from apps.moderation.models import ReportReason, UserBlock
from apps.moderation.models import ReportStatus, UserReport
from apps.moderation.services import (
    create_user_block,
    create_user_report,
    get_report_for_reporter,
    is_blocked_between,
    list_reports_for_moderator,
    transition_user_report,
)
from apps.audit.models import AuditEvent

User = get_user_model()


class ReportAndBlockServiceTests(TestCase):
    def setUp(self):
        self.reporter = self.make_user("reporter@example.test")
        self.reported = self.make_user("reported@example.test")
        self.other = self.make_user("other@example.test")

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

    def test_report_requires_controlled_reason_and_cannot_target_self(self):
        report = create_user_report(
            reporter=self.reporter,
            reported_user_id=self.reported.pk,
            reason=ReportReason.HARASSMENT,
            description="  Synthetic report detail  ",
        )
        self.assertEqual(report.description, "Synthetic report detail")
        self.assertEqual(report.status, "OPEN")
        with self.assertRaises(ValidationError):
            create_user_report(
                reporter=self.reporter,
                reported_user_id=self.reporter.pk,
                reason=ReportReason.OTHER,
                description="Self report",
            )
        with self.assertRaises(ValidationError):
            create_user_report(
                reporter=self.reporter,
                reported_user_id=self.reported.pk,
                reason="UNSUPPORTED",
                description="Synthetic detail",
            )

    def test_report_details_are_private_to_reporter_until_moderator_workflow(self):
        report = create_user_report(
            reporter=self.reporter,
            reported_user_id=self.reported.pk,
            reason=ReportReason.SAFETY_CONCERN,
            description="Private synthetic report detail",
        )
        self.assertEqual(get_report_for_reporter(reporter=self.reporter, report_id=report.pk), report)
        with self.assertRaises(PermissionDenied):
            get_report_for_reporter(reporter=self.reported, report_id=report.pk)
        with self.assertRaises(PermissionDenied):
            get_report_for_reporter(reporter=self.other, report_id=report.pk)

    def test_block_creation_is_idempotent_and_relationship_is_bilateral(self):
        block = create_user_block(blocker=self.reporter, blocked_user_id=self.reported.pk)
        repeated = create_user_block(blocker=self.reporter, blocked_user_id=self.reported.pk)
        self.assertEqual(block.pk, repeated.pk)
        self.assertEqual(UserBlock.objects.count(), 1)
        self.assertTrue(is_blocked_between(user_a=self.reporter, user_b=self.reported))
        self.assertTrue(is_blocked_between(user_a=self.reported, user_b=self.reporter))
        self.assertFalse(is_blocked_between(user_a=self.reporter, user_b=self.other))

    def test_users_cannot_block_themselves(self):
        with self.assertRaises(ValidationError):
            create_user_block(blocker=self.reporter, blocked_user_id=self.reporter.pk)


class ModeratorWorkflowTests(ReportAndBlockServiceTests):
    def setUp(self):
        super().setUp()
        self.report = create_user_report(
            reporter=self.reporter,
            reported_user_id=self.reported.pk,
            reason=ReportReason.HARASSMENT,
            description="Private synthetic report detail with contact@example.test",
        )
        self.moderator = self.make_user("moderator@example.test")
        self.moderator_group = Group.objects.create(name="MODERATOR")
        self.moderator.groups.add(self.moderator_group)

    def test_only_explicit_active_moderator_group_can_review(self):
        staff = self.make_user("staff@example.test")
        staff.is_staff = True
        staff.save(update_fields=["is_staff"])
        for user in (self.reporter, self.reported, self.other, staff):
            with self.assertRaises(PermissionDenied):
                list_reports_for_moderator(moderator=user)
        self.assertEqual(list_reports_for_moderator(moderator=self.moderator).get(), self.report)

    def test_resolution_requires_reason_and_writes_minimized_audit_event(self):
        with self.assertRaises(ValidationError):
            transition_user_report(
                moderator=self.moderator,
                report_id=self.report.pk,
                target_status=ReportStatus.RESOLVED,
            )
        result = transition_user_report(
            moderator=self.moderator,
            report_id=self.report.pk,
            target_status=ReportStatus.RESOLVED,
            resolution_note="Reviewed synthetic report and applied policy.",
        )
        self.assertEqual(result.status, ReportStatus.RESOLVED)
        self.assertEqual(result.assigned_admin, self.moderator)
        self.assertIsNotNone(result.resolved_at)
        event = AuditEvent.objects.get(
            resource_id=self.report.pk,
            action="moderation.report.transition",
        )
        self.assertEqual(event.actor, self.moderator)
        self.assertEqual(event.metadata_redacted["from_status"], ReportStatus.OPEN)
        self.assertEqual(event.metadata_redacted["to_status"], ReportStatus.RESOLVED)
        serialized = str(event.metadata_redacted)
        self.assertNotIn("contact@example.test", serialized)
        self.assertNotIn("Reviewed synthetic", serialized)
        self.assertNotIn(self.report.description, serialized)

    def test_transition_rules_prevent_reopening_and_audit_under_review(self):
        transition_user_report(
            moderator=self.moderator,
            report_id=self.report.pk,
            target_status=ReportStatus.UNDER_REVIEW,
        )
        self.assertEqual(
            AuditEvent.objects.filter(action="moderation.report.transition").count(), 1
        )
        with self.assertRaises(ValidationError):
            transition_user_report(
                moderator=self.moderator,
                report_id=self.report.pk,
                target_status=ReportStatus.OPEN,
            )
        self.assertEqual(
            AuditEvent.objects.filter(action="moderation.report.transition").count(), 1
        )

    def test_moderation_pages_deny_non_moderators_and_transition_is_post_only(self):
        list_url = reverse("moderation:list")
        detail_url = reverse("moderation:detail", args=[self.report.pk])
        transition_url = reverse("moderation:transition", args=[self.report.pk])
        self.client.force_login(self.reported)
        self.assertEqual(self.client.get(list_url).status_code, 403)
        self.assertEqual(self.client.get(detail_url).status_code, 403)
        self.assertEqual(self.client.post(transition_url, {"status": ReportStatus.DISMISSED}).status_code, 403)
        self.client.force_login(self.moderator)
        self.assertEqual(self.client.get(list_url).status_code, 200)
        self.assertEqual(self.client.get(detail_url).status_code, 200)
        self.assertEqual(self.client.get(transition_url).status_code, 405)
        self.assertEqual(self.client.post(transition_url, {
            "status": ReportStatus.DISMISSED,
            "resolution_note": "Synthetic policy review.",
        }).status_code, 302)

    def test_reported_user_never_receives_reporter_identity(self):
        self.client.force_login(self.reported)
        self.assertEqual(self.client.get(reverse("moderation:list")).status_code, 403)
        response = self.client.get(reverse("moderation:detail", args=[self.report.pk]))
        self.assertEqual(response.status_code, 403)
