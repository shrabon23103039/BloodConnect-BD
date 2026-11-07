"""Authenticated contact request pages and POST-only state actions."""

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from apps.accounts.models import AccountStatus
from apps.accounts.throttling import limited_by_ip
from apps.connections.forms import ContactRequestForm
from apps.connections.models import Connection, ContactRequest, ContactRequestStatus
from apps.connections.services import (
    create_contact_request,
    get_disclosed_contact_channels,
    transition_contact_request,
)


def _require_active_account(user):
    if user.account_status != AccountStatus.ACTIVE:
        raise PermissionDenied("An active account is required.")


@login_required
def contact_request_home(request):
    return redirect("connections:outgoing")


@login_required
def outgoing_contact_requests(request):
    _require_active_account(request.user)
    contact_requests = ContactRequest.objects.filter(
        recipient=request.user
    ).select_related("donor_profile", "donor_profile__district", "blood_request")
    return render(
        request,
        "connections/outgoing.html",
        {"contact_requests": contact_requests},
    )


@login_required
def incoming_contact_requests(request):
    _require_active_account(request.user)
    contact_requests = ContactRequest.objects.filter(
        donor_profile__user=request.user
    ).select_related("recipient", "blood_request")
    return render(
        request,
        "connections/incoming.html",
        {"contact_requests": contact_requests},
    )


@login_required
@limited_by_ip(
    scope="contact-create", limit=10, window_seconds=3600, methods={"POST"}
)
@require_http_methods(["GET", "POST"])
def create_contact_request_view(request):
    _require_active_account(request.user)
    if request.method == "POST":
        form = ContactRequestForm(
            request.POST,
            user=request.user,
            donor_profile_id=request.GET.get("donor"),
        )
        if form.is_valid():
            try:
                contact_request = create_contact_request(
                    recipient=request.user,
                    donor_profile_id=form.cleaned_data["donor_profile"].pk,
                    blood_request_id=form.cleaned_data["blood_request"].pk,
                    message=form.cleaned_data["message"],
                )
            except ValidationError as error:
                form.add_error(None, error)
            else:
                messages.success(request, "Your contact request was sent to the donor.")
                return redirect("connections:outgoing_detail", contact_request_id=contact_request.pk)
    else:
        form = ContactRequestForm(
            user=request.user,
            donor_profile_id=request.GET.get("donor"),
        )
    return render(request, "connections/create.html", {"form": form})


@login_required
def outgoing_contact_request_detail(request, contact_request_id):
    _require_active_account(request.user)
    contact_request = get_object_or_404(
        ContactRequest.objects.select_related("donor_profile", "blood_request"),
        pk=contact_request_id,
        recipient=request.user,
    )
    return render(
        request,
        "connections/detail.html",
        {"contact_request": contact_request, "audience": "recipient"},
    )


@login_required
def incoming_contact_request_detail(request, contact_request_id):
    _require_active_account(request.user)
    contact_request = get_object_or_404(
        ContactRequest.objects.select_related("recipient", "blood_request"),
        pk=contact_request_id,
        donor_profile__user=request.user,
    )
    return render(
        request,
        "connections/detail.html",
        {"contact_request": contact_request, "audience": "donor"},
    )


@login_required
@require_POST
def contact_request_action(request, contact_request_id, action):
    _require_active_account(request.user)
    transitions = {
        "accept": ContactRequestStatus.ACCEPTED,
        "decline": ContactRequestStatus.DECLINED,
        "cancel": ContactRequestStatus.CANCELLED,
    }
    if action not in transitions:
        raise Http404
    contact_request = get_object_or_404(ContactRequest, pk=contact_request_id)
    contact_request = transition_contact_request(
        user=request.user,
        contact_request_id=contact_request.pk,
        target_status=transitions[action],
    )
    if contact_request.status == ContactRequestStatus.EXPIRED:
        messages.info(request, "This contact request has expired.")
    else:
        messages.success(request, f"Contact request {contact_request.status.lower()}.")
    if contact_request.recipient_id == request.user.pk:
        return redirect("connections:outgoing_detail", contact_request_id=contact_request.pk)
    return redirect("connections:incoming_detail", contact_request_id=contact_request.pk)


@login_required
def accepted_connection_detail(request, connection_id):
    _require_active_account(request.user)
    connection = get_object_or_404(
        Connection.objects.select_related(
            "contact_request",
            "contact_request__donor_profile",
            "contact_request__blood_request",
        ),
        pk=connection_id,
    )
    channels = get_disclosed_contact_channels(
        recipient=request.user,
        connection_id=connection.pk,
    )
    return render(
        request,
        "connections/connection_detail.html",
        {"connection": connection, "channels": channels},
    )
