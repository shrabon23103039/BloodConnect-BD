import uuid

from django import forms

from apps.donors.models import AvailabilityStatus, BloodGroup
from apps.locations.models import Location, LocationLevel


class DonorSearchForm(forms.Form):
    blood_group = forms.ChoiceField(
        required=False,
        choices=[("", "Any blood group"), *BloodGroup.choices],
    )
    division = forms.ModelChoiceField(
        required=False,
        queryset=Location.objects.none(),
        empty_label="Any division",
    )
    district = forms.ModelChoiceField(
        required=False,
        queryset=Location.objects.none(),
        empty_label="Any district",
    )
    upazila = forms.ModelChoiceField(
        required=False,
        queryset=Location.objects.none(),
        empty_label="Any upazila",
    )
    availability = forms.ChoiceField(
        required=False,
        choices=[("", "Available donors"), (AvailabilityStatus.AVAILABLE, "Available")],
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        active = Location.objects.filter(is_active=True)
        self.fields["division"].queryset = active.filter(
            level=LocationLevel.DIVISION
        ).order_by("name_en")
        division_id = self._selected_parent_id("division")
        self.fields["district"].queryset = active.filter(
            level=LocationLevel.DISTRICT,
            parent_id=division_id,
        ).order_by("name_en") if division_id else Location.objects.none()
        district_id = self._selected_parent_id("district")
        self.fields["upazila"].queryset = active.filter(
            level=LocationLevel.UPAZILA,
            parent_id=district_id,
        ).order_by("name_en") if district_id else Location.objects.none()

        for field in self.fields.values():
            field.widget.attrs["class"] = "form-select"

    def _selected_parent_id(self, name):
        if not self.is_bound:
            return None
        value = self.data.get(name)
        try:
            uuid.UUID(str(value))
        except (ValueError, TypeError, AttributeError):
            return None
        return value
