from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render

from apps.governance.forms import PrivacySettingsForm
from apps.governance.models import (
    ConsentSource,
    ConsentType,
    current_consent_state,
    record_consent,
)


SETTING_TYPES = {
    "donor_discovery": ConsentType.DONOR_DISCOVERY,
    "phone_share_after_accept": ConsentType.PHONE_SHARE_AFTER_ACCEPT,
    "email_share_after_accept": ConsentType.EMAIL_SHARE_AFTER_ACCEPT,
    "optional_notifications": ConsentType.OPTIONAL_NOTIFICATIONS,
    "location_display": ConsentType.LOCATION_DISPLAY,
}


@login_required
def privacy_settings(request):
    if not request.user.is_active:
        raise PermissionDenied

    current = current_consent_state(request.user)
    initial = {name: current.get(consent_type, False) for name, consent_type in SETTING_TYPES.items()}
    form = PrivacySettingsForm(
        request.POST if request.method == "POST" else None,
        initial=initial,
    )
    if request.method == "POST" and form.is_valid():
        for field_name, consent_type in SETTING_TYPES.items():
            record_consent(
                user=request.user,
                consent_type=consent_type,
                policy_version=settings.PRIVACY_POLICY_VERSION,
                granted=form.cleaned_data[field_name],
                source=ConsentSource.WEB,
            )
        messages.success(request, "Your privacy choices have been saved.")
        return redirect("governance:privacy_settings")

    return render(
        request,
        "governance/privacy_settings.html",
        {"form": form, "policy_version": settings.PRIVACY_POLICY_VERSION},
    )
