"""Verification challenge persistence, expiry, abuse and web-flow tests."""

from datetime import timedelta
from io import StringIO

from django.contrib.auth import get_user_model
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
        response = self.client.post(request_url, {"identifier": pending.email})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "If the account is pending")
        code = mock_verification_provider.messages[-1].code
        self.assertNotContains(response, code)

        unknown_response = self.client.post(
            request_url, {"identifier": "unknown@example.test"}
        )
        self.assertContains(unknown_response, "If the account is pending")

        verified = self.client.post(
            reverse("accounts:verify"), {"identifier": pending.email, "code": code}
        )
        self.assertRedirects(verified, reverse("accounts:login"))
        pending.refresh_from_db()
        self.assertEqual(pending.account_status, AccountStatus.ACTIVE)

    def test_verification_code_is_not_rendered_or_logged(self):
        user = User.objects.create_user(
            email="private@example.test", display_name="Private Example", password=PASSWORD
        )
        start_url = reverse("accounts:verification_start")
        with self.assertLogs("bloodconnect.request", level="INFO") as send_logs:
            response = self.client.post(start_url, {"identifier": user.email})
        code = mock_verification_provider.messages[-1].code
        self.assertNotContains(response, code)
        self.assertNotIn(code, "\n".join(send_logs.output))

        with self.assertLogs("bloodconnect.request", level="INFO") as verify_logs:
            self.client.post(
                reverse("accounts:verify"), {"identifier": user.email, "code": code}
            )
        self.assertNotIn(code, "\n".join(verify_logs.output))

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
