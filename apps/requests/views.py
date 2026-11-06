from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from apps.accounts.models import AccountStatus
from apps.requests.forms import BloodRequestForm
from apps.requests.models import BloodRequest, BloodRequestStatus
from apps.requests.services import create_blood_request, transition_blood_request, update_blood_request


def _require_active(user):
    if user.account_status != AccountStatus.ACTIVE:
        raise PermissionDenied("An active account is required.")


def _owned_request(user, public_id):
    return get_object_or_404(BloodRequest, pk=public_id, requester=user)


@login_required
def request_list(request):
    _require_active(request.user)
    items = BloodRequest.objects.filter(requester=request.user).order_by("-created_at")
    return render(request, "requests/request_list.html", {"blood_requests": items})


@login_required
@require_http_methods(["GET", "POST"])
def request_create(request):
    _require_active(request.user)
    form = BloodRequestForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        publish = request.POST.get("action") == "publish"
        try:
            item = create_blood_request(user=request.user, values=form.cleaned_data, publish=publish)
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, "Request published." if publish else "Draft saved.")
            return redirect("requests:detail", public_id=item.pk)
    return render(request, "requests/request_form.html", {"form": form, "creating": True})


@login_required
def request_detail(request, public_id):
    _require_active(request.user)
    item = _owned_request(request.user, public_id)
    return render(request, "requests/request_detail.html", {"blood_request": item})


@login_required
@require_http_methods(["GET", "POST"])
def request_edit(request, public_id):
    _require_active(request.user)
    item = _owned_request(request.user, public_id)
    if item.status not in (BloodRequestStatus.DRAFT, BloodRequestStatus.OPEN):
        messages.error(request, "This request can no longer be edited.")
        return redirect("requests:detail", public_id=item.pk)
    form = BloodRequestForm(request.POST or None, instance=item)
    if request.method == "POST" and form.is_valid():
        publish = request.POST.get("action") == "publish"
        try:
            item = update_blood_request(user=request.user, blood_request_id=item.pk, values=form.cleaned_data)
            if publish and item.status == BloodRequestStatus.DRAFT:
                item = transition_blood_request(
                    user=request.user, blood_request_id=item.pk, target_status=BloodRequestStatus.OPEN
                )
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, "Request updated.")
            return redirect("requests:detail", public_id=item.pk)
    return render(request, "requests/request_form.html", {"form": form, "creating": False})


@login_required
@require_POST
def request_transition(request, public_id, target_status):
    _require_active(request.user)
    item = _owned_request(request.user, public_id)
    try:
        target_status = BloodRequestStatus(target_status)
        transition_blood_request(
            user=request.user, blood_request_id=item.pk, target_status=target_status
        )
    except (ValueError, ValidationError) as error:
        messages.error(request, str(error) or "That request action is not available.")
    else:
        messages.success(request, f"Request marked {target_status.label.lower()}.")
    return redirect("requests:detail", public_id=item.pk)
