"""Owner-scoped report and block services."""

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone

from apps.accounts.models import AccountStatus
from apps.accounts.permissions import AccountRole, has_role
from apps.audit.services import record_audit_event
from apps.audit.services import record_audit_event
from apps.moderation.models import ReportReason, UserBlock, UserReport
from apps.moderation.models import ReportStatus


def _active_user(user):
    if not user.is_authenticated or user.account_status != AccountStatus.ACTIVE:
        raise PermissionDenied("An active account is required.")
    return user.__class__.objects.select_for_update().get(pk=user.pk)


@transaction.atomic
def create_user_report(*, reporter, reported_user_id, reason, description):
    """Create a private user report with controlled reason and nonblank details."""
    reporter = _active_user(reporter)
    if reason not in ReportReason.values:
        raise ValidationError({"reason": "Select a supported report reason."})
    description = (description or "").strip()
    if not description:
        raise ValidationError({"description": "Describe the concern."})
    reported_user = reporter.__class__.objects.filter(pk=reported_user_id).first()
    if reported_user is None:
        raise ValidationError("This account is not available to report.")
    if reported_user.pk == reporter.pk:
        raise ValidationError({"reported_user": "You cannot report your own account."})
    report = UserReport.objects.create(
        reporter=reporter,
        reported_user=reported_user,
        reason=reason,
        description=description,
    )
    record_audit_event(
        actor=reporter,
        action="moderation.report.created",
        resource_type="user_report",
        resource_id=report.pk,
        metadata={"to_status": report.status, "reason_code": report.reason},
    )
    return report


@transaction.atomic
def create_user_block(*, blocker, blocked_user_id):
    """Create an idempotent block; only the blocker can view its relationship."""
    blocker = _active_user(blocker)
    blocked = blocker.__class__.objects.filter(pk=blocked_user_id).first()
    if blocked is None:
        raise ValidationError("This account is not available to block.")
    if blocked.pk == blocker.pk:
        raise ValidationError({"blocked_user": "You cannot block your own account."})
    try:
        with transaction.atomic():
            block, created = UserBlock.objects.get_or_create(blocker=blocker, blocked=blocked)
            if created:
                record_audit_event(
                    actor=blocker,
                    action="moderation.block.created",
                    resource_type="user_block",
                    resource_id=None,
                    metadata={"reason_code": "USER_REQUEST"},
                )
            return block
    except IntegrityError:
        return UserBlock.objects.get(blocker=blocker, blocked=blocked)


def is_blocked_between(*, user_a, user_b):
    """Return true if either user blocked the other."""
    if not user_a or not user_b or user_a.pk == user_b.pk:
        return False
    return UserBlock.objects.filter(
        Q(blocker_id=user_a.pk, blocked_id=user_b.pk)
        | Q(blocker_id=user_b.pk, blocked_id=user_a.pk)
    ).exists()


def get_report_for_reporter(*, reporter, report_id):
    """Return only the caller's report; moderators gain access in P6-02."""
    _active_user(reporter)
    try:
        return UserReport.objects.get(pk=report_id, reporter=reporter)
    except UserReport.DoesNotExist as error:
        raise PermissionDenied("You may only view reports you submitted.") from error


def _require_moderator(moderator):
    if not has_role(moderator, AccountRole.MODERATOR):
        raise PermissionDenied("An explicitly authorized moderator account is required.")


def list_reports_for_moderator(*, moderator, status=None):
    """Return report records only to active members of the MODERATOR group."""
    _require_moderator(moderator)
    reports = UserReport.objects.select_related("reporter", "reported_user", "assigned_admin")
    if status:
        if status not in ReportStatus.values:
            raise ValidationError({"status": "Select a supported report status."})
        reports = reports.filter(status=status)
    return reports.order_by("created_at", "id")


def get_report_for_moderator(*, moderator, report_id):
    """Fetch a report for an explicitly authorized moderator."""
    _require_moderator(moderator)
    try:
        return UserReport.objects.select_related(
            "reporter", "reported_user", "assigned_admin"
        ).get(pk=report_id)
    except UserReport.DoesNotExist as error:
        raise PermissionDenied("This report is unavailable.") from error


@transaction.atomic
def transition_user_report(*, moderator, report_id, target_status, resolution_note=""):
    """Apply an allowed report transition and append a redacted audit event."""
    _require_moderator(moderator)
    if target_status not in ReportStatus.values:
        raise ValidationError({"status": "Select a supported report status."})
    note = (resolution_note or "").strip()
    if len(note) > 1000:
        raise ValidationError({"resolution_note": "Keep the note to 1000 characters or fewer."})

    try:
        report = UserReport.objects.select_for_update().get(pk=report_id)
    except UserReport.DoesNotExist as error:
        raise PermissionDenied("This report is unavailable.") from error

    allowed = {
        ReportStatus.OPEN: {ReportStatus.UNDER_REVIEW, ReportStatus.RESOLVED, ReportStatus.DISMISSED},
        ReportStatus.UNDER_REVIEW: {ReportStatus.RESOLVED, ReportStatus.DISMISSED},
    }
    if target_status == report.status:
        return report
    if target_status not in allowed.get(report.status, set()):
        raise ValidationError({"status": "This report cannot transition to that status."})
    terminal = target_status in {ReportStatus.RESOLVED, ReportStatus.DISMISSED}
    if terminal and not note:
        raise ValidationError({"resolution_note": "A reason is required to resolve or dismiss a report."})

    previous = report.status
    report.status = target_status
    report.assigned_admin = moderator
    if terminal:
        report.resolution_note = note
        report.resolved_at = timezone.now()
        update_fields = ["status", "assigned_admin", "resolution_note", "resolved_at"]
    else:
        update_fields = ["status", "assigned_admin"]
    report.save(update_fields=update_fields)
    record_audit_event(
        actor=moderator,
        action="moderation.report.transition",
        resource_type="user_report",
        resource_id=report.pk,
        metadata={
            "from_status": previous,
            "to_status": target_status,
            "reason_code": "RESOLUTION_NOTE_PROVIDED" if terminal else "ASSIGNED_FOR_REVIEW",
        },
    )
    return report
