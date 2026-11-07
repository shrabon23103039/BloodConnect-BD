"""Moderator-only aggregate operations dashboard."""

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render

from apps.accounts.permissions import AccountRole, has_role
from apps.analytics.services import get_operational_metrics


@login_required
def operational_dashboard(request):
    if not has_role(request.user, AccountRole.MODERATOR):
        raise PermissionDenied("An explicitly authorized moderator account is required.")
    return render(
        request,
        "analytics/operational_dashboard.html",
        {"metrics": get_operational_metrics()},
    )
