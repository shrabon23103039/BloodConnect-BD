"""Verification challenge persistence, expiry, abuse and web-flow tests."""

from datetime import timedelta
from io import StringIO

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import (
    AccountStatus,
    VerificationChallenge,
    VerificationChannel,
    VerificationPurpose,
)
from apps.accounts.verification import (
    CODE_LIFETIME_SECONDS,
    VerificationDeliveryError,
    VerificationRateLimited,
    VerificationUnavailable,
    consume_challenge,
    issue_challenge,
    mock_verification_provider,
)

User = get_user_model()
PASSWORD = "Synthetic-Unique-Password!947"


class VerificationServiceTests(TestCase):
    def setUp(self):
        cache.clear()
        mock_verification_provider.clear()
        self.user = User.objects.create_user(
            email="pending@example.test",
            display_name="Pending Example",
            password=PASSWORD,
        )

    def test_account_code_is_hmac_only_and_activates_verified_email(self):
        challenge = issue_challenge(self.user, VerificationPurpose.ACCOUNT)
        message = mock_verification_provider.messages[-1]
        challenge.refresh_from_db()

        self.assertEqual(message.challenge_id, challenge.id)
        self.assertEqual(message.channel, VerificationChannel.EMAIL)
        self.assertEqual(len(message.code), 6)
        self.assertTrue(message.code.isdigit())
        self.assertEqual(len(challenge.code_digest), 64)
        self.assertNotEqual(challenge.code_digest, message.code)
        lifetime = (challenge.expires_at - challenge.created_at).total_seconds()
        self.assertLessEqual(lifetime, CODE_LIFETIME_SECONDS)
        self.assertGreater(lifetime, CODE_LIFETIME_SECONDS - 1)

        self.assertTrue(consume_challenge(self.user, VerificationPurpose.ACCOUNT, message.code))
        self.user.refresh_from_db()
        challenge.refresh_from_db()
        self.assertEqual(self.user.account_status, AccountStatus.ACTIVE)
        self.assertIsNotNone(self.user.email_verified_at)
        self.assertIsNotNone(challenge.consumed_at)
        self.assertFalse(consume_challenge(self.user, VerificationPurpose.ACCOUNT, message.code))

    def test_phone_account_verification_sets_only_phone_timestamp(self):
        user = User.objects.create_user(
            phone_e164="+8801700000000",
            display_name="Phone Example",
            password=PASSWORD,
        )
        issue_challenge(user, VerificationPurpose.ACCOUNT)
        message = mock_verification_provider.messages[-1]

        self.assertEqual(message.channel, VerificationChannel.PHONE)
        self.assertTrue(consume_challenge(user, VerificationPurpose.ACCOUNT, message.code))
        user.refresh_from_db()
        self.assertEqual(user.account_status, AccountStatus.ACTIVE)
        self.assertIsNotNone(user.phone_verified_at)
        self.assertIsNone(user.email_verified_at)

    def test_expired_and_replayed_codes_are_rejected(self):
        challenge = issue_challenge(self.user, VerificationPurpose.ACCOUNT)
        message = mock_verification_provider.messages[-1]
        now = timezone.now()
        VerificationChallenge.objects.filter(pk=challenge.pk).update(
            created_at=now - timedelta(minutes=11),
            expires_at=now - timedelta(minutes=1),
        )

        self.assertFalse(consume_challenge(self.user, VerificationPurpose.ACCOUNT, message.code))
        self.assertFalse(consume_challenge(self.user, VerificationPurpose.ACCOUNT, message.code))
        self.user.refresh_from_db()
        self.assertEqual(self.user.account_status, AccountStatus.PENDING)

    def test_wrong_code_is_counted_and_locks_after_five_attempts(self):
        challenge = issue_challenge(self.user, VerificationPurpose.ACCOUNT)

        for _ in range(5):
            self.assertFalse(consume_challenge(self.user, VerificationPurpose.ACCOUNT, "999999"))
        challenge.refresh_from_db()
        self.assertEqual(challenge.failed_attempts, 5)
        self.assertIsNotNone(challenge.consumed_at)
        self.assertFalse(consume_challenge(self.user, VerificationPurpose.ACCOUNT, "000000"))

    def test_resend_invalidates_previous_code_and_enforces_cooldown(self):
        first = issue_challenge(self.user, VerificationPurpose.ACCOUNT)
        first_code = mock_verification_provider.messages[-1].code
        with self.assertRaises(VerificationRateLimited):
            issue_challenge(self.user, VerificationPurpose.ACCOUNT)

        VerificationChallenge.objects.filter(pk=first.pk).update(
            created_at=timezone.now() - timedelta(seconds=61)
        )
        second = issue_challenge(self.user, VerificationPurpose.ACCOUNT)
        self.assertEqual(mock_verification_provider.messages[-1].challenge_id, second.id)
        first.refresh_from_db()
        self.assertIsNotNone(first.consumed_at)
        self.assertFalse(consume_challenge(self.user, VerificationPurpose.ACCOUNT, first_code))

    @override_settings(
        DEBUG=True,
        DEVELOPMENT_VERIFICATION_SEND_COOLDOWN_SECONDS=0,
        DEVELOPMENT_VERIFICATION_MAX_SENDS_PER_HOUR=1000,
    )
    def test_idempotent_challenge_request_reuses_live_challenge_without_resending(self):
        first = issue_challenge(
            self.user,
            VerificationPurpose.ACCOUNT,
            reuse_unexpired=True,
        )
        retry = issue_challenge(
            self.user,
            VerificationPurpose.ACCOUNT,
            reuse_unexpired=True,
        )

        self.assertEqual(retry.pk, first.pk)
        self.assertEqual(VerificationChallenge.objects.filter(user=self.user).count(), 1)
        self.assertEqual(len(mock_verification_provider.messages), 1)

    @override_settings(
        DEBUG=True,
        DEVELOPMENT_VERIFICATION_SEND_COOLDOWN_SECONDS=0,
        DEVELOPMENT_VERIFICATION_MAX_SENDS_PER_HOUR=1000,
    )
    def test_development_profile_allows_repeated_code_issue_without_weakening_code_security(self):
        challenges = [
            issue_challenge(self.user, VerificationPurpose.ACCOUNT) for _ in range(5)
        ]
        self.assertEqual(len(challenges), 5)
        self.assertEqual(CODE_LIFETIME_SECONDS, 600)
        self.assertEqual(challenges[-1].failed_attempts, 0)

    def test_account_send_limit_is_three_per_hour(self):
        issue_challenge(self.user, VerificationPurpose.ACCOUNT)
        for challenge in VerificationChallenge.objects.filter(user=self.user):
            VerificationChallenge.objects.filter(pk=challenge.pk).update(
                created_at=timezone.now() - timedelta(seconds=61)
            )
        issue_challenge(self.user, VerificationPurpose.ACCOUNT)
        for challenge in VerificationChallenge.objects.filter(user=self.user):
            VerificationChallenge.objects.filter(pk=challenge.pk).update(
                created_at=timezone.now() - timedelta(seconds=61)
            )
        issue_challenge(self.user, VerificationPurpose.ACCOUNT)
        for challenge in VerificationChallenge.objects.filter(user=self.user):
            VerificationChallenge.objects.filter(pk=challenge.pk).update(
                created_at=timezone.now() - timedelta(seconds=61)
            )

        with self.assertRaises(VerificationRateLimited):
            issue_challenge(self.user, VerificationPurpose.ACCOUNT)
        self.assertEqual(len(mock_verification_provider.messages), 3)

    @override_settings(ALLOW_MOCK_VERIFICATION=False)
    def test_provider_fails_closed_without_authorized_adapter(self):
        with self.assertRaises(VerificationUnavailable):
            issue_challenge(self.user, VerificationPurpose.ACCOUNT)
        self.assertFalse(VerificationChallenge.objects.exists())

    @override_settings(
        ALLOW_MOCK_VERIFICATION=False,
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        DEFAULT_FROM_EMAIL="BloodConnect Verification <verify@example.test>",
    )
    def test_email_provider_sends_exactly_one_code_with_django_test_backend(self):
        challenge = issue_challenge(self.user, VerificationPurpose.ACCOUNT)
        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]
        self.assertEqual(sent.to, [self.user.email])
        self.assertEqual(sent.from_email, "BloodConnect Verification <verify@example.test>")
        self.assertEqual(sent.subject, "Your BloodConnect BD verification code")
        code = sent.body.split("code is ", 1)[1].split(".", 1)[0]
        self.assertEqual(len(code), 6)
        self.assertTrue(code.isdigit())
        challenge.refresh_from_db()
        self.assertNotEqual(challenge.code_digest, code)
        self.assertTrue(consume_challenge(self.user, VerificationPurpose.ACCOUNT, code))
        self.assertEqual(len(mail.outbox), 1)

    @override_settings(
        ALLOW_MOCK_VERIFICATION=False,
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        DEFAULT_FROM_EMAIL="verify@example.test",
    )
    def test_email_delivery_failure_invalidates_code_and_keeps_account_pending(self):
        from unittest.mock import patch

        with patch(
            "apps.accounts.verification.send_mail",
            side_effect=OSError("synthetic SMTP failure"),
        ):
            with self.assertRaises(VerificationDeliveryError):
                issue_challenge(self.user, VerificationPurpose.ACCOUNT)

        challenge = VerificationChallenge.objects.get(user=self.user)
        self.assertIsNotNone(challenge.consumed_at)
        self.user.refresh_from_db()
        self.assertEqual(self.user.account_status, AccountStatus.PENDING)
        self.assertIsNone(self.user.email_verified_at)

    def test_cleanup_command_purges_only_challenges_over_24_hours_expired(self):
        expired = issue_challenge(self.user, VerificationPurpose.ACCOUNT)
        recent = VerificationChallenge.objects.create(
            user=self.user,
            purpose=VerificationPurpose.ACCOUNT,
            channel=VerificationChannel.EMAIL,
            code_digest="0" * 64,
            expires_at=timezone.now() + timedelta(minutes=10),
        )
        now = timezone.now()
        VerificationChallenge.objects.filter(pk=expired.pk).update(
            created_at=now - timedelta(hours=26),
            expires_at=now - timedelta(hours=25),
        )
        VerificationChallenge.objects.filter(pk=recent.pk).update(
            created_at=now - timedelta(hours=2),
            expires_at=now - timedelta(hours=1),
        )

        output = StringIO()
        call_command("purge_verification_challenges", stdout=output)

        self.assertFalse(VerificationChallenge.objects.filter(pk=expired.pk).exists())
        self.assertTrue(VerificationChallenge.objects.filter(pk=recent.pk).exists())
        self.assertIn("Purged 1 expired", output.getvalue())

    def test_phone_password_reset_requires_verified_active_phone(self):
        with self.assertRaises(VerificationUnavailable):
            issue_challenge(self.user, VerificationPurpose.PASSWORD_RESET)

        user = User.objects.create_user(
            phone_e164="+8801700000000",
            display_name="Phone Example",
            password=PASSWORD,
        )
        user.account_status = AccountStatus.ACTIVE
        user.phone_verified_at = timezone.now()
        user.save(update_fields=["account_status", "phone_verified_at", "updated_at"])
        challenge = issue_challenge(user, VerificationPurpose.PASSWORD_RESET)
        message = mock_verification_provider.messages[-1]

        self.assertEqual(challenge.purpose, VerificationPurpose.PASSWORD_RESET)
        self.assertTrue(consume_challenge(user, VerificationPurpose.PASSWORD_RESET, message.code))
        user.refresh_from_db()
        self.assertEqual(user.account_status, AccountStatus.ACTIVE)
        self.assertEqual(user.password, User.objects.get(pk=user.pk).password)


class VerificationWebFlowTests(TestCase):
    def setUp(self):
        cache.clear()
        mock_verification_provider.clear()

    def test_account_verify_view_is_generic_and_activates_with_code(self):
        pending = User.objects.create_user(
            email="pending@example.test",
            display_name="Pending Example",
            password=PASSWORD,
        )
        request_url = reverse("accounts:verification_start")
        submitted = self.client.post(request_url, {"identifier": pending.email})
        verify_url = reverse("accounts:verify")
        self.assertRedirects(submitted, verify_url, fetch_redirect_response=False)
        self.assertEqual(self.client.session["verification_identifier"], pending.email)
        challenge_count = VerificationChallenge.objects.filter(user=pending).count()
        response = self.client.get(verify_url)
        self.assertContains(response, "If an eligible pending account matches")
        code = mock_verification_provider.messages[-1].code
        self.assertNotContains(response, code)
        self.assertContains(response, pending.email)
        self.assertContains(response, 'name="code"')
        self.assertEqual(VerificationChallenge.objects.filter(user=pending).count(), challenge_count)
        self.assertEqual(len(mock_verification_provider.messages), 1)
        fallback_response = self.client.get(request_url)
        self.assertContains(fallback_response, "Enter verification code")
        invalid_code = self.client.post(
            reverse("accounts:verify"),
            {"identifier": pending.email, "code": "abc"},
        )
        self.assertContains(invalid_code, "Enter the six-digit code.")
        self.assertContains(invalid_code, pending.email)

        unknown_post = self.client.post(
            request_url, {"identifier": "unknown@example.test"}
        )
        self.assertRedirects(unknown_post, verify_url, fetch_redirect_response=False)
        unknown_response = self.client.get(verify_url)
        self.assertContains(unknown_response, "If an eligible pending account matches")

        verified = self.client.post(
            reverse("accounts:verify"),
            {"identifier": pending.email, "code": code},
            follow=True,
        )
        self.assertEqual(verified.status_code, 200)
        self.assertContains(verified, "Your email has been verified. You can now sign in.")
        pending.refresh_from_db()
        self.assertEqual(pending.account_status, AccountStatus.ACTIVE)

    @override_settings(
        ALLOW_MOCK_VERIFICATION=False,
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        DEFAULT_FROM_EMAIL="verify@example.test",
    )
    def test_email_backend_web_flow_sends_once_and_activates_local_email(self):
        pending = User.objects.create_user(
            email="smtp-flow@example.test",
            display_name="SMTP Flow",
            password=PASSWORD,
        )
        submitted = self.client.post(
            reverse("accounts:verification_start"),
            {"identifier": pending.email},
        )
        self.assertRedirects(
            submitted,
            reverse("accounts:verify"),
            fetch_redirect_response=False,
        )
        response = self.client.get(reverse("accounts:verify"))
        self.assertEqual(len(mail.outbox), 1)
        code = mail.outbox[0].body.split("code is ", 1)[1].split(".", 1)[0]
        self.assertNotContains(response, code)

        verified = self.client.post(
            reverse("accounts:verify"),
            {"identifier": pending.email, "code": code},
        )
        self.assertRedirects(verified, reverse("accounts:login"))
        pending.refresh_from_db()
        self.assertEqual(pending.account_status, AccountStatus.ACTIVE)
        self.assertIsNotNone(pending.email_verified_at)
        self.assertEqual(len(mail.outbox), 1)

        self.client.post(
            reverse("accounts:verification_start"),
            {"identifier": pending.email},
        )
        self.assertEqual(len(mail.outbox), 1)

    def test_verification_code_is_not_rendered_or_logged(self):
        user = User.objects.create_user(
            email="private@example.test", display_name="Private Example", password=PASSWORD
        )
        start_url = reverse("accounts:verification_start")
        with self.assertLogs("bloodconnect.request", level="INFO") as send_logs:
            submitted = self.client.post(start_url, {"identifier": user.email})
        self.assertRedirects(
            submitted, reverse("accounts:verify"), fetch_redirect_response=False
        )
        response = self.client.get(reverse("accounts:verify"))
        code = mock_verification_provider.messages[-1].code
        self.assertNotContains(response, code)
        self.assertNotIn(code, "\n".join(send_logs.output))

        with self.assertLogs("bloodconnect.request", level="INFO") as verify_logs:
            self.client.post(
                reverse("accounts:verify"), {"identifier": user.email, "code": code}
            )
        self.assertNotIn(code, "\n".join(verify_logs.output))

    @override_settings(
        ALLOW_MOCK_VERIFICATION=False,
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        DEFAULT_FROM_EMAIL="verify@example.test",
    )
    def test_email_delivery_failure_is_safe_and_does_not_reveal_account(self):
        from unittest.mock import patch

        user = User.objects.create_user(
            email="delivery-failure@example.test",
            display_name="Pending Email",
            password=PASSWORD,
        )
        request_url = reverse("accounts:verification_start")
        with patch(
            "apps.accounts.verification.send_mail",
            side_effect=OSError("synthetic SMTP failure"),
        ):
            with self.assertLogs("bloodconnect.verification", level="WARNING") as logs:
                failed_post = self.client.post(request_url, {"identifier": user.email})
        verify_url = reverse("accounts:verify")
        self.assertRedirects(failed_post, verify_url, fetch_redirect_response=False)
        failed = self.client.get(verify_url)
        unknown_post = self.client.post(
            request_url,
            {"identifier": "unknown@example.test"},
        )
        self.assertRedirects(unknown_post, verify_url, fetch_redirect_response=False)
        unknown = self.client.get(verify_url)

        self.assertEqual(failed.status_code, 200)
        self.assertEqual(unknown.status_code, 200)
        self.assertContains(failed, "If an eligible pending account matches")
        self.assertContains(unknown, "If an eligible pending account matches")
        self.assertNotIn("synthetic SMTP failure", "\n".join(logs.output))
        self.assertNotIn("Traceback", "\n".join(logs.output))
        user.refresh_from_db()
        self.assertEqual(user.account_status, AccountStatus.PENDING)
        self.assertIsNone(user.email_verified_at)
        challenge = VerificationChallenge.objects.get(user=user)
        self.assertIsNotNone(challenge.consumed_at)

    def test_resend_rate_limit_and_code_attempt_limit_are_applied(self):
        user = User.objects.create_user(
            email="rate@example.test", display_name="Rate Example", password=PASSWORD
        )
        request_url = reverse("accounts:verification_start")
        for _ in range(5):
            self.client.post(request_url, {"identifier": user.email})
        limited = self.client.post(request_url, {"identifier": user.email})
        self.assertEqual(limited.status_code, 429)

        code = mock_verification_provider.messages[-1].code
        verify_url = reverse("accounts:verify")
        for _ in range(5):
            response = self.client.post(
                verify_url, {"identifier": user.email, "code": "999999"}
            )
            self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertEqual(user.account_status, AccountStatus.PENDING)
        self.assertFalse(consume_challenge(user, VerificationPurpose.ACCOUNT, code))

    def test_phone_password_reset_changes_password_only_after_code(self):
        user = User.objects.create_user(
            phone_e164="+8801700000000", display_name="Phone Example", password=PASSWORD
        )
        user.account_status = AccountStatus.ACTIVE
        user.phone_verified_at = timezone.now()
        user.save(update_fields=["account_status", "phone_verified_at", "updated_at"])

        start_url = reverse("accounts:phone_password_reset")
        response = self.client.post(start_url, {"phone_e164": user.phone_e164})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "If an active account matches")
        code = mock_verification_provider.messages[-1].code

        verified = self.client.post(
            reverse("accounts:phone_password_reset_verify"),
            {"phone_e164": user.phone_e164, "code": code},
        )
        self.assertRedirects(verified, reverse("accounts:phone_password_reset_confirm"))
        new_password = "New-Synthetic-Password!6284"
        changed = self.client.post(
            reverse("accounts:phone_password_reset_confirm"),
            {"new_password1": new_password, "new_password2": new_password},
        )
        self.assertRedirects(changed, reverse("accounts:password_reset_complete"))
        user.refresh_from_db()
        self.assertTrue(user.check_password(new_password))
        self.assertFalse(user.check_password(PASSWORD))
        self.assertNotIn("phone_password_reset_user_id", self.client.session)
