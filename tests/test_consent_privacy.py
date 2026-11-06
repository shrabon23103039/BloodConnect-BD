from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from apps.accounts.models import AccountStatus
from apps.governance.models import (
    ConsentRecord,
    ConsentSource,
    ConsentType,
    current_consent_state,
    record_consent,
)

User = get_user_model()


class ConsentRegistrationTests(TestCase):
    @override_settings(ALLOW_MOCK_VERIFICATION=True)
    @override_settings(TERMS_POLICY_VERSION="terms-v9", PRIVACY_POLICY_VERSION="privacy-v4")
    def test_registration_records_separate_versioned_terms_and_privacy_acknowledgements(self):
        response = self.client.post(
            reverse("accounts:register"),
            {
                "display_name": "Consent Example",
                "email": "consent@example.test",
                "phone_e164": "",
                "password1": "Synthetic-Unique-Password!947",
                "password2": "Synthetic-Unique-Password!947",
                "accept_terms": "on",
                "accept_privacy": "on",
            },
        )

        self.assertRedirects(response, reverse("accounts:registration_submitted"))
        records = {record.consent_type: record for record in ConsentRecord.objects.all()}
        self.assertEqual(records[ConsentType.TERMS_ACCEPTED].policy_version, "terms-v9")
        self.assertEqual(records[ConsentType.PRIVACY_ACKNOWLEDGED].policy_version, "privacy-v4")
        self.assertTrue(all(record.granted for record in records.values()))
        self.assertTrue(all(record.source == ConsentSource.WEB for record in records.values()))


class PrivacySettingsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="privacy@example.test",
            password="Synthetic-Unique-Password!947",
            display_name="Privacy Example",
        )
        self.user.account_status = AccountStatus.ACTIVE
        self.user.email_verified_at = timezone.now()
        self.user.save(update_fields=["account_status", "email_verified_at", "updated_at"])
        self.url = reverse("governance:privacy_settings")

    def post_settings(self, **values):
        return self.client.post(self.url, values)

    def test_anonymous_and_inactive_accounts_cannot_change_privacy_settings(self):
        response = self.client.get(self.url)
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={self.url}")

        self.client.force_login(self.user)
        self.user.account_status = AccountStatus.SUSPENDED
        self.user.save(update_fields=["account_status", "updated_at"])
        response = self.client.get(self.url)
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={self.url}")

    @override_settings(PRIVACY_POLICY_VERSION="privacy-v2")
    def test_changes_append_versioned_events_and_repeat_values_are_idempotent(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(self.url).status_code, 200)

        self.post_settings(donor_discovery="on", email_share_after_accept="on")
        records = list(ConsentRecord.objects.filter(user=self.user))
        self.assertEqual(len(records), 4)
        self.assertTrue(all(record.policy_version == "privacy-v2" for record in records))
        self.assertTrue(all(record.source == ConsentSource.WEB for record in records))
        self.assertTrue(current_consent_state(self.user)[ConsentType.DONOR_DISCOVERY])
        self.assertTrue(current_consent_state(self.user)[ConsentType.EMAIL_SHARE_AFTER_ACCEPT])

        self.post_settings(donor_discovery="on", email_share_after_accept="on")
        self.assertEqual(ConsentRecord.objects.filter(user=self.user).count(), 4)

        self.post_settings()
        history = ConsentRecord.objects.filter(
            user=self.user,
            consent_type=ConsentType.DONOR_DISCOVERY,
        ).order_by("captured_at")
        self.assertEqual(history.count(), 2)
        self.assertTrue(history.first().granted)
        self.assertFalse(history.last().granted)
        self.assertIsNotNone(history.last().withdrawn_at)
        self.assertTrue(current_consent_state(self.user)[ConsentType.DONOR_DISCOVERY] is False)

    def test_consent_events_cannot_be_edited_or_deleted(self):
        self.client.force_login(self.user)
        self.post_settings(donor_discovery="on")
        record = ConsentRecord.objects.filter(user=self.user).first()

        record.policy_version = "changed"
        with self.assertRaises(ValueError):
            record.save()
        with self.assertRaises(ValueError):
            record.delete()

        self.assertFalse(ConsentRecord.objects.filter(policy_version="changed").exists())

    def test_consent_events_keep_order_when_recorded_with_same_clock_time(self):
        fixed_time = timezone.now()
        with patch("apps.governance.models.timezone.now", return_value=fixed_time):
            ConsentRecord.objects.create(
                user=self.user,
                consent_type=ConsentType.DONOR_DISCOVERY,
                policy_version="privacy-v1",
                granted=True,
                captured_at=fixed_time,
                source=ConsentSource.WEB,
            )
            record_consent(
                user=self.user,
                consent_type=ConsentType.DONOR_DISCOVERY,
                policy_version="privacy-v1",
                granted=False,
            )

        history = ConsentRecord.objects.filter(
            user=self.user,
            consent_type=ConsentType.DONOR_DISCOVERY,
        ).order_by("captured_at")
        self.assertLess(history.first().captured_at, history.last().captured_at)
        self.assertFalse(current_consent_state(self.user)[ConsentType.DONOR_DISCOVERY])
