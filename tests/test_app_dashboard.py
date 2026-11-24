from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import AccountStatus, User
from apps.connections.models import ContactRequest, ContactRequestStatus
from apps.donors.models import BloodGroup, DonorProfile
from apps.locations.models import Location, LocationLevel
from apps.notifications.models import Notification, NotificationType
from apps.requests.models import BloodRequest, BloodRequestStatus, RequestUrgency


class AuthenticatedDashboardTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="member@example.test",
            password="A-secure-password-123",
            display_name="Test Member",
        )
        self.user.account_status = AccountStatus.ACTIVE
        self.user.save(update_fields=["account_status"])
        self.client.force_login(self.user)

    def test_authenticated_home_renders_dashboard_and_existing_navigation(self):
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/dashboard.html")
        self.assertContains(response, 'app-shell--redesigned-workspace')
        self.assertContains(response, 'class="app-topbar"')
        self.assertContains(response, 'js/app_shell.js')
        self.assertNotContains(response, 'dashboard-toolbar')
        self.assertContains(response, "Welcome back, Test Member.")
        self.assertContains(response, 'aria-current="page"')
        for route in (
            "donors:search",
            "requests:list",
            "connections:incoming",
            "notifications:list",
            "donors:profile",
            "governance:privacy_settings",
            "accounts:google_link",
            "safety",
        ):
            self.assertContains(response, reverse(route))
        self.assertContains(response, 'method="post" action="/accounts/logout/"')
        self.assertContains(response, "No blood requests yet")
        self.assertContains(response, "Find donors")
        self.assertContains(response, "Settings")
        self.assertNotContains(response, ">Contact requests</a>")

    def test_summary_and_recent_requests_use_only_the_signed_in_user_data(self):
        division = Location.objects.create(
            name_en="Test Division",
            level=LocationLevel.DIVISION,
            source_name="tests",
            source_version="1",
            is_active=False,
        )
        district = Location.objects.create(
            name_en="Test District",
            level=LocationLevel.DISTRICT,
            parent=division,
            source_name="tests",
            source_version="1",
            is_active=False,
        )
        now = timezone.now()
        own_request = BloodRequest.objects.create(
            requester=self.user,
            blood_group=BloodGroup.O_POSITIVE,
            units_requested=1,
            required_at=now + timedelta(days=1),
            division=division,
            district=district,
            urgency=RequestUrgency.NORMAL,
            status=BloodRequestStatus.OPEN,
            expires_at=now + timedelta(days=2),
        )
        Notification.objects.create(
            recipient=self.user,
            notification_type=NotificationType.CONTACT_REQUEST_RECEIVED,
            title="A contact request arrived",
            body="Review the request in your account.",
        )
        other = User.objects.create_user(
            email="other@example.test",
            password="A-secure-password-123",
            display_name="Other Member",
        )
        other_request = BloodRequest.objects.create(
            requester=other,
            blood_group=BloodGroup.A_POSITIVE,
            units_requested=1,
            required_at=now + timedelta(days=1),
            division=division,
            district=district,
            urgency=RequestUrgency.NORMAL,
            status=BloodRequestStatus.OPEN,
            expires_at=now + timedelta(days=2),
        )
        donor_profile = DonorProfile.objects.create(
            user=self.user,
            blood_group=BloodGroup.A_POSITIVE,
            division=division,
            district=district,
        )
        ContactRequest.objects.create(
            recipient=other,
            donor_profile=donor_profile,
            blood_request=other_request,
            status=ContactRequestStatus.PENDING,
            expires_at=now + timedelta(days=2),
        )
        response = self.client.get(reverse("home"))

        self.assertEqual(response.context["open_request_count"], 1)
        self.assertEqual(response.context["pending_contact_request_count"], 1)
        self.assertEqual(response.context["unread_notification_count"], 1)
        self.assertContains(response, 'aria-label="Notifications, 1 unread"')
        self.assertContains(response, '<span class="app-notification-count" aria-hidden="true">1</span>')
        self.assertEqual(len(response.context["recent_requests"]), 1)
        self.assertEqual(response.context["recent_requests"][0].requester_id, self.user.pk)
        self.assertFalse(response.context["has_reviewed_area_filters"])
        self.assertContains(response, "Test District")
        self.assertContains(response, "Area filters are not available yet")

    def test_requests_area_keeps_blood_and_contact_workflows_together(self):
        response = self.client.get(reverse("requests:list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'aria-label="Requests workspace"')
        self.assertContains(response, reverse("connections:incoming"))
        self.assertContains(response, reverse("connections:outgoing"))
        self.assertContains(response, 'aria-current="page" class="is-active"')
