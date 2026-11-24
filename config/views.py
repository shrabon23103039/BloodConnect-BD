from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_GET

from apps.connections.models import ContactRequest, ContactRequestStatus
from apps.locations.models import Location, LocationLevel
from apps.requests.models import BloodRequest, BloodRequestStatus


def home(request):
    """Keep the public landing page for guests and show the app home to members."""
    if not request.user.is_authenticated:
        return render(request, "pages/home.html")
    if not request.user.is_active:
        raise PermissionDenied

    now = timezone.now()
    user = request.user
    open_request_count = BloodRequest.objects.filter(
        requester=user,
        status=BloodRequestStatus.OPEN,
        expires_at__gt=now,
    ).count()
    pending_contact_request_count = ContactRequest.objects.filter(
        donor_profile__user=user,
        status=ContactRequestStatus.PENDING,
        expires_at__gt=now,
    ).count()
    recent_requests = BloodRequest.objects.filter(requester=user).order_by("-created_at")[:4]
    has_reviewed_area_filters = Location.objects.filter(
        level=LocationLevel.DIVISION,
        is_active=True,
    ).exists()

    return render(
        request,
        "pages/dashboard.html",
        {
            "open_request_count": open_request_count,
            "pending_contact_request_count": pending_contact_request_count,
            "recent_requests": recent_requests,
            "has_reviewed_area_filters": has_reviewed_area_filters,
        },
    )


def _render_system_error(request, status, *, page_title, heading, copy):
    if getattr(request, "user", None) and request.user.is_authenticated:
        template_name = "pages/app_error.html"
    else:
        template_name = "pages/public_error.html"
    return render(
        request,
        template_name,
        {
            "error_status": status,
            "error_title": page_title,
            "error_heading": heading,
            "error_copy": copy,
        },
        status=status,
    )


def bad_request(request, exception=None):
    return _render_system_error(
        request,
        400,
        page_title="Invalid request",
        heading="We couldn't process that request",
        copy="Check the submitted information and try again.",
    )


def permission_denied(request, exception=None):
    return _render_system_error(
        request,
        403,
        page_title="Access denied",
        heading="You don't have access to this page",
        copy="You may need to sign in with an authorized account.",
    )


def not_found(request, exception=None):
    return _render_system_error(
        request,
        404,
        page_title="Page not found",
        heading="This page is not available",
        copy="The link may be outdated or the page may no longer be available.",
    )


def server_error(request):
    return _render_system_error(
        request,
        500,
        page_title="Unexpected error",
        heading="Something went wrong",
        copy="Please try again. No account or private record information was included in this message.",
    )


@require_GET
def location_demo(request):
    if not settings.DEBUG:
        raise Http404
    return render(
        request,
        "demos/location_demo.html",
        {
            "google_maps_browser_api_key": getattr(settings, "GOOGLE_MAPS_BROWSER_API_KEY", ""),
        },
    )
