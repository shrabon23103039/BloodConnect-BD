from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import AccountStatus
from apps.analytics.services import suppress_small_count


User = get_user_model()


class OperationalAnalyticsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="metrics-user@example.test",
            password="Synthetic-Unique-Password!947",
            display_name="Synthetic metrics user",
        )
        self.user.account_status = AccountStatus.ACTIVE
        self.user.save(update_fields=["account_status", "updated_at"])

    def test_small_counts_are_suppressed(self):
        self.assertIsNone(suppress_small_count(0))
        self.assertIsNone(suppress_small_count(4))
        self.assertEqual(suppress_small_count(5), 5)

    def test_dashboard_is_moderator_only_and_suppresses_empty_cells(self):
        url = reverse("analytics:operational_dashboard")
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(url).status_code, 403)
        group = Group.objects.create(name="MODERATOR")
        self.user.groups.add(group)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Counts below five are suppressed")
        self.assertEqual(response.context["metrics"], {
            "discoverable_donors": None,
            "open_blood_requests": None,
            "pending_contact_requests": None,
            "open_reports": None,
        })
        self.assertNotContains(response, self.user.email)
