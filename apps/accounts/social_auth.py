"""django-allauth adapters that preserve BloodConnect account policy."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.shortcuts import redirect
from django.urls import reverse

from allauth.account.adapter import DefaultAccountAdapter
from allauth.core.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.models import SocialAccount, SocialApp
from allauth.socialaccount.providers.base import AuthError

from apps.accounts.managers import UserManager
from apps.accounts.models import (
    AccountStatus,
    VerificationPurpose,
)
from apps.accounts.verification import (
    VerificationDeliveryError,
    VerificationRateLimited,
    VerificationUnavailable,
    issue_challenge,
)

verification_logger = logging.getLogger("bloodconnect.verification")


def _request_google_email_verification(request, user):
    """Request one email challenge for a pending Google-created account."""
    request.session["verification_identifier"] = user.email
    request.session["verification_request_submitted"] = True
    request.session["verification_code_only"] = True

    try:
        # The service rechecks under its per-user lock, so concurrent callback
        # retries cannot each create and deliver a separate live challenge.
        issue_challenge(
            user,
            VerificationPurpose.ACCOUNT,
            reuse_unexpired=True,
        )
    except VerificationRateLimited:
        # The existing service cooldown/cap prevents repeated callback sends.
        return
    except (VerificationDeliveryError, VerificationUnavailable) as error:
        verification_logger.warning(
            "Google account verification delivery unavailable",
            extra={
                "event": "google_verification_delivery_unavailable",
                "request_id": getattr(request, "request_id", ""),
                "error_type": type(error.__cause__ or error).__name__,
            },
        )


class BloodConnectAccountAdapter(DefaultAccountAdapter):
    """Keep pending/suspended account sign-in behind existing policy gates."""

    def respond_user_inactive(self, request, user):
        if user.account_status == AccountStatus.PENDING:
            google_linked = SocialAccount.objects.filter(
                user=user, provider="google"
            ).exists()
            if google_linked and user.email and user.email_verified_at is None:
                # The social signup form sets this marker for its generic
                # confirmation screen. Google-created accounts continue to
                # the existing email challenge flow instead.
                request.session.pop("registration_created", None)
                request.session.pop("registration_identifier_type", None)
                _request_google_email_verification(request, user)
                return redirect("accounts:verify")
            if request.session.pop("registration_created", False):
                request.session["registration_created"] = True
                request.session["registration_identifier_type"] = "email"
                return redirect("accounts:registration_submitted")
            messages.info(
                request,
                "Your account still needs verification before you can sign in.",
            )
            return redirect("accounts:verification_start")

        messages.error(
            request,
            "Google sign-in could not be completed for this account. Contact support if you need help.",
        )
        return redirect("accounts:login")


class BloodConnectSocialAccountAdapter(DefaultSocialAccountAdapter):
    """Require a verified Google subject and an explicit, safe link action."""

    def list_apps(self, request, provider=None, client_id=None):
        """Resolve configured providers from settings without querying SocialApp."""
        apps_by_provider = {}
        provider_settings = getattr(settings, "SOCIALACCOUNT_PROVIDERS", {})
        for provider_name, provider_config in provider_settings.items():
            if provider and provider_name != provider:
                continue
            app_configs = provider_config.get("APPS")
            if app_configs is None:
                configured_app = provider_config.get("APP")
                app_configs = [configured_app] if configured_app else []
            for config in app_configs:
                if client_id and config.get("client_id") != client_id:
                    continue
                app = SocialApp(provider=provider_name)
                for field in ("name", "provider_id", "client_id", "secret", "key", "settings"):
                    if field in config:
                        setattr(app, field, config[field])
                apps_by_provider.setdefault(provider_name, []).append(app)
        return [app for provider_apps in apps_by_provider.values() for app in provider_apps]

    def _reject_google(self, request, message, destination=None):
        messages.error(request, message)
        destination = destination or (
            "accounts:google_link" if request.user.is_authenticated else "accounts:login"
        )
        raise ImmediateHttpResponse(redirect(destination))

    def on_authentication_error(
        self, request, provider, error=None, exception=None, extra_context=None
    ):
        if provider.id != "google":
            return super().on_authentication_error(
                request,
                provider,
                error=error,
                exception=exception,
                extra_context=extra_context,
            )

        if error == AuthError.CANCELLED:
            messages.info(
                request,
                "Google sign-in was cancelled. You can continue with email or phone.",
            )
        else:
            messages.error(
                request,
                "Google sign-in could not be completed. You can continue with email or phone.",
            )

        destination = (
            "accounts:google_link"
            if request.user.is_authenticated
            else "accounts:login"
        )
        raise ImmediateHttpResponse(redirect(destination))

    def pre_social_login(self, request, sociallogin):
        if sociallogin.account.provider != "google":
            self._reject_google(request, "Google sign-in could not be verified.")

        claims = sociallogin.account.extra_data
        if not isinstance(claims, Mapping):
            self._reject_google(request, "Google sign-in could not be verified.")

        subject = str(claims.get("sub") or "")
        email = UserManager.normalize_email_identifier(
            getattr(sociallogin.user, "email", None)
        )
        audience = claims.get("aud")
        audiences = {audience} if isinstance(audience, str) else set(audience or [])
        try:
            expires_at = int(claims.get("exp", 0))
        except (TypeError, ValueError):
            expires_at = 0

        provider_verified_emails = {
            UserManager.normalize_email_identifier(address.email)
            for address in sociallogin.email_addresses
            if address.verified and address.email
        }
        now = int(datetime.now(timezone.utc).timestamp())
        if (
            not subject
            or subject != sociallogin.account.uid
            or claims.get("iss") != "https://accounts.google.com"
            or not settings.GOOGLE_OAUTH_CLIENT_ID
            or settings.GOOGLE_OAUTH_CLIENT_ID not in audiences
            or expires_at <= now
            or claims.get("email_verified") is not True
            or not email
            or email not in provider_verified_emails
        ):
            # The Google provider has already performed OIDC token validation.
            # This boundary also requires the expected identity claims and a
            # verified email before any account policy decision is made.
            self._reject_google(request, "Google sign-in could not be verified.")

        User = get_user_model()
        linked = SocialAccount.objects.filter(
            provider="google", uid=subject
        ).select_related("user").first()
        process = str(sociallogin.state.get("process", "login"))

        if process == "connect":
            if (
                not request.user.is_authenticated
                or request.user.account_status != AccountStatus.ACTIVE
            ):
                messages.info(request, "Sign in to your BloodConnect account before linking Google.")
                raise ImmediateHttpResponse(redirect("accounts:login"))
            if linked and linked.user_id != request.user.pk:
                self._reject_google(request, "That Google account is already linked to another BloodConnect account.")
            if sociallogin.is_existing and sociallogin.user.pk != request.user.pk:
                self._reject_google(request, "That Google account is already linked to another BloodConnect account.")
            email_owner = User.objects.filter(email=email).first()
            if email_owner and email_owner.pk != request.user.pk:
                self._reject_google(request, "This Google email belongs to another BloodConnect account. Sign in to that account before linking.")
        else:
            if request.user.is_authenticated:
                messages.error(
                    request,
                    "For account safety, sign out before signing in with another Google account.",
                )
                raise ImmediateHttpResponse(redirect("accounts:google_link"))
            if linked:
                if linked.user.account_status != AccountStatus.ACTIVE:
                    # Existing status enforcement below redirects inactive accounts
                    # without establishing a Django session.
                    return
                if sociallogin.user.pk != linked.user_id:
                    self._reject_google(request, "Google sign-in could not be verified.")
            elif User.objects.filter(email=email).exists():
                messages.info(
                    request,
                    "This Google email is associated with a local account. Sign in with that account first, then link Google from Account access.",
                )
                raise ImmediateHttpResponse(redirect("accounts:login"))

        # The provider subject is stored in SocialAccount.uid. Discard names,
        # avatars, email claims and any other provider data after validation.
        sociallogin.account.extra_data = {}

    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)
        name = (data.get("name") or data.get("given_name") or "").strip()
        user.display_name = name[:120] or (user.email or "Google user")[:120]
        return user

    def save_user(self, request, sociallogin, form=None):
        if form is None:
            raise self.validation_error("invalid_token")

        suggested_user = sociallogin.user
        if suggested_user is None or not suggested_user.email:
            raise self.validation_error("invalid_token")

        try:
            with transaction.atomic():
                user = get_user_model().objects.create_user(
                    email=suggested_user.email,
                    display_name=suggested_user.display_name,
                    password=None,
                )
                sociallogin.user = user
                sociallogin.account.extra_data = {}
                # Persist only the provider identity. SocialLogin.save() also
                # creates allauth EmailAddress rows, but BloodConnect stores
                # its authoritative identifier and verification state on User.
                # Avoid coupling this flow to unused allauth account tables.
                sociallogin.account.user = user
                sociallogin.account.save()
        except IntegrityError as error:
            # Unique email and provider-identity constraints are authoritative
            # when concurrent callbacks race the preflight checks.
            raise self.validation_error("email_taken", "Google") from error
        return user

    def get_connect_redirect_url(self, request, socialaccount):
        return reverse("accounts:google_link")
