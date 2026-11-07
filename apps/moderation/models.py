"""Private user reports and bilateral contact blocks."""

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.utils import timezone


class ReportReason(models.TextChoices):
    SAFETY_CONCERN = "SAFETY_CONCERN", "Safety concern"
    HARASSMENT = "HARASSMENT", "Harassment"
    SPAM = "SPAM", "Spam"
    IMPERSONATION = "IMPERSONATION", "Impersonation"
    INAPPROPRIATE_CONTENT = "INAPPROPRIATE_CONTENT", "Inappropriate content"
    OTHER = "OTHER", "Other"


class ReportStatus(models.TextChoices):
    OPEN = "OPEN", "Open"
    UNDER_REVIEW = "UNDER_REVIEW", "Under review"
    RESOLVED = "RESOLVED", "Resolved"
    DISMISSED = "DISMISSED", "Dismissed"


class UserReport(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="submitted_reports",
    )
    reported_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reports_against",
    )
    reason = models.CharField(max_length=40, choices=ReportReason.choices)
    description = models.CharField(max_length=1000)
    status = models.CharField(
        max_length=20,
        choices=ReportStatus.choices,
        default=ReportStatus.OPEN,
    )
    assigned_admin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="assigned_user_reports",
    )
    resolution_note = models.CharField(max_length=1000, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "moderation_userreport"
        indexes = [
            models.Index(fields=["status", "created_at"], name="report_status_created_idx"),
            models.Index(fields=["reporter", "created_at"], name="report_reporter_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(reason__in=ReportReason.values),
                name="report_reason_valid",
            ),
            models.CheckConstraint(
                condition=Q(status__in=ReportStatus.values),
                name="report_status_valid",
            ),
            models.CheckConstraint(
                condition=~Q(reporter=F("reported_user")),
                name="report_not_self",
            ),
        ]

    def clean(self):
        if self.reporter_id and self.reporter_id == self.reported_user_id:
            raise ValidationError({"reported_user": "You cannot report your own account."})
        if not self.description or not self.description.strip():
            raise ValidationError({"description": "Describe the concern."})

    def save(self, *args, **kwargs):
        if self.description:
            self.description = self.description.strip()
        self.full_clean()
        return super().save(*args, **kwargs)


class UserBlock(models.Model):
    blocker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="blocks_created",
    )
    blocked = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="blocks_received",
    )
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        db_table = "moderation_userblock"
        constraints = [
            models.UniqueConstraint(
                fields=["blocker", "blocked"],
                name="block_pair_unique",
            ),
            models.CheckConstraint(
                condition=~Q(blocker=F("blocked")),
                name="block_not_self",
            ),
        ]

    def clean(self):
        if self.blocker_id and self.blocker_id == self.blocked_id:
            raise ValidationError({"blocked": "You cannot block your own account."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
