from django import forms
from django.utils import timezone

from apps.donors.models import (
    DonorProfile,
    DonorProfileStatus,
    PreferredContactMethod,
)
from apps.governance.models import ConsentType, current_consent_state


class DonorProfileForm(forms.ModelForm):
    location_confirmed = forms.BooleanField(
        required=False,
        widget=forms.HiddenInput,
    )
    store_donation_area = forms.BooleanField(
        required=False,
        label="Store this donation area privately",
        help_text=(
            "The selected point and its general-area label are stored on your profile only. "
            "They are not shared or used in donor search."
        ),
    )

    class Meta:
        model = DonorProfile
        fields = (
            "blood_group",
            "donation_area_label",
            "donation_area_latitude",
            "donation_area_longitude",
            "google_place_id",
            "location_source",
            "availability_status",
            "visibility_enabled",
            "public_alias",
            "thana_name",
            "preferred_contact_method",
            "share_phone_after_accept",
            "share_email_after_accept",
            "last_donation_date",
        )
        widgets = {
            "donation_area_label": forms.HiddenInput,
            "donation_area_latitude": forms.HiddenInput,
            "donation_area_longitude": forms.HiddenInput,
            "google_place_id": forms.HiddenInput,
            "location_source": forms.HiddenInput,
            "last_donation_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, user, **kwargs):
        self.account = user
        super().__init__(*args, **kwargs)
        available_methods = [(PreferredContactMethod.IN_APP, "In app")]
        self.share_fields = set()
        self.consent_fields = {"store_donation_area"}
        consent_state = current_consent_state(user)
        if not self.is_bound:
            stored_visibility = getattr(self.instance, "visibility_enabled", False)
            self.initial["visibility_enabled"] = (
                stored_visibility and consent_state.get(ConsentType.DONOR_DISCOVERY, False)
                if self.instance.pk and not self.instance._state.adding
                else consent_state.get(ConsentType.DONOR_DISCOVERY, False)
            )
            self.initial["location_confirmed"] = bool(
                self.instance.pk
                and self.instance.donation_area_latitude is not None
                and self.instance.donation_area_longitude is not None
            )
            self.initial["store_donation_area"] = consent_state.get(
                ConsentType.DONOR_AREA_STORAGE,
                False,
            )
        if (
            self.instance.pk
            and not self.instance._state.adding
            and self.instance.profile_status == DonorProfileStatus.SUSPENDED
        ):
            self.fields.pop("availability_status")
            self.fields.pop("visibility_enabled")
        if user.phone_e164 and user.phone_verified_at:
            available_methods.append((PreferredContactMethod.PHONE_AFTER_ACCEPT, "Phone after acceptance"))
            self.share_fields.add("share_phone_after_accept")
            if not self.is_bound:
                self.initial["share_phone_after_accept"] = consent_state.get(
                    ConsentType.PHONE_SHARE_AFTER_ACCEPT,
                    getattr(self.instance, "share_phone_after_accept", False),
                )
        else:
            self.fields.pop("share_phone_after_accept")
        if user.email and user.email_verified_at:
            available_methods.append((PreferredContactMethod.EMAIL_AFTER_ACCEPT, "Email after acceptance"))
            self.share_fields.add("share_email_after_accept")
            if not self.is_bound:
                self.initial["share_email_after_accept"] = consent_state.get(
                    ConsentType.EMAIL_SHARE_AFTER_ACCEPT,
                    getattr(self.instance, "share_email_after_accept", False),
                )
        else:
            self.fields.pop("share_email_after_accept")
        self.fields["preferred_contact_method"].choices = available_methods

        for field in self.fields.values():
            if field.widget.input_type == "checkbox":
                css_class = "form-check-input"
            elif isinstance(field, forms.ChoiceField):
                css_class = "form-select"
            else:
                css_class = "form-control"
            field.widget.attrs["class"] = css_class
        for name in self.share_fields:
            self.fields[name].widget.attrs["class"] = "form-check-input"

    def clean(self):
        cleaned = super().clean()
        latitude = cleaned.get("donation_area_latitude")
        longitude = cleaned.get("donation_area_longitude")
        has_latitude = latitude is not None
        has_longitude = longitude is not None
        location_confirmed = cleaned.get("location_confirmed", False)
        area_label = cleaned.get("donation_area_label", "")
        place_id = cleaned.get("google_place_id", "")
        location_source = cleaned.get("location_source", "")

        if has_latitude != has_longitude:
            self.add_error("donation_area_latitude", "Select a complete donation area.")
        elif has_latitude:
            if not area_label:
                self.add_error("donation_area_label", "Select a general area before confirming.")
            if not location_source:
                self.add_error("location_source", "Confirm the selected donation area.")
            if not location_confirmed:
                self.add_error("location_confirmed", "Confirm the selected donation area before saving.")
            if not cleaned.get("store_donation_area"):
                self.add_error(
                    "store_donation_area",
                    "Consent is required to store the selected donation area privately.",
                )
        elif area_label or place_id or location_source or location_confirmed:
            self.add_error("donation_area_label", "Clear the selected donation area before saving.")

        if has_latitude and has_longitude and location_confirmed:
            self.instance.location_confirmed_at = timezone.now()
        elif not has_latitude and not has_longitude:
            self.instance.location_confirmed_at = None

        method = cleaned.get("preferred_contact_method")
        if method == PreferredContactMethod.PHONE_AFTER_ACCEPT and "share_phone_after_accept" not in self.share_fields:
            self.add_error("preferred_contact_method", "A verified phone number is required for this contact method.")
        if method == PreferredContactMethod.EMAIL_AFTER_ACCEPT and "share_email_after_accept" not in self.share_fields:
            self.add_error("preferred_contact_method", "A verified email address is required for this contact method.")
        return cleaned
