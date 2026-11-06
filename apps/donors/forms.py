from django import forms

from apps.donors.models import (
    DonorProfile,
    DonorProfileStatus,
    PreferredContactMethod,
)
from apps.governance.models import ConsentType, current_consent_state
from apps.locations.models import Location, LocationLevel


class DonorProfileForm(forms.ModelForm):
    class Meta:
        model = DonorProfile
        fields = (
            "blood_group",
            "division",
            "district",
            "upazila",
            "availability_status",
            "visibility_enabled",
            "public_alias",
            "preferred_contact_method",
            "share_phone_after_accept",
            "share_email_after_accept",
            "last_donation_date",
        )
        widgets = {"last_donation_date": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, user, **kwargs):
        self.account = user
        super().__init__(*args, **kwargs)
        self.fields["division"].queryset = Location.objects.filter(
            level=LocationLevel.DIVISION,
            is_active=True,
        ).order_by("name_en")

        division_id = self.data.get("division") if self.is_bound else getattr(self.instance, "division_id", None)
        district_queryset = Location.objects.filter(
            level=LocationLevel.DISTRICT,
            is_active=True,
            parent_id=division_id,
        ) if division_id else Location.objects.none()
        self.fields["district"].queryset = district_queryset.order_by("name_en")

        district_id = self.data.get("district") if self.is_bound else getattr(self.instance, "district_id", None)
        upazila_queryset = Location.objects.filter(
            level=LocationLevel.UPAZILA,
            is_active=True,
            parent_id=district_id,
        ) if district_id else Location.objects.none()
        self.fields["upazila"].queryset = upazila_queryset.order_by("name_en")

        available_methods = [(PreferredContactMethod.IN_APP, "In app")]
        self.share_fields = set()
        consent_state = current_consent_state(user)
        if not self.is_bound:
            stored_visibility = getattr(self.instance, "visibility_enabled", False)
            self.initial["visibility_enabled"] = (
                stored_visibility and consent_state.get(ConsentType.DONOR_DISCOVERY, False)
                if self.instance.pk and not self.instance._state.adding
                else consent_state.get(ConsentType.DONOR_DISCOVERY, False)
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
        method = cleaned.get("preferred_contact_method")
        if method == PreferredContactMethod.PHONE_AFTER_ACCEPT and "share_phone_after_accept" not in self.share_fields:
            self.add_error("preferred_contact_method", "A verified phone number is required for this contact method.")
        if method == PreferredContactMethod.EMAIL_AFTER_ACCEPT and "share_email_after_accept" not in self.share_fields:
            self.add_error("preferred_contact_method", "A verified email address is required for this contact method.")
        return cleaned
