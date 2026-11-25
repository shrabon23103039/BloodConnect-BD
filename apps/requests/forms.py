from django import forms

from apps.requests.models import BloodRequest, RequestLocationSource


class BloodRequestForm(forms.ModelForm):
    request_location_confirmed = forms.BooleanField(
        required=False,
        widget=forms.HiddenInput,
    )
    expires_at = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}),
        help_text="Defaults to the required date and time.",
    )

    class Meta:
        model = BloodRequest
        fields = (
            "blood_group", "units_requested", "required_at",
            "request_location_label", "request_location_latitude",
            "request_location_longitude", "request_location_place_id",
            "request_location_source", "request_location_confirmed",
            "facility_name", "facility_address", "urgency", "description",
            "public_listing_enabled", "expires_at",
        )
        widgets = {
            "required_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "description": forms.Textarea(attrs={"rows": 4}),
            "request_location_label": forms.HiddenInput,
            "request_location_latitude": forms.HiddenInput,
            "request_location_longitude": forms.HiddenInput,
            "request_location_place_id": forms.HiddenInput,
            "request_location_source": forms.HiddenInput,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["facility_name"].help_text = (
            "Optional facility text; separate from the selected request area."
        )
        self.fields["facility_address"].help_text = (
            "Optional facility directions/details; this does not change the map-selected area."
        )
        if not self.is_bound:
            self.initial["request_location_confirmed"] = bool(
                self.instance.pk
                and self.instance.request_location_latitude is not None
                and self.instance.request_location_longitude is not None
                and self.instance.request_location_confirmed_at is not None
            )

    def clean(self):
        cleaned = super().clean()
        label = cleaned.get("request_location_label", "")
        latitude = cleaned.get("request_location_latitude")
        longitude = cleaned.get("request_location_longitude")
        place_id = cleaned.get("request_location_place_id", "")
        source = cleaned.get("request_location_source", "")
        confirmed = cleaned.get("request_location_confirmed", False)
        has_location_data = bool(label or latitude is not None or longitude is not None or place_id or source)

        if latitude is not None or longitude is not None:
            if latitude is None or longitude is None:
                self.add_error("request_location_label", "Choose a complete map location.")
            if not label or not source or not confirmed:
                self.add_error(
                    "request_location_confirmed",
                    "Select and explicitly confirm a request area before saving it.",
                )
        elif has_location_data or confirmed:
            self.add_error(
                "request_location_label",
                "Select and confirm a request area, or clear the selected area.",
            )
        if source == RequestLocationSource.MAP_PIN and place_id:
            self.add_error(
                "request_location_place_id",
                "A map-adjusted pin cannot retain a place identifier.",
            )

        if cleaned.get("required_at") and not cleaned.get("expires_at"):
            cleaned["expires_at"] = cleaned["required_at"]
        return cleaned
