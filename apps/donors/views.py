from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from apps.donors.forms import DonorProfileForm
from apps.donors.models import DonorProfile
from apps.donors.services import (
    deactivate_donor_profile,
    pause_donor_profile,
    save_donor_profile,
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
                consent_fields=form.share_fields,
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
