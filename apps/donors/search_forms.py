import uuid

from django import forms
from django.db.models import Q

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
    union = forms.ModelChoiceField(required=False, queryset=Location.objects.none(), empty_label="Any union")
    city_corporation = forms.ModelChoiceField(required=False, queryset=Location.objects.none(), empty_label="Any city corporation")
    city_zone = forms.ModelChoiceField(required=False, queryset=Location.objects.none(), empty_label="Any city zone")
    ward = forms.ModelChoiceField(required=False, queryset=Location.objects.none(), empty_label="Any ward")
    availability = forms.ChoiceField(
        required=False,
        choices=[("", "Available donors"), (AvailabilityStatus.AVAILABLE, "Available")],
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["upazila"].label = "Upazila (rural)"
        self.fields["union"].label = "Union (rural)"
        self.fields["city_corporation"].label = "City corporation (urban)"
        self.fields["city_zone"].label = "City zone"
        active = Location.objects.filter(is_active=True)
        self.fields["division"].queryset = active.filter(
            level=LocationLevel.DIVISION
        ).order_by("name_en")
        division_id = self._selected_parent_id("division")
        self.fields["district"].queryset = active.filter(
            level=LocationLevel.DISTRICT,
            parent_id=division_id,
            parent__level=LocationLevel.DIVISION,
            parent__is_active=True,
        ).order_by("name_en") if division_id else Location.objects.none()
        district_id = self._selected_parent_id("district")
        self.fields["upazila"].queryset = active.filter(
            level=LocationLevel.UPAZILA,
            parent_id=district_id,
            parent__level=LocationLevel.DISTRICT,
            parent__is_active=True,
            parent__parent__level=LocationLevel.DIVISION,
            parent__parent__is_active=True,
        ).order_by("name_en") if district_id else Location.objects.none()
        upazila_id = self._selected_parent_id("upazila")
        self.fields["union"].queryset = active.filter(
            level=LocationLevel.UNION,
            parent_id=upazila_id,
            parent__is_active=True,
            parent__parent__is_active=True,
            parent__parent__parent__is_active=True,
        ).order_by("name_en") if upazila_id else Location.objects.none()
        self.fields["city_corporation"].queryset = active.filter(
            level=LocationLevel.CITY_CORPORATION,
            parent_id=district_id,
            parent__is_active=True,
            parent__parent_id=division_id,
            parent__parent__is_active=True,
        ).order_by("name_en") if district_id and division_id else Location.objects.none()
        city_id = self._selected_parent_id("city_corporation")
        self.fields["city_zone"].queryset = active.filter(
            level=LocationLevel.ZONE,
            parent_id=city_id,
            parent__is_active=True,
            parent__parent__is_active=True,
            parent__parent__parent__is_active=True,
        ).order_by("name_en") if city_id else Location.objects.none()
        zone_id = self._selected_parent_id("city_zone")
        if city_id:
            ward_queryset = active.filter(
                level=LocationLevel.WARD,
                parent__is_active=True,
                parent__parent__is_active=True,
                parent__parent__parent__is_active=True,
            ).filter(
                Q(parent_id=zone_id, parent__parent_id=city_id)
                if zone_id
                else Q(parent_id=city_id) | Q(parent__parent_id=city_id)
            )
            self.fields["ward"].queryset = ward_queryset.order_by("name_en")

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
