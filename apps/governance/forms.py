from django import forms


class PrivacySettingsForm(forms.Form):
    donor_discovery = forms.BooleanField(
        required=False,
        label="Allow my donor profile to appear in discovery",
    )
    phone_share_after_accept = forms.BooleanField(
        required=False,
        label="Allow my phone number to be shared after I accept a contact request",
    )
    email_share_after_accept = forms.BooleanField(
        required=False,
        label="Allow my email address to be shared after I accept a contact request",
    )
    optional_notifications = forms.BooleanField(
        required=False,
        label="Receive optional service notifications",
    )
    location_display = forms.BooleanField(
        required=False,
        label="Allow generalized area display on a future map",
    )

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        if not user.phone_e164 or not user.phone_verified_at:
            self.fields.pop("phone_share_after_accept")
        if not user.email or not user.email_verified_at:
            self.fields.pop("email_share_after_accept")
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-check-input"
