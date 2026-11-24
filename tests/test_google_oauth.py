from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlparse

import pytest
from django import forms
from django.contrib.auth import get_user_model
from allauth.core.exceptions import ImmediateHttpResponse
from allauth.socialaccount.models import SocialAccount
from allauth.socialaccount.providers.base import AuthError
from django.contrib.auth.models import AnonymousUser
from django.contrib.messages.storage.fallback import FallbackStorage
from django.db import ProgrammingError
from django.contrib.auth import SESSION_KEY
from django.test import Client, RequestFactory, SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone as django_timezone

from apps.accounts.models import (
    AccountStatus,
    VerificationChallenge,
    VerificationPurpose,
)
from apps.accounts.social_auth import (
    BloodConnectAccountAdapter,
    BloodConnectSocialAccountAdapter,
)
from apps.accounts.social_forms import GoogleSocialSignupForm
from apps.accounts.verification import mock_verification_provider


@override_settings(
    GOOGLE_OAUTH_ENABLED=True,
    GOOGLE_OAUTH_CLIENT_ID="synthetic-client-id.apps.googleusercontent.com",
    GOOGLE_OAUTH_CLIENT_SECRET="synthetic-client-secret",
    SOCIALACCOUNT_PROVIDERS={
        "google": {
            "APP": {
                "client_id": "synthetic-client-id.apps.googleusercontent.com",
                "secret": "synthetic-client-secret",
                "key": "",
            },
            "SCOPE": ["openid", "email", "profile"],
            "OAUTH_PKCE_ENABLED": True,
        }
    },
)
class GoogleOAuthEntryTests(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)

    def _csrf_post(self, url):
        self.client.get(reverse("accounts:login"))
        token = self.client.cookies["csrftoken"].value
        return self.client.post(url, HTTP_X_CSRFTOKEN=token)

    def test_login_and_registration_render_google_action(self):
        for route in ("accounts:login", "accounts:register"):
            response = self.client.get(reverse(route))
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "Continue with Google")
            self.assertContains(response, 'method="post"')
            self.assertContains(response, 'name="csrfmiddlewaretoken"')

    def test_oauth_start_requires_post_and_redirects_to_google(self):
        response = self.client.get(reverse("google_login"))
        self.assertEqual(response.status_code, 405)
        response = self._csrf_post(reverse("google_login"))
        self.assertEqual(response.status_code, 302)
        target = urlparse(response["Location"])
        self.assertEqual(target.hostname, "accounts.google.com")
        query = parse_qs(target.query)
        self.assertEqual(query.get("client_id"), ["synthetic-client-id.apps.googleusercontent.com"])
        self.assertEqual(set(query.get("scope", [""])[0].split()), {"openid", "email", "profile"})
        self.assertTrue(query.get("state"))
        self.assertEqual(query.get("code_challenge_method"), ["S256"])
        self.assertTrue(query.get("code_challenge"))

    @override_settings(GOOGLE_OAUTH_ENABLED=False)
    def test_disabled_google_action_falls_back_to_local_login(self):
        response = self._csrf_post(reverse("google_login"))
        self.assertRedirects(response, reverse("accounts:login"), fetch_redirect_response=False)


@override_settings(GOOGLE_OAUTH_CLIENT_ID="synthetic-client-id")
class GoogleClaimPolicyTests(SimpleTestCase):
    def setUp(self):
        self.adapter = BloodConnectSocialAccountAdapter()
        self.request = RequestFactory().get(reverse("accounts:login"))
        self.request.user = AnonymousUser()
        self.request.session = {}
        self.request._messages = FallbackStorage(self.request)
        self.claims = {
            "sub": "google-subject",
            "iss": "https://accounts.google.com",
            "aud": "synthetic-client-id",
            "exp": int((datetime.now(timezone.utc) + timedelta(minutes=5)).timestamp()),
            "email_verified": True,
        }
        self.sociallogin = self.make_sociallogin(self.claims)

    @staticmethod
    def make_sociallogin(claims):
        verified_email = SimpleNamespace(email="person@example.test", verified=True)
        return SimpleNamespace(
            account=SimpleNamespace(provider="google", uid="google-subject", extra_data=claims),
            user=SimpleNamespace(email="person@example.test"),
            email_addresses=[verified_email],
            state={"process": "login"},
        )

    def test_missing_or_invalid_google_claims_are_rejected_safely(self):
        invalid_claims = (
            {},
            {**self.claims, "iss": "https://attacker.example"},
            {**self.claims, "aud": "another-client"},
            {**self.claims, "exp": 1},
            {**self.claims, "sub": "different-subject"},
            {**self.claims, "email_verified": False},
        )
        for claims in invalid_claims:
            with self.subTest(claims=claims):
                with self.assertRaises(ImmediateHttpResponse) as raised:
                    self.adapter.pre_social_login(self.request, self.make_sociallogin(claims))
                self.assertEqual(raised.exception.response.status_code, 302)
                self.assertEqual(raised.exception.response.url, reverse("accounts:login"))

    def test_provider_identity_must_be_google(self):
        self.sociallogin.account.provider = "untrusted"
        with self.assertRaises(ImmediateHttpResponse):
            self.adapter.pre_social_login(self.request, self.sociallogin)

    def test_google_cancel_and_provider_error_use_generic_safe_redirects(self):
        for error in (AuthError.CANCELLED, AuthError.UNKNOWN):
            with self.subTest(error=error):
                with self.assertRaises(ImmediateHttpResponse) as raised:
                    self.adapter.on_authentication_error(
                        self.request,
                        SimpleNamespace(id="google"),
                        error=error,
                        exception=RuntimeError("synthetic secret token detail"),
                    )
                self.assertEqual(raised.exception.response.status_code, 302)
                self.assertEqual(raised.exception.response.url, reverse("accounts:login"))

    def test_matching_local_email_without_google_link_is_not_auto_merged(self):
        linked_query = Mock()
        linked_query.select_related.return_value.first.return_value = None
        user_model = Mock()
        user_model.objects.filter.return_value.exists.return_value = True
        with patch("apps.accounts.social_auth.SocialAccount.objects.filter", return_value=linked_query), patch(
            "apps.accounts.social_auth.get_user_model", return_value=user_model
        ):
            with self.assertRaises(ImmediateHttpResponse) as raised:
                self.adapter.pre_social_login(self.request, self.sociallogin)
        self.assertEqual(raised.exception.response.url, reverse("accounts:login"))


class GoogleLinkPolicyTests(GoogleClaimPolicyTests):
    def setUp(self):
        super().setUp()
        self.sociallogin.state = {"process": "connect"}
        self.sociallogin.is_existing = False
        self.linked_query = Mock()
        self.linked_query.select_related.return_value.first.return_value = None
        self.social_filter = patch(
            "apps.accounts.social_auth.SocialAccount.objects.filter",
            return_value=self.linked_query,
        )
        self.social_filter.start()
        self.addCleanup(self.social_filter.stop)
        self.user_model = Mock()
        self.user_model.objects.filter.return_value.first.return_value = None
        self.user_patch = patch("apps.accounts.social_auth.get_user_model", return_value=self.user_model)
        self.user_patch.start()
        self.addCleanup(self.user_patch.stop)

    def test_link_requires_authenticated_active_user(self):
        with self.assertRaises(ImmediateHttpResponse) as raised:
            self.adapter.pre_social_login(self.request, self.sociallogin)
        self.assertEqual(raised.exception.response.url, reverse("accounts:login"))

    def test_active_user_can_explicitly_link_unclaimed_google_identity(self):
        self.request.user = SimpleNamespace(is_authenticated=True, account_status=AccountStatus.ACTIVE, pk="owner")
        self.adapter.pre_social_login(self.request, self.sociallogin)
        self.assertEqual(self.sociallogin.account.extra_data, {})

    def test_google_identity_linked_to_another_user_is_rejected(self):
        self.request.user = SimpleNamespace(is_authenticated=True, account_status=AccountStatus.ACTIVE, pk="owner")
        self.linked_query.select_related.return_value.first.return_value = SimpleNamespace(
            user_id="another-owner", user=SimpleNamespace(account_status=AccountStatus.ACTIVE)
        )
        with self.assertRaises(ImmediateHttpResponse) as raised:
            self.adapter.pre_social_login(self.request, self.sociallogin)
        self.assertEqual(raised.exception.response.status_code, 302)

    def test_new_user_is_created_through_existing_manager_without_password(self):
        proposed_user = SimpleNamespace(email="person@example.test", display_name="Synthetic Google User")
        sociallogin = SimpleNamespace(
            user=proposed_user,
            account=SimpleNamespace(extra_data={"email": "person@example.test"}, save=Mock()),
            save=Mock(),
        )
        manager = Mock()
        manager.objects.create_user.return_value = proposed_user
        with patch("apps.accounts.social_auth.get_user_model", return_value=manager), patch(
            "apps.accounts.social_auth.transaction.atomic"
        ):
            created = BloodConnectSocialAccountAdapter().save_user(
                self.request, sociallogin, form=object()
            )
        self.assertIs(created, proposed_user)
        manager.objects.create_user.assert_called_once_with(
            email="person@example.test", display_name="Synthetic Google User", password=None
        )
        self.assertEqual(sociallogin.account.user, proposed_user)
        sociallogin.account.save.assert_called_once_with()
        sociallogin.save.assert_not_called()
        self.assertEqual(sociallogin.account.extra_data, {})

@override_settings(
    SOCIALACCOUNT_PROVIDERS={
        "google": {
            "APP": {
                "client_id": "settings-client-id",
                "secret": "settings-client-secret",
                "key": "",
            },
            "SCOPE": ["openid", "email", "profile"],
        }
    }
)
class SettingsBackedProviderTests(SimpleTestCase):
    def test_google_app_is_resolved_from_settings_without_socialapp_query(self):
        from allauth.socialaccount.models import SocialApp

        request = RequestFactory().get("/")
        adapter = BloodConnectSocialAccountAdapter()
        with patch.object(SocialApp.objects, "on_site", side_effect=AssertionError("database lookup")):
            apps = adapter.list_apps(request, provider="google")
        self.assertEqual(len(apps), 1)
        self.assertEqual(apps[0].client_id, "settings-client-id")
        self.assertEqual(apps[0].secret, "settings-client-secret")


@override_settings(DEBUG=True)
class GoogleOAuthCallbackErrorTests(SimpleTestCase):
    def test_callback_database_error_returns_safe_page_and_sanitized_log(self):
        from config.logging import JsonFormatter
        import json

        with patch(
            "apps.accounts.views.oauth2_callback",
            side_effect=ProgrammingError('relation "socialaccount_socialaccount" does not exist'),
        ):
            with self.assertLogs("bloodconnect.oauth", level="ERROR") as captured:
                response = self.client.get(reverse("google_callback"))

        self.assertEqual(response.status_code, 503)
        self.assertContains(response, "Google sign-in could not be completed", status_code=503)
        self.assertContains(response, 'class="public-site"', status_code=503)
        self.assertContains(response, "css/public_web.css", status_code=503)
        self.assertNotContains(response, "socialaccount_socialaccount", status_code=503)
        self.assertNotContains(response, "Traceback", status_code=503)
        record = captured.records[0]
        self.assertEqual(record.error_type, "ProgrammingError")
        self.assertIsNone(record.exc_info)
        structured = json.loads(JsonFormatter().format(record))
        self.assertEqual(structured["event"], "oauth_callback_failed")
        self.assertEqual(structured["error_type"], "ProgrammingError")
        self.assertNotIn("relation", json.dumps(structured))


class GoogleSignupEmailPolicyTests(TestCase):
    def test_duplicate_check_uses_bloodconnect_user_email_without_emailaddress_table(self):
        User = get_user_model()
        User.objects.create_user(
            email="person@example.test",
            display_name="Existing local user",
            password=None,
        )
        with patch(
            "allauth.account.models.EmailAddress.objects.filter",
            side_effect=AssertionError("allauth EmailAddress must not be queried"),
        ):
            with self.assertRaises(forms.ValidationError):
                GoogleSocialSignupForm.validate_unique_email(None, "person@example.test")

    def test_new_email_is_normalized_without_emailaddress_table(self):
        with patch(
            "allauth.account.models.EmailAddress.objects.filter",
            side_effect=AssertionError("allauth EmailAddress must not be queried"),
        ):
            value = GoogleSocialSignupForm.validate_unique_email(None, "New.Person@Example.test")
        self.assertEqual(value, "new.person@example.test")


class GoogleSignupVerificationPolicyTests(TestCase):
    def setUp(self):
        mock_verification_provider.clear()

    def test_google_created_user_remains_pending_and_locally_unverified(self):
        request = RequestFactory().post("/accounts/google/login/callback/")
        request.user = AnonymousUser()
        request.session = {}
        sociallogin = SimpleNamespace(
            user=get_user_model()(email="google-user@example.test", display_name="Google User"),
            account=SocialAccount(provider="google", uid="synthetic-google-subject"),
        )

        user = BloodConnectSocialAccountAdapter().save_user(
            request,
            sociallogin,
            form=object(),
        )

        user.refresh_from_db()
        self.assertEqual(user.account_status, AccountStatus.PENDING)
        self.assertIsNone(user.email_verified_at)
        self.assertFalse(user.has_usable_password())
        self.assertTrue(
            SocialAccount.objects.filter(
                user=user,
                provider="google",
                uid="synthetic-google-subject",
            ).exists()
        )

    @override_settings(
        DEBUG=True,
        DEVELOPMENT_VERIFICATION_SEND_COOLDOWN_SECONDS=0,
        DEVELOPMENT_VERIFICATION_MAX_SENDS_PER_HOUR=1000,
    )
    @override_settings(GOOGLE_OAUTH_CLIENT_ID="synthetic-client-id.apps.googleusercontent.com")
    def test_pending_google_signup_auto_requests_once_and_opens_email_code_form(self):
        request = RequestFactory().post("/accounts/google/login/callback/")
        request.user = AnonymousUser()
        request.session = {"registration_created": True}
        request._messages = FallbackStorage(request)
        google_email = "google-user@example.test"
        google_subject = "synthetic-google-subject"
        claims = {
            "sub": google_subject,
            "iss": "https://accounts.google.com",
            "aud": "synthetic-client-id.apps.googleusercontent.com",
            "exp": int((datetime.now(timezone.utc) + timedelta(minutes=5)).timestamp()),
            "email_verified": True,
        }
        sociallogin = SimpleNamespace(
            user=get_user_model()(email=google_email, display_name="Google User"),
            account=SocialAccount(
                provider="google", uid=google_subject, extra_data=claims
            ),
            email_addresses=[
                SimpleNamespace(email=google_email, verified=True)
            ],
            state={"process": "login"},
            is_existing=False,
        )

        BloodConnectSocialAccountAdapter().pre_social_login(request, sociallogin)
        user = BloodConnectSocialAccountAdapter().save_user(
            request, sociallogin, form=object()
        )
        account_adapter = BloodConnectAccountAdapter()
        first_callback_response = account_adapter.respond_user_inactive(request, user)

        self.assertEqual(first_callback_response.url, reverse("accounts:verify"))
        self.assertEqual(request.session["verification_identifier"], user.email)
        self.assertTrue(request.session["verification_code_only"])
        self.assertNotIn("registration_created", request.session)
        self.assertEqual(len(mock_verification_provider.messages), 1)
        self.assertTrue(
            VerificationChallenge.objects.filter(
                user=user, purpose=VerificationPurpose.ACCOUNT
            ).exists()
        )
        self.assertEqual(mock_verification_provider.messages[-1].destination, user.email)
        code = mock_verification_provider.messages[-1].code

        # Replaying the pending-account callback reuses the live challenge.
        retry_response = account_adapter.respond_user_inactive(request, user)
        self.assertEqual(retry_response.url, reverse("accounts:verify"))
        self.assertEqual(len(mock_verification_provider.messages), 1)
        self.assertEqual(
            VerificationChallenge.objects.filter(user=user).count(), 1
        )

        session = self.client.session
        session.update(request.session)
        session.save()
        verify_url = reverse("accounts:verify")
        page = self.client.get(verify_url)
        self.assertContains(page, user.email)
        self.assertContains(page, 'type="hidden" name="identifier"')
        self.assertContains(page, 'name="code"')
        self.assertNotContains(page, "Email or phone")
        self.assertEqual(len(mock_verification_provider.messages), 1)
        self.client.get(verify_url)
        self.assertEqual(len(mock_verification_provider.messages), 1)
        self.assertEqual(
            VerificationChallenge.objects.filter(user=user).count(), 1
        )

        verified = self.client.post(
            verify_url,
            {"identifier": "tampered@example.test", "code": code},
        )
        self.assertRedirects(verified, reverse("accounts:login"))
        user.refresh_from_db()
        self.assertEqual(user.account_status, AccountStatus.ACTIVE)
        self.assertEqual(user.email, "google-user@example.test")
        self.assertIsNotNone(user.email_verified_at)

    @override_settings(GOOGLE_OAUTH_CLIENT_ID="synthetic-client-id.apps.googleusercontent.com")
    def test_active_verified_google_account_does_not_get_another_challenge(self):
        user = get_user_model().objects.create_user(
            email="verified-google@example.test",
            display_name="Verified Google User",
            password=None,
        )
        user.account_status = AccountStatus.ACTIVE
        user.email_verified_at = django_timezone.now()
        user.save(update_fields=["account_status", "email_verified_at", "updated_at"])
        socialaccount = SocialAccount.objects.create(
            user=user, provider="google", uid="verified-google-subject"
        )
        claims = {
            "sub": socialaccount.uid,
            "iss": "https://accounts.google.com",
            "aud": "synthetic-client-id.apps.googleusercontent.com",
            "exp": int((datetime.now(timezone.utc) + timedelta(minutes=5)).timestamp()),
            "email_verified": True,
        }
        sociallogin = GoogleClaimPolicyTests.make_sociallogin(claims)
        sociallogin.user = user
        sociallogin.account.uid = socialaccount.uid
        sociallogin.email_addresses[0].email = user.email
        request = RequestFactory().get("/accounts/google/login/callback/")
        request.user = AnonymousUser()
        request.session = {}
        request._messages = FallbackStorage(request)

        BloodConnectSocialAccountAdapter().pre_social_login(request, sociallogin)

        self.assertEqual(user.account_status, AccountStatus.ACTIVE)
        self.assertEqual(VerificationChallenge.objects.filter(user=user).count(), 0)
        self.assertEqual(len(mock_verification_provider.messages), 0)

    @override_settings(GOOGLE_OAUTH_CLIENT_ID="synthetic-client-id.apps.googleusercontent.com")
    def test_existing_linked_google_user_is_authenticated_and_redirected_to_home(self):
        user = get_user_model().objects.create_user(
            email="existing-google@example.test",
            display_name="Existing Google User",
            password=None,
        )
        user.account_status = AccountStatus.ACTIVE
        user.email_verified_at = django_timezone.now()
        user.save(update_fields=["account_status", "email_verified_at", "updated_at"])
        account = SocialAccount.objects.create(
            user=user,
            provider="google",
            uid="existing-google-subject",
            extra_data={
                "sub": "existing-google-subject",
                "iss": "https://accounts.google.com",
                "aud": "synthetic-client-id.apps.googleusercontent.com",
                "exp": int((datetime.now(timezone.utc) + timedelta(minutes=5)).timestamp()),
                "email_verified": True,
            },
        )
        claims = {
            "sub": account.uid,
            "iss": "https://accounts.google.com",
            "aud": "synthetic-client-id.apps.googleusercontent.com",
            "exp": int((datetime.now(timezone.utc) + timedelta(minutes=5)).timestamp()),
            "email_verified": True,
        }
        sociallogin = GoogleClaimPolicyTests.make_sociallogin(claims)
        sociallogin.user = user
        sociallogin.account = account
        sociallogin.email_addresses[0].email = user.email
        sociallogin.state = {"process": "login"}

        def complete_existing_social_login(request):
            BloodConnectSocialAccountAdapter().pre_social_login(request, sociallogin)
            from allauth.account.utils import perform_login

            return perform_login(
                request,
                user,
                signal_kwargs={"sociallogin": sociallogin},
            )

        with patch(
            "apps.accounts.views.oauth2_callback",
            side_effect=complete_existing_social_login,
        ):
            callback_response = self.client.get(reverse("google_callback"))

        self.assertEqual(callback_response.status_code, 302)
        self.assertEqual(callback_response["Location"], reverse("home"))
        self.assertNotEqual(callback_response["Location"], reverse("accounts:google_link"))
        self.assertEqual(self.client.session[SESSION_KEY], str(user.pk))
        destination = self.client.get(callback_response["Location"])
        self.assertEqual(destination.status_code, 200)
        self.assertTrue(destination.wsgi_request.user.is_authenticated)
        self.assertEqual(destination.wsgi_request.user.pk, user.pk)
        self.assertEqual(VerificationChallenge.objects.filter(user=user).count(), 0)
