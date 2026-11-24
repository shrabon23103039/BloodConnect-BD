"""Consent-aware social signup form for Google-created BloodConnect accounts."""

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction

from allauth.socialaccount.forms import SignupForm

from apps.accounts.managers import UserManager
from apps.governance.models import ConsentSource, ConsentType, record_consent


class GoogleSocialSignupForm(SignupForm):
    display_name = forms.CharField(
        max_length=120,
        label="Display name",
        widget=forms.TextInput(attrs={"autocomplete": "name"}),
    )
    accept_terms = forms.BooleanField(
        label="I accept the Terms of Service.",
        error_messages={"required": "Please review and accept the Terms of Service."},
    )
    accept_privacy = forms.BooleanField(
        label="I acknowledge the Privacy Notice.",
        error_messages={"required": "Please review and acknowledge the Privacy Notice."},
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].disabled = True
        self.fields["email"].initial = UserManager.normalize_email_identifier(
            self.sociallogin.user.email
        )
        self.fields["display_name"].initial = self.sociallogin.user.display_name
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")
        for name in ("accept_terms", "accept_privacy"):
            self.fields[name].widget.attrs["class"] = "form-check-input"

    def clean_display_name(self):
        display_name = self.cleaned_data["display_name"].strip()
        if not display_name:
            raise forms.ValidationError("Enter a display name.")
        return display_name[:120]

    def validate_unique_email(self, value):
        """Use BloodConnect's User email field, not allauth EmailAddress rows."""
        email = UserManager.normalize_email_identifier(value)
        if get_user_model().objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already associated with an account.")
        return email

    def save(self, request):
        self.sociallogin.user.display_name = self.cleaned_data["display_name"]
        with transaction.atomic():
            user = super().save(request)
            record_consent(
                user=user,
                consent_type=ConsentType.TERMS_ACCEPTED,
                policy_version=settings.TERMS_POLICY_VERSION,
                granted=True,
                source=ConsentSource.WEB,
            )
            record_consent(
                user=user,
                consent_type=ConsentType.PRIVACY_ACKNOWLEDGED,
                policy_version=settings.PRIVACY_POLICY_VERSION,
                granted=True,
                source=ConsentSource.WEB,
            )
            request.session["registration_created"] = True
            request.session["registration_identifier_type"] = "email"
        return user
