from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.core.paginator import Paginator
from django.shortcuts import redirect, render
from django.utils.http import urlencode
from django.views.decorators.http import require_http_methods

from apps.accounts.throttling import limited_by_ip
from apps.donors.forms import DonorProfileForm
from apps.donors.models import AvailabilityStatus, DonorProfile
from apps.donors.search_forms import DonorSearchForm
from apps.donors.services import (
    deactivate_donor_profile,
    pause_donor_profile,
    save_donor_profile,
)

DONOR_SEARCH_PAGE_SIZE = 20


@limited_by_ip(scope="donor-search", limit=30, window_seconds=60)
def donor_search(request):
    form = DonorSearchForm(request.GET or None)
    profiles = DonorProfile.objects.none()
    if not form.is_bound or form.is_valid():
        profiles = DonorProfile.objects.discoverable().filter(
            availability_status=AvailabilityStatus.AVAILABLE
        )
        if form.is_bound:
            filters = form.cleaned_data
            for field in ("blood_group", "division", "district", "upazila"):
                value = filters.get(field)
                if value:
                    profiles = profiles.filter(**{field: value})
        profiles = (
            profiles.select_related("division", "district", "upazila")
            .only(
                "id",
                "public_alias",
                "blood_group",
                "availability_status",
                "division__name_en",
                "district__name_en",
                "upazila__name_en",
            )
            .order_by("district__name_en", "public_alias", "id")
        )
    paginator = Paginator(profiles, DONOR_SEARCH_PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get("page"))
    query_params = request.GET.copy()
    query_params.pop("page", None)
    return render(
        request,
        "donors/search.html",
        {
            "form": form,
            "page_obj": page_obj,
            "query_string": urlencode(query_params),
            "invalid_filters": form.is_bound and not form.is_valid(),
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def donor_profile_editor(request):
    if not request.user.is_active:
        raise PermissionDenied
    profile = DonorProfile.objects.filter(user=request.user).first()

    if request.method == "POST":
        action = request.POST.get("action", "save")
        if action in {"pause", "deactivate"}:
            if profile is None:
                raise Http404
            if action == "pause":
                pause_donor_profile(user=request.user, profile=profile)
                messages.success(request, "Your donor profile is paused.")
            else:
                deactivate_donor_profile(user=request.user, profile=profile)
                messages.success(request, "Your donor profile is hidden and unavailable.")
            return redirect("donors:profile")

        form = DonorProfileForm(
            request.POST,
            instance=profile,
            user=request.user,
        )
        if form.is_valid():
            profile = save_donor_profile(
                user=request.user,
                profile=form.save(commit=False),
                values=form.cleaned_data,
                consent_fields=form.share_fields
                | ({"visibility_enabled"} if "visibility_enabled" in form.fields else set()),
            )
            messages.success(request, "Your donor profile has been saved as a self-reported profile.")
            return redirect("donors:profile")
    else:
        form = DonorProfileForm(instance=profile, user=request.user)

    return render(
        request,
        "donors/profile_form.html",
        {"form": form, "profile": profile},
    )
