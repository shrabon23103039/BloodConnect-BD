"""Server-rendered account registration and session authentication views."""

from django.contrib.auth import views as auth_views
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_http_methods

from apps.accounts.forms import (
    AccountPasswordResetForm,
    IdentifierAuthenticationForm,
    PhoneResetCodeForm,
    PhoneResetIdentifierForm,
    PhoneResetSetPasswordForm,
    RegistrationForm,
    VerificationCodeForm,
    VerificationIdentifierForm,
)
from apps.accounts.models import AccountStatus, VerificationPurpose
from apps.accounts.throttling import limited_by_ip
from apps.accounts.verification import (
    VerificationRateLimited,
    VerificationUnavailable,
    consume_challenge,
    get_verification_provider,
    issue_challenge,
)


@limited_by_ip(scope="register", limit=5, window_seconds=3600)
@require_http_methods(["GET", "POST"])
def register(request):
    form = RegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            get_verification_provider()
        except VerificationUnavailable:
            return render(
                request,
                "accounts/registration_unavailable.html",
                status=503,
            )
        values = form.cleaned_data
        try:
            with transaction.atomic():
                get_user_model().objects.create_user(
                    email=values.get("email"),
                    phone_e164=values.get("phone_e164"),
                    display_name=values["display_name"],
                    password=values["password1"],
                )
        except (IntegrityError, ValidationError):
            # A generic response prevents account enumeration by email or phone.
            pass
        return redirect("accounts:registration_submitted")
    return render(request, "accounts/register.html", {"form": form})


def registration_submitted(request):
    return render(request, "accounts/registration_submitted.html")


def _find_account(identifier):
    User = get_user_model()
    if "@" in identifier:
        return User.objects.filter(email=identifier).first()
    return User.objects.filter(phone_e164=identifier).first()


@limited_by_ip(scope="verification-send", limit=5, window_seconds=3600)
@require_http_methods(["GET", "POST"])
def verification_start(request):
    form = VerificationIdentifierForm(request.POST or None)
    sent = False
    if request.method == "POST" and form.is_valid():
        user = _find_account(form.cleaned_data["identifier"])
        if user and user.account_status == AccountStatus.PENDING:
            try:
                issue_challenge(user, VerificationPurpose.ACCOUNT)
            except (VerificationRateLimited, VerificationUnavailable):
                pass
        # Same response for unknown, active, rate-limited and pending accounts.
        sent = True
    return render(request, "accounts/verification_start.html", {"form": form, "sent": sent})


@limited_by_ip(scope="verification-attempt", limit=10, window_seconds=3600)
@require_http_methods(["GET", "POST"])
def verify_account(request):
    form = VerificationCodeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = _find_account(form.cleaned_data["identifier"])
        if (
            user
            and user.account_status == AccountStatus.PENDING
            and consume_challenge(
                user,
                VerificationPurpose.ACCOUNT,
                form.cleaned_data["code"],
            )
        ):
            return redirect("accounts:login")
        form.add_error(None, "The code is invalid, expired, or already used.")
    return render(request, "accounts/verify.html", {"form": form})


@limited_by_ip(scope="phone-reset-send", limit=5, window_seconds=3600)
@require_http_methods(["GET", "POST"])
def phone_password_reset(request):
    form = PhoneResetIdentifierForm(request.POST or None)
    sent = False
    if request.method == "POST" and form.is_valid():
        user = get_user_model().objects.filter(
            phone_e164=form.cleaned_data["phone_e164"],
            account_status=AccountStatus.ACTIVE,
            phone_verified_at__isnull=False,
        ).first()
        if user:
            try:
                issue_challenge(user, VerificationPurpose.PASSWORD_RESET)
            except (VerificationRateLimited, VerificationUnavailable):
                pass
        sent = True
    return render(request, "accounts/phone_password_reset.html", {"form": form, "sent": sent})


@limited_by_ip(scope="phone-reset-attempt", limit=10, window_seconds=3600)
@require_http_methods(["GET", "POST"])
def phone_password_reset_verify(request):
    form = PhoneResetCodeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = get_user_model().objects.filter(
            phone_e164=form.cleaned_data["phone_e164"],
            account_status=AccountStatus.ACTIVE,
            phone_verified_at__isnull=False,
        ).first()
        if (
            user
            and consume_challenge(
                user,
                VerificationPurpose.PASSWORD_RESET,
                form.cleaned_data["code"],
            )
        ):
            request.session["phone_password_reset_user_id"] = str(user.pk)
            request.session.set_expiry(300)
            return redirect("accounts:phone_password_reset_confirm")
        form.add_error(None, "The code is invalid, expired, or already used.")
    return render(request, "accounts/phone_password_reset_verify.html", {"form": form})


@require_http_methods(["GET", "POST"])
def phone_password_reset_confirm(request):
    User = get_user_model()
    user = User.objects.filter(
        pk=request.session.get("phone_password_reset_user_id"),
        account_status=AccountStatus.ACTIVE,
        phone_e164__isnull=False,
    ).first()
    if user is None:
        return redirect("accounts:phone_password_reset")

    form = PhoneResetSetPasswordForm(user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        request.session.pop("phone_password_reset_user_id", None)
        return redirect("accounts:password_reset_complete")
    return render(request, "accounts/phone_password_reset_confirm.html", {"form": form})


class ThrottledLoginView(auth_views.LoginView):
    template_name = "accounts/login.html"
    authentication_form = IdentifierAuthenticationForm
    next_page = reverse_lazy("home")

    @limited_by_ip(scope="login", limit=10, window_seconds=60)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)


class ThrottledPasswordResetView(auth_views.PasswordResetView):
    template_name = "accounts/password_reset_form.html"
    form_class = AccountPasswordResetForm
    email_template_name = "accounts/password_reset_email.txt"
    subject_template_name = "accounts/password_reset_subject.txt"
    success_url = reverse_lazy("accounts:password_reset_done")

    @limited_by_ip(scope="password-reset", limit=5, window_seconds=3600)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)
