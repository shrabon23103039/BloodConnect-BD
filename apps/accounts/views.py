"""Server-rendered account registration and session authentication views."""

import logging

from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import DatabaseError, IntegrityError, transaction
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_http_methods

from allauth.socialaccount.providers.google.views import oauth2_callback, oauth2_login
from allauth.socialaccount.models import SocialAccount

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
from apps.accounts.models import (
    AccountStatus,
    VerificationChannel,
    VerificationPurpose,
)
from apps.accounts.throttling import limited_by_ip
from apps.accounts.verification import (
    VerificationRateLimited,
    VerificationDeliveryError,
    VerificationUnavailable,
    consume_challenge,
    get_verification_provider,
    issue_challenge,
)

from apps.governance.models import ConsentSource, ConsentType, record_consent

oauth_logger = logging.getLogger("bloodconnect.oauth")


@limited_by_ip(
    scope="register", limit=5, window_seconds=3600,
    limit_setting="REGISTRATION_THROTTLE_LIMIT",
)
@require_http_methods(["GET", "POST"])
def register(request):
    form = RegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        verification_channel = (
            VerificationChannel.EMAIL
            if form.cleaned_data.get("email")
            else VerificationChannel.PHONE
        )
        try:
            get_verification_provider(verification_channel)
        except VerificationUnavailable:
            return render(
                request,
                "accounts/registration_unavailable.html",
                status=503,
            )
        values = form.cleaned_data
        try:
            with transaction.atomic():
                user = get_user_model().objects.create_user(
                    email=values.get("email"),
                    phone_e164=values.get("phone_e164"),
                    display_name=values["display_name"],
                    password=values["password1"],
                )
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
            request.session["registration_identifier_type"] = (
                "email" if values.get("email") else "phone"
            )
        except (IntegrityError, ValidationError):
            # A generic response prevents account enumeration by email or phone.
            request.session["registration_created"] = False
            request.session.pop("registration_identifier_type", None)
        return redirect("accounts:registration_submitted")
    return render(request, "accounts/register.html", {"form": form})


def registration_submitted(request):
    account_created = request.session.get("registration_created", False)
    identifier_type = request.session.get("registration_identifier_type", "")
    return render(
        request,
        "accounts/registration_submitted.html",
        {
            "account_created": account_created,
            "identifier_type": identifier_type,
        },
    )


def _find_account(identifier):
    User = get_user_model()
    if "@" in identifier:
        return User.objects.filter(email=identifier).first()
    return User.objects.filter(phone_e164=identifier).first()


@limited_by_ip(scope="verification-send", limit=5, window_seconds=3600)
@require_http_methods(["GET", "POST"])
def verification_start(request):
    initial = {}
    if request.method == "GET" and request.session.get("verification_identifier"):
        initial["identifier"] = request.session["verification_identifier"]
    form = VerificationIdentifierForm(request.POST or None, initial=initial)
    sent = request.session.pop("verification_request_submitted", False)
    if request.method == "POST" and form.is_valid():
        identifier = form.cleaned_data["identifier"]
        request.session.pop("verification_code_only", None)
        request.session["verification_identifier"] = identifier
        user = _find_account(identifier)
        if user and user.account_status == AccountStatus.PENDING:
            try:
                issue_challenge(user, VerificationPurpose.ACCOUNT)
            except VerificationDeliveryError as error:
                logging.getLogger("bloodconnect.verification").warning(
                    "Verification delivery failed",
                    extra={
                        "event": "verification_delivery_failed",
                        "request_id": getattr(request, "request_id", ""),
                        "error_type": type(error.__cause__).__name__
                        if error.__cause__
                        else type(error).__name__,
                    },
                )
            except (VerificationRateLimited, VerificationUnavailable):
                pass
        # Same response for unknown, active, rate-limited and pending accounts.
        request.session["verification_request_submitted"] = True
        return redirect("accounts:verify")
    return render(request, "accounts/verification_start.html", {"form": form, "sent": sent})


@limited_by_ip(scope="verification-attempt", limit=10, window_seconds=3600)
@require_http_methods(["GET", "POST"])
def verify_account(request):
    initial = {}
    if request.method == "GET" and request.session.get("verification_identifier"):
        initial["identifier"] = request.session["verification_identifier"]
    verification_code_only = bool(
        request.session.get("verification_code_only")
        and request.session.get("verification_identifier")
    )
    submitted_data = request.POST or None
    if request.method == "POST" and verification_code_only:
        # Google supplied the verified address; the session, not a modifiable
        # hidden field, is authoritative for which account receives the code.
        submitted_data = request.POST.copy()
        submitted_data["identifier"] = request.session["verification_identifier"]
    form = VerificationCodeForm(submitted_data, initial=initial)
    request_submitted = request.session.get("verification_request_submitted", False)
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
            request.session.pop("verification_identifier", None)
            request.session.pop("verification_code_only", None)
            request.session.pop("verification_request_submitted", None)
            identifier_type = "email" if user.email else "phone"
            messages.success(
                request,
                f"Your {identifier_type} has been verified. You can now sign in.",
            )
            return redirect("accounts:login")
        form.add_error(None, "The code is invalid, expired, or already used.")
    return render(
        request,
        "accounts/verify.html",
        {
            "form": form,
            "request_submitted": request_submitted,
            "verification_code_only": verification_code_only,
        },
    )


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
            except VerificationDeliveryError as error:
                logging.getLogger("bloodconnect.verification").warning(
                    "Verification delivery failed",
                    extra={
                        "event": "verification_delivery_failed",
                        "request_id": getattr(request, "request_id", ""),
                        "error_type": type(error.__cause__).__name__
                        if error.__cause__
                        else type(error).__name__,
                    },
                )
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
            request.session.cycle_key()
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

    @limited_by_ip(scope="login", limit=10, window_seconds=60, methods={"POST"})
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


class SecurePasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    """Rotate the anonymous session before granting reset-token authority."""

    @limited_by_ip(scope="password-reset-confirm", limit=10, window_seconds=3600)
    def dispatch(self, request, *args, **kwargs):
        user = self.get_user(kwargs.get("uidb64", ""))
        token = kwargs.get("token", "")
        if (
            user is not None
            and token != self.reset_url_token
            and self.token_generator.check_token(user, token)
        ):
            request.session.cycle_key()
        return super().dispatch(request, *args, **kwargs)


@login_required
@require_http_methods(["GET"])
def google_link(request):
    """Show the explicit, authenticated Google-link action."""
    if request.user.account_status != AccountStatus.ACTIVE:
        return render(request, "accounts/google_link.html", status=403)
    linked = SocialAccount.objects.filter(
        user=request.user,
        provider="google",
    ).exists()
    return render(
        request,
        "accounts/google_link.html",
        {"google_account_linked": linked},
    )


@limited_by_ip(
    scope="google-oauth-start", limit=10, window_seconds=60, methods={"POST"},
    limit_setting="GOOGLE_OAUTH_START_THROTTLE_LIMIT",
)
@require_http_methods(["POST"])
def google_oauth_start(request):
    """Apply the account IP throttle before django-allauth starts OAuth."""
    if not settings.GOOGLE_OAUTH_ENABLED:
        return redirect("accounts:login")
    return oauth2_login(request)


@limited_by_ip(scope="google-oauth-callback", limit=20, window_seconds=60)
@require_http_methods(["GET"])
def google_oauth_callback(request):
    """Bound callback traffic and delegate protocol processing to allauth."""
    try:
        return oauth2_callback(request)
    except Exception as error:
        # Keep DEBUG's technical 500 page from exposing callback/database details.
        oauth_logger.error(
            "Google OAuth callback failed",
            extra={
                "event": "oauth_callback_failed",
                "request_id": getattr(request, "request_id", ""),
                "error_type": type(error).__name__,
            },
        )
        response_status = 503 if isinstance(error, DatabaseError) else 400
        return render(
            request,
            "accounts/google_oauth_error.html",
            status=response_status,
        )
