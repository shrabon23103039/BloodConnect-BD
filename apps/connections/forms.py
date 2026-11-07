"""Forms for starting a private contact request."""

from django import forms
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone

from apps.connections.models import ContactRequest
from apps.donors.models import DonorProfile
from apps.requests.models import BloodRequest, BloodRequestStatus


class ContactRequestForm(forms.ModelForm):
    donor_profile = forms.ModelChoiceField(
        queryset=DonorProfile.objects.none(),
        empty_label="Choose a potential donor",
    )
    blood_request = forms.ModelChoiceField(
        queryset=BloodRequest.objects.none(),
        empty_label="Choose your open blood request",
    )

    class Meta:
        model = ContactRequest
        fields = ("donor_profile", "blood_request", "message")
        widgets = {
            "message": forms.Textarea(attrs={"rows": 3, "maxlength": 500}),
        }

    def __init__(self, *args, user, donor_profile_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        donors = DonorProfile.objects.discoverable().select_related(
            "district", "division"
        )
        self.fields["donor_profile"].queryset = donors.order_by(
            "district__name_en", "public_alias", "id"
        )
        self.fields["donor_profile"].label_from_instance = self._donor_label
        self.fields["blood_request"].queryset = BloodRequest.objects.filter(
            requester=user,
            status=BloodRequestStatus.OPEN,
            expires_at__gt=timezone.now(),
        ).order_by("-created_at")
        if donor_profile_id:
            try:
                self.initial["donor_profile"] = donors.get(pk=donor_profile_id)
            except (DonorProfile.DoesNotExist, ValueError, DjangoValidationError):
                pass
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"
        for name in ("donor_profile", "blood_request"):
            self.fields[name].widget.attrs["class"] = "form-select"

    @staticmethod
    def _donor_label(profile):
        alias = profile.public_alias or "Blood donor"
        return f"{alias} — {profile.district.name_en}"
