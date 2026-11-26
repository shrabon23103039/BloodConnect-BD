"""Registration, session authentication, password reset and throttling tests."""

import re

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.test import APIRequestFactory

from apps.accounts.forms import (
    PhoneResetCodeForm,
    PhoneResetIdentifierForm,
    VerificationIdentifierForm,
)
from apps.accounts.models import AccountStatus
from apps.api.authentication import BearerTokenAuthentication
from apps.api.models import ApiAccessToken, ApiRefreshToken
from apps.api.token_services import digest_token, issue_token_pair
from rest_framework.exceptions import AuthenticationFailed

User = get_user_model()
PASSWORD = "Synthetic-Unique-Password!947"


class AccountAuthFlowTests(TestCase):
    def setUp(self):
        cache.clear()

    def post_registration(self, **overrides):
        data = {
            "display_name": "Example Account",
            "email": "example.account@example.test",
            "phone_e164": "",
            "password1": PASSWORD,
            "password2": PASSWORD,
            "accept_terms": "on",
            "accept_privacy": "on",
        }
        data.update(overrides)
        return self.client.post(reverse("accounts:register"), data)

    def create_active_user(self, **overrides):
        values = {
            "email": "active.account@example.test",
            "display_name": "Active Example",
            "password": PASSWORD,
        }
        values.update(overrides)
        user = User.objects.create_user(**values)
        user.account_status = AccountStatus.ACTIVE
        if user.email:
            user.email_verified_at = timezone.now()
            user.save(update_fields=["account_status", "email_verified_at", "updated_at"])
        else:
            user.phone_verified_at = timezone.now()
            user.save(update_fields=["account_status", "phone_verified_at", "updated_at"])
        return user

    def test_register_email_creates_pending_account_without_logging_in(self):
        response = self.post_registration()

        self.assertRedirects(response, reverse("accounts:registration_submitted"))
        user = User.objects.get(email="example.account@example.test")
        self.assertEqual(user.account_status, AccountStatus.PENDING)
        self.assertTrue(user.check_password(PASSWORD))
        self.assertNotIn("_auth_user_id", self.client.session)
        submitted = self.client.get(reverse("accounts:registration_submitted"))
        self.assertTrue(submitted.context["account_created"])
        self.assertEqual(submitted.context["identifier_type"], "email")

    @override_settings(ALLOW_MOCK_VERIFICATION=False, DEFAULT_FROM_EMAIL="")
    def test_registration_unavailable_state_uses_public_auth_shell_without_creating_account(self):
        response = self.post_registration(
            email="",
            phone_e164="+8801700000123",
            display_name="Unavailable Example",
        )

        self.assertEqual(response.status_code, 503)
        self.assertContains(response, 'class="public-site"', status_code=503)
        self.assertContains(response, "Registration is temporarily unavailable", status_code=503)
        self.assertContains(response, "Account verification delivery is not enabled", status_code=503)
        self.assertFalse(User.objects.filter(phone_e164="+8801700000123").exists())

    def test_registration_accepts_phone_identifier_and_requires_exactly_one(self):
        response = self.post_registration(
            email="",
            phone_e164="+8801700000000",
            display_name="Phone Example",
        )
        self.assertRedirects(response, reverse("accounts:registration_submitted"))
        self.assertTrue(User.objects.filter(phone_e164="+8801700000000").exists())

    def test_registration_rejects_missing_and_both_identifiers(self):
        missing = self.post_registration(email="", phone_e164="")
        self.assertEqual(missing.status_code, 200)
        self.assertContains(missing, "Enter an email address.")
        self.assertFalse(User.objects.exists())

        both = self.post_registration(
            email="both@example.test",
            phone_e164="+8801700000000",
            identifier_type="email",
        )
        self.assertEqual(both.status_code, 200)
        self.assertContains(both, "Use only the selected Email identifier.")
        self.assertFalse(User.objects.exists())

    def test_registration_normalizes_local_bangladesh_phone_to_e164(self):
        response = self.post_registration(
            email="", phone_e164="01700000000", display_name="Local Phone Example"
        )
        self.assertRedirects(response, reverse("accounts:registration_submitted"))
        self.assertTrue(User.objects.filter(phone_e164="+8801700000000").exists())

    def test_registration_rejects_duplicate_equivalent_phone_formats(self):
        User.objects.create_user(phone_e164="+8801700000000", display_name="Existing")
        response = self.post_registration(
            email="", phone_e164="01700000000", display_name="Duplicate"
        )
        self.assertRedirects(response, reverse("accounts:registration_submitted"))
        self.assertEqual(User.objects.filter(phone_e164="+8801700000000").count(), 1)

    def test_registration_rejects_invalid_bangladesh_local_phone(self):
        response = self.post_registration(
            email="", phone_e164="0170000000", display_name="Invalid Phone"
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "E.164 format")
        self.assertFalse(User.objects.filter(display_name="Invalid Phone").exists())

    def test_phone_registration_validation_response_preserves_selected_identifier(self):
        response = self.post_registration(
            email="",
            phone_e164="0170000000",
            identifier_type="phone",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="identifier_mode_ui" value="phone" checked')
        self.assertContains(response, 'data-registration-phone-group >')
        self.assertContains(response, "E.164 format")
        self.assertFalse(User.objects.exists())

    def test_verification_form_normalizes_local_bangladesh_phone_before_validation(self):
        form = VerificationIdentifierForm({"identifier": "01700000000"})

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["identifier"], "+8801700000000")

    def test_phone_reset_forms_accept_local_and_international_formats(self):
        for form_class in (PhoneResetIdentifierForm, PhoneResetCodeForm):
            for phone in ("01700000000", "+880 170 000 0000"):
                with self.subTest(form=form_class.__name__, phone_format=phone):
                    data = {"phone_e164": phone}
                    if form_class is PhoneResetCodeForm:
                        data["code"] = "123456"
                    form = form_class(data)
                    self.assertTrue(form.is_valid(), form.errors)
                    self.assertEqual(form.cleaned_data["phone_e164"], "+8801700000000")

    def test_phone_reset_forms_reject_invalid_bangladesh_mobile(self):
        for form_class in (PhoneResetIdentifierForm, PhoneResetCodeForm):
            with self.subTest(form=form_class.__name__):
                data = {"phone_e164": "+8801100000000"}
                if form_class is PhoneResetCodeForm:
                    data["code"] = "123456"
                form = form_class(data)
                self.assertFalse(form.is_valid())
                self.assertIn("phone_e164", form.errors)

    def test_phone_reset_pages_render_phone_format_help(self):
        for route in ("accounts:phone_password_reset", "accounts:phone_password_reset_verify"):
            with self.subTest(route=route):
                response = self.client.get(reverse(route))
                self.assertContains(response, "Phone number")
                self.assertContains(response, "01XXXXXXXXX or +8801XXXXXXXXX")

    def test_registration_validates_password_confirmation_and_policy_acceptance(self):
        mismatch = self.post_registration(password2="Different-Unique-Password!42")
        self.assertEqual(mismatch.status_code, 200)
        self.assertFalse(User.objects.exists())

        missing_acceptance = self.post_registration(accept_terms="")
        self.assertEqual(missing_acceptance.status_code, 200)
        self.assertFalse(User.objects.exists())

        missing_privacy_acknowledgement = self.post_registration(accept_privacy="")
        self.assertEqual(missing_privacy_acknowledgement.status_code, 200)
        self.assertFalse(User.objects.exists())

        oversized = "A" * 129
        too_long = self.post_registration(password1=oversized, password2=oversized)
        self.assertEqual(too_long.status_code, 200)
        self.assertFalse(User.objects.exists())

    def test_registration_response_does_not_disclose_duplicate_identifier(self):
        User.objects.create_user(
            email="example.account@example.test",
            display_name="Existing Example",
            password=PASSWORD,
        )

        response = self.post_registration()

        self.assertRedirects(response, reverse("accounts:registration_submitted"))
        self.assertEqual(User.objects.count(), 1)

    @override_settings(ALLOW_MOCK_VERIFICATION=False)
    def test_registration_fails_closed_when_no_verification_provider_exists(self):
        response = self.post_registration()

        self.assertEqual(response.status_code, 503)
        self.assertContains(response, "No account was created", status_code=503)
        self.assertFalse(User.objects.exists())

    def test_login_accepts_normalized_email_and_phone_only_when_active(self):
        email_user = self.create_active_user()
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "  ACTIVE.ACCOUNT@EXAMPLE.TEST ", "password": PASSWORD},
        )
        self.assertRedirects(response, reverse("home"))
        self.assertEqual(self.client.session["_auth_user_id"], str(email_user.pk))

    def test_login_honors_local_next_and_rejects_external_next(self):
        user = self.create_active_user()
        local_path = reverse("donors:profile")

        local_response = self.client.post(
            f"{reverse('accounts:login')}?next={local_path}",
            {"username": user.email, "password": PASSWORD, "next": local_path},
        )
        self.assertRedirects(local_response, local_path, fetch_redirect_response=False)

        self.client.logout()
        external_response = self.client.post(
            f"{reverse('accounts:login')}?next=https://attacker.example/collect",
            {
                "username": user.email,
                "password": PASSWORD,
                "next": "https://attacker.example/collect",
            },
        )
        self.assertRedirects(
            external_response, reverse("home"), fetch_redirect_response=False
        )

        self.client.post(reverse("accounts:logout"))
        phone_user = self.create_active_user(
            email=None,
            phone_e164="+8801700000000",
            display_name="Phone Example",
        )
        response = self.client.post(
            reverse("accounts:login"),
            {"username": " 01700000000 ", "password": PASSWORD},
        )
        self.assertRedirects(response, reverse("home"))
        self.assertEqual(self.client.session["_auth_user_id"], str(phone_user.pk))

    def test_login_failure_is_generic_and_pending_accounts_cannot_sign_in(self):
        User.objects.create_user(
            email="pending@example.test", display_name="Pending Example", password=PASSWORD
        )
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "pending@example.test", "password": PASSWORD},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Email or phone and password were not accepted")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_rotates_existing_session_key(self):
        user = self.create_active_user()
        session = self.client.session
        session["unrelated_session_data"] = "preserved"
        session.save()
        old_session_key = self.client.session.session_key

        response = self.client.post(
            reverse("accounts:login"),
            {"username": user.email, "password": PASSWORD},
        )

        self.assertRedirects(response, reverse("home"))
        self.assertNotEqual(self.client.session.session_key, old_session_key)
        self.assertEqual(self.client.session["unrelated_session_data"], "preserved")

    def test_login_attempt_does_not_log_identifier_or_password(self):
        identifier = "private-identifier@example.test"
        with self.assertLogs("bloodconnect.request", level="INFO") as captured:
            self.client.post(
                reverse("accounts:login"),
                {"username": identifier, "password": PASSWORD},
            )

        output = "\n".join(captured.output)
        self.assertNotIn(identifier, output)
        self.assertNotIn(PASSWORD, output)

    def test_logout_requires_post_and_clears_session(self):
        self.create_active_user()
        self.client.post(
            reverse("accounts:login"),
            {"username": "active.account@example.test", "password": PASSWORD},
        )

        get_response = self.client.get(reverse("accounts:logout"))
        self.assertEqual(get_response.status_code, 405)
        post_response = self.client.post(reverse("accounts:logout"))
        self.assertRedirects(post_response, reverse("home"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_form_uses_csrf_protection(self):
        csrf_client = self.client_class(enforce_csrf_checks=True)
        response = csrf_client.get(reverse("accounts:login"))
        self.assertEqual(response.status_code, 200)
        rejected = csrf_client.post(
            reverse("accounts:login"),
            {"username": "unknown", "password": "wrong"},
        )
        self.assertEqual(rejected.status_code, 403)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_password_reset_sends_one_time_link_and_updates_password(self):
        user = self.create_active_user()
        token_pair = issue_token_pair(user=user)
        other_session_client = self.client_class()
        existing_login = other_session_client.post(
            reverse("accounts:login"),
            {"username": user.email, "password": PASSWORD},
        )
        self.assertRedirects(existing_login, reverse("home"))
        self.assertIn("_auth_user_id", other_session_client.session)

        response = self.client.post(
            reverse("accounts:password_reset"), {"email": user.email}
        )
        self.assertRedirects(response, reverse("accounts:password_reset_done"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertNotIn(PASSWORD, mail.outbox[0].body)
        path_match = re.search(
            r"http://testserver(/accounts/password-reset/[^\s]+)", mail.outbox[0].body
        )
        self.assertIsNotNone(path_match)

        session = self.client.session
        session["unrelated_session_data"] = "preserved"
        session.save()
        session_key_before_reset = self.client.session.session_key
        reset_path = path_match.group(1)
        reset_page = self.client.get(reset_path, follow=True)
        self.assertEqual(reset_page.status_code, 200)
        self.assertNotEqual(self.client.session.session_key, session_key_before_reset)
        self.assertEqual(self.client.session["unrelated_session_data"], "preserved")
        reset_form_path = reset_page.request["PATH_INFO"]
        new_password = "New-Synthetic-Password!6284"
        complete = self.client.post(
            reset_form_path,
            {"new_password1": new_password, "new_password2": new_password},
        )
        self.assertRedirects(complete, reverse("accounts:password_reset_complete"))
        reused_link = self.client.get(reset_form_path)
        self.assertContains(
            reused_link, "This reset link is invalid or has already been used."
        )
        user.refresh_from_db()
        self.assertTrue(user.check_password(new_password))
        self.assertFalse(user.check_password(PASSWORD))
        access = ApiAccessToken.objects.get(
            token_digest=digest_token(token_pair["access_token"])
        )
        refresh = ApiRefreshToken.objects.get(
            token_digest=digest_token(token_pair["refresh_token"])
        )
        self.assertIsNotNone(access.revoked_at)
        self.assertIsNotNone(refresh.revoked_at)
        with self.assertRaises(AuthenticationFailed):
            BearerTokenAuthentication().authenticate(
                APIRequestFactory().get(
                    "/api/v1/protected/",
                    HTTP_AUTHORIZATION=f"Bearer {token_pair['access_token']}",
                )
            )
        protected = other_session_client.get(reverse("donors:profile"))
        self.assertEqual(protected.status_code, 302)
        self.assertNotIn("_auth_user_id", other_session_client.session)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_password_reset_delivery_failure_is_generic_and_redacted(self):
        from unittest.mock import patch

        user = self.create_active_user()
        with patch(
            "django.core.mail.message.EmailMultiAlternatives.send",
            side_effect=OSError("synthetic SMTP failure"),
        ):
            with self.assertLogs("bloodconnect.password_reset", level="WARNING") as logs:
                failed = self.client.post(
                    reverse("accounts:password_reset"), {"email": user.email}
                )
        unknown = self.client.post(
            reverse("accounts:password_reset"), {"email": "unknown@example.test"}
        )

        self.assertRedirects(failed, reverse("accounts:password_reset_done"))
        self.assertRedirects(unknown, reverse("accounts:password_reset_done"))
        self.assertNotIn(user.email, "\n".join(logs.output))
        self.assertNotIn("synthetic SMTP failure", "\n".join(logs.output))
        self.assertNotIn("Traceback", "\n".join(logs.output))

    @override_settings(PASSWORD_RESET_TIMEOUT=-1)
    def test_expired_email_reset_link_is_rejected(self):
        user = self.create_active_user()
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        response = self.client.get(
            reverse(
                "accounts:password_reset_confirm",
                kwargs={"uidb64": uidb64, "token": token},
            ),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, "This reset link is invalid or has already been used."
        )

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_password_reset_response_does_not_disclose_unknown_email(self):
        response = self.client.post(
            reverse("accounts:password_reset"), {"email": "unknown@example.test"}
        )

        self.assertRedirects(response, reverse("accounts:password_reset_done"))
        self.assertEqual(mail.outbox, [])
        self.assertContains(
            self.client.get(reverse("accounts:password_reset_done")),
            "If an active account matches",
        )

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_password_reset_requires_an_active_verified_email(self):
        user = User.objects.create_user(
            email="unverified@example.test",
            display_name="Unverified Example",
            password=PASSWORD,
        )
        user.account_status = AccountStatus.ACTIVE
        user.save(update_fields=["account_status", "updated_at"])

        response = self.client.post(
            reverse("accounts:password_reset"), {"email": user.email}
        )

        self.assertRedirects(response, reverse("accounts:password_reset_done"))
        self.assertEqual(mail.outbox, [])

    def test_sensitive_auth_forms_are_rate_limited(self):
        for _ in range(10):
            response = self.client.post(
                reverse("accounts:login"), {"username": "nobody", "password": "wrong"}
            )
            self.assertEqual(response.status_code, 200)
        limited = self.client.post(
            reverse("accounts:login"), {"username": "nobody", "password": "wrong"}
        )
        self.assertEqual(limited.status_code, 429)
        self.assertEqual(limited["Retry-After"], "60")

    @override_settings(
        DEBUG=True,
        DEVELOPMENT_THROTTLE_OVERRIDES={"login": (1000, 3600)},
    )
    def test_development_throttle_override_allows_repeated_local_login_testing(self):
        for _ in range(25):
            response = self.client.post(
                reverse("accounts:login"), {"username": "nobody", "password": "wrong"}
            )
            self.assertEqual(response.status_code, 200)

    def test_registration_and_password_reset_have_separate_throttles(self):
        for index in range(5):
            response = self.post_registration(
                email=f"account-{index}@example.test", display_name=f"Account {index}"
            )
            self.assertEqual(response.status_code, 302)
        self.assertEqual(self.post_registration(email="sixth@example.test").status_code, 429)

        for _ in range(5):
            response = self.client.post(
                reverse("accounts:password_reset"), {"email": "unknown@example.test"}
            )
            self.assertEqual(response.status_code, 302)
        limited = self.client.post(
            reverse("accounts:password_reset"), {"email": "unknown@example.test"}
        )
        self.assertEqual(limited.status_code, 429)
        self.assertEqual(limited["Retry-After"], "3600")
