"""Least-privilege server-rendered moderation workflows."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.permissions import AccountRole, has_role
from apps.moderation.forms import ReportTransitionForm
from apps.moderation.models import ReportStatus, UserReport
from apps.moderation.services import (
    get_report_for_moderator,
    list_reports_for_moderator,
    transition_user_report,
)


def _authorize(request):
    if not has_role(request.user, AccountRole.MODERATOR):
        raise PermissionDenied("An explicitly authorized moderator account is required.")


@login_required
def report_list(request):
    _authorize(request)
    status = request.GET.get("status") or None
    reports = list_reports_for_moderator(moderator=request.user, status=status)
    return render(
        request,
        "moderation/report_list.html",
        {"reports": reports, "status": status, "status_choices": ReportStatus.choices},
    )


@login_required
def report_detail(request, report_id):
    _authorize(request)
    report = get_report_for_moderator(moderator=request.user, report_id=report_id)
    form = ReportTransitionForm(report=report)
    return render(request, "moderation/report_detail.html", {"report": report, "form": form})


@login_required
@require_POST
def report_transition(request, report_id):
    _authorize(request)
    report = get_object_or_404(UserReport, pk=report_id)
    form = ReportTransitionForm(request.POST, report=report)
    if form.is_valid():
        try:
            transition_user_report(
                moderator=request.user,
                report_id=report.pk,
                target_status=form.cleaned_data["status"],
                resolution_note=form.cleaned_data["resolution_note"],
            )
        except ValidationError as error:
            for field, errors in getattr(error, "message_dict", {}).items():
                for message in errors:
                    form.add_error(field if field in form.fields else None, message)
        else:
            messages.success(request, "Report status updated.")
            return redirect("moderation:detail", report_id=report.pk)
    return render(request, "moderation/report_detail.html", {"report": report, "form": form}, status=400)
