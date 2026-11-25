"""Forms for account creation and identifier-based sign-in."""

from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm, SetPasswordForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction

from apps.accounts.managers import UserManager
from apps.accounts.models import AccountStatus, User, validate_phone_e164


class RegistrationForm(forms.Form):
    display_name = forms.CharField(max_length=120, label="Display name")
    identifier_type = forms.ChoiceField(
        required=False,
        choices=(("email", "Email"), ("phone", "Phone")),
        initial="email",
        widget=forms.HiddenInput,
    )
    email = forms.EmailField(required=False, max_length=254)
    phone_e164 = forms.CharField(
        required=False,
        max_length=24,
        label="Phone number",
        help_text="Bangladesh numbers may be entered as 01XXXXXXXXX or +8801XXXXXXXXX.",
        widget=forms.TextInput(attrs={"inputmode": "tel", "autocomplete": "tel", "placeholder": "+880"}),
    )
    password1 = forms.CharField(
        label="Password", strip=False, max_length=128, widget=forms.PasswordInput
    )
    password2 = forms.CharField(
        label="Confirm password", strip=False, max_length=128, widget=forms.PasswordInput
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
        for name, field in self.fields.items():
            field.widget.attrs["class"] = (
                "form-check-input" if name in {"accept_terms", "accept_privacy"} else "form-control"
            )
        self.fields["display_name"].widget.attrs.update({
            "autocomplete": "name",
            "placeholder": "How you want to be identified",
        })
        self.fields["email"].widget.attrs.update({
            "autocomplete": "email",
            "inputmode": "email",
            "placeholder": "name@example.com",
        })
        self.fields["phone_e164"].widget.attrs.update({
            "autocomplete": "tel",
            "inputmode": "tel",
            "placeholder": "+8801XXXXXXXXX",
        })
        self.fields["password1"].widget.attrs.update({
            "autocomplete": "new-password",
        })
        self.fields["password2"].widget.attrs.update({
            "autocomplete": "new-password",
        })

    def clean_email(self):
        return UserManager.normalize_email_identifier(self.cleaned_data.get("email"))

    def clean_phone_e164(self):
        phone = UserManager.normalize_phone_identifier(self.cleaned_data.get("phone_e164"))
        if phone:
            validate_phone_e164(phone)
        return phone

    def clean(self):
        cleaned_data = super().clean()
        identifier_type = cleaned_data.get("identifier_type")
        email = cleaned_data.get("email")
        phone = cleaned_data.get("phone_e164")
        if not identifier_type:
            if email and not phone:
                identifier_type = "email"
            elif phone and not email:
                identifier_type = "phone"
        if identifier_type == "email":
            if phone:
                self.add_error("phone_e164", "Use only the selected Email identifier.")
            if not email:
                self.add_error("email", "Enter an email address.")
        elif identifier_type == "phone":
            if email:
                self.add_error("email", "Use only the selected Phone identifier.")
            if not phone:
                self.add_error("phone_e164", "Enter a phone number.")
        else:
            if not identifier_type:
                if not email and not phone:
                    self.add_error("email", "Enter an email address.")
                else:
                    self.add_error("identifier_type", "Choose Email or Phone.")
        if not identifier_type and bool(email) == bool(phone):
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


def normalize_verification_identifier(identifier: str) -> str:
    identifier = identifier.strip()
    if "@" in identifier:
        validate_email(identifier)
        return UserManager.normalize_email_identifier(identifier)
    phone = UserManager.normalize_phone_identifier(identifier)
    validate_phone_e164(phone)
    return phone


class VerificationIdentifierForm(forms.Form):
    identifier = forms.CharField(max_length=254, label="Email or phone")

    def clean_identifier(self):
        return normalize_verification_identifier(self.cleaned_data["identifier"])


class PhoneResetIdentifierForm(forms.Form):
    phone_e164 = forms.CharField(
        max_length=24,
        label="Phone number",
        help_text=(
            "Enter a Bangladesh mobile as 01XXXXXXXXX or +8801XXXXXXXXX. "
            "Spaces, parentheses, periods and hyphens are allowed."
        ),
    )

    def clean_phone_e164(self):
        phone = UserManager.normalize_phone_identifier(self.cleaned_data["phone_e164"])
        validate_phone_e164(phone)
        return phone


class VerificationCodeForm(forms.Form):
    identifier = forms.CharField(max_length=254, label="Email or phone")
    code = forms.RegexField(
        regex=r"^[0-9]{6}$",
        max_length=6,
        min_length=6,
        error_messages={"invalid": "Enter the six-digit code."},
    )

    def clean_identifier(self):
        return normalize_verification_identifier(self.cleaned_data["identifier"])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["identifier"].widget.attrs["class"] = "form-control"
        self.fields["code"].widget.attrs.update(
            {"class": "form-control", "inputmode": "numeric", "autocomplete": "one-time-code"}
        )


class PhoneResetCodeForm(forms.Form):
    phone_e164 = forms.CharField(
        max_length=24,
        label="Phone number",
        help_text=(
            "Enter a Bangladesh mobile as 01XXXXXXXXX or +8801XXXXXXXXX. "
            "Spaces, parentheses, periods and hyphens are allowed."
        ),
    )
    code = forms.RegexField(
        regex=r"^[0-9]{6}$",
        max_length=6,
        min_length=6,
        error_messages={"invalid": "Enter the six-digit code."},
    )

    def clean_phone_e164(self):
        phone = UserManager.normalize_phone_identifier(self.cleaned_data["phone_e164"])
        validate_phone_e164(phone)
        return phone

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"
        self.fields["code"].widget.attrs.update(
            {"inputmode": "numeric", "autocomplete": "one-time-code"}
        )


class RevokingSetPasswordForm(SetPasswordForm):
    """Save a reset password and revoke all API credentials atomically."""

    def save(self, commit=True):
        if not commit:
            return super().save(commit=False)
        with transaction.atomic():
            user = super().save(commit=True)
            from apps.api.token_services import revoke_user_tokens

            revoke_user_tokens(user=user)
        return user


class PhoneResetSetPasswordForm(RevokingSetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"
