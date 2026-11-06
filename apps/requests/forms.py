from django import forms

from apps.locations.models import Location, LocationLevel
from apps.requests.models import BloodRequest


class BloodRequestForm(forms.ModelForm):
    expires_at = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}),
        help_text="Defaults to the required date and time.",
    )

    class Meta:
        model = BloodRequest
        fields = (
            "blood_group", "units_requested", "required_at", "division", "district",
            "upazila", "facility_name", "facility_address", "urgency", "description",
            "public_listing_enabled", "expires_at",
        )
        widgets = {
            "required_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "description": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["division"].queryset = Location.objects.filter(
            level=LocationLevel.DIVISION, is_active=True
        ).order_by("name_en")
        division_id = self.data.get("division") if self.is_bound else self.instance.division_id
        self.fields["district"].queryset = Location.objects.filter(
            level=LocationLevel.DISTRICT, is_active=True, parent_id=division_id
        ).order_by("name_en") if division_id else Location.objects.none()
        district_id = self.data.get("district") if self.is_bound else self.instance.district_id
        self.fields["upazila"].queryset = Location.objects.filter(
            level=LocationLevel.UPAZILA, is_active=True, parent_id=district_id
        ).order_by("name_en") if district_id else Location.objects.none()

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("required_at") and not cleaned.get("expires_at"):
            cleaned["expires_at"] = cleaned["required_at"]
        return cleaned
