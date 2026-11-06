"""Forms for account creation and identifier-based sign-in."""

from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from apps.accounts.managers import UserManager
from apps.accounts.models import AccountStatus, User, phone_e164_validator


class RegistrationForm(forms.Form):
    display_name = forms.CharField(max_length=120, label="Display name")
    email = forms.EmailField(required=False, max_length=254)
    phone_e164 = forms.CharField(required=False, max_length=16, label="Phone (E.164)")
    password1 = forms.CharField(
        label="Password", strip=False, max_length=128, widget=forms.PasswordInput
    )
    password2 = forms.CharField(
        label="Confirm password", strip=False, max_length=128, widget=forms.PasswordInput
    )
    accept_terms = forms.BooleanField(
        label="I have read the Terms and Privacy Notice.",
        error_messages={"required": "Please review and accept the Terms and Privacy Notice."},
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.widget.attrs["class"] = (
                "form-check-input" if name == "accept_terms" else "form-control"
            )

    def clean_email(self):
        return UserManager.normalize_email_identifier(self.cleaned_data.get("email"))

    def clean_phone_e164(self):
        phone = UserManager.normalize_phone_identifier(self.cleaned_data.get("phone_e164"))
        if phone:
            phone_e164_validator(phone)
        return phone

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get("email")
        phone = cleaned_data.get("phone_e164")
        if bool(email) == bool(phone):
            raise ValidationError("Enter one email address or one E.164 phone number.")

        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            self.add_error("password2", "The passwords do not match.")
        elif password1:
            candidate = User(
                display_name=cleaned_data.get("display_name", ""),
                email=email,
                phone_e164=phone,
            )
            try:
                validate_password(password1, user=candidate)
            except ValidationError as error:
                self.add_error("password1", error)
        return cleaned_data


class IdentifierAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label="Email or phone",
        widget=forms.TextInput(attrs={"autocomplete": "username", "autofocus": True}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs["class"] = "form-control"
        self.fields["password"].widget.attrs["class"] = "form-control"


class AccountPasswordResetForm(PasswordResetForm):
    """Find only active email accounts without relying on a DB `is_active` field."""

    def get_users(self, email):
        normalized_email = UserManager.normalize_email_identifier(email)
        users = User.objects.filter(
            email=normalized_email,
            account_status=AccountStatus.ACTIVE,
            email_verified_at__isnull=False,
        )
        return (user for user in users if user.has_usable_password())

    def clean(self):
        identifier = self.cleaned_data.get("username", "").strip()
        password = self.cleaned_data.get("password")
        if identifier and password:
            self.user_cache = authenticate(
                self.request,
                username=identifier,
                password=password,
            )
            if self.user_cache is None:
                raise self.get_invalid_login_error()
            self.confirm_login_allowed(self.user_cache)
        return self.cleaned_data
