"""Opt-in genuine route screenshots backed only by isolated synthetic test data."""

from datetime import timedelta
import os
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse
from django.utils import timezone
from playwright.sync_api import sync_playwright

from apps.accounts.models import AccountStatus
from apps.donors.models import AvailabilityStatus, BloodGroup, DonorProfile, DonorProfileStatus
from apps.governance.models import ConsentType, record_consent
from apps.locations.models import Location, LocationLevel
from apps.requests.models import RequestUrgency
from apps.requests.services import create_blood_request


@pytest.mark.django_db(transaction=True)
def test_capture_synthetic_screenshots(live_server):
    if os.environ.get("BLOODCONNECT_CAPTURE_SCREENSHOTS") != "1":
        pytest.skip("Set BLOODCONNECT_CAPTURE_SCREENSHOTS=1 to write showcase assets")

    User = get_user_model()
    division = Location.objects.create(name_en="Synthetic Division", level=LocationLevel.DIVISION,
        source_name="Synthetic screenshot fixture", source_version="synthetic-v1")
    district = Location.objects.create(name_en="Synthetic District", level=LocationLevel.DISTRICT,
        parent=division, source_name="Synthetic screenshot fixture", source_version="synthetic-v1")
    donor = User.objects.create_user(email="donor@example.test", password="Synthetic-Donor-947!",
        display_name="Synthetic Donor")
    donor.account_status = AccountStatus.ACTIVE
    donor.email_verified_at = timezone.now()
    donor.save(update_fields=["account_status", "email_verified_at", "updated_at"])
    DonorProfile.objects.create(user=donor, blood_group=BloodGroup.O_POSITIVE, division=division,
        district=district, availability_status=AvailabilityStatus.AVAILABLE, visibility_enabled=True,
        profile_status=DonorProfileStatus.ACTIVE, public_alias="Synthetic Donor")
    record_consent(user=donor, consent_type=ConsentType.DONOR_DISCOVERY,
        policy_version="draft-1", granted=True)

    recipient = User.objects.create_user(email="recipient@example.test", password="Synthetic-Recipient-947!",
        display_name="Synthetic Recipient")
    recipient.account_status = AccountStatus.ACTIVE
    recipient.email_verified_at = timezone.now()
    recipient.save(update_fields=["account_status", "email_verified_at", "updated_at"])
    create_blood_request(user=recipient, publish=True, values={
        "blood_group": BloodGroup.O_POSITIVE, "units_requested": 1,
        "required_at": timezone.now() + timedelta(days=2), "division": division, "district": district,
        "upazila": None, "facility_name": "Synthetic Facility", "facility_address": "Synthetic Address",
        "urgency": RequestUrgency.NORMAL, "description": "Synthetic screenshot request",
        "public_listing_enabled": True, "expires_at": timezone.now() + timedelta(days=3),
    })
    moderator = User.objects.create_user(email="moderator@example.test", password="Synthetic-Mod-947!",
        display_name="Synthetic Moderator")
    moderator.account_status = AccountStatus.ACTIVE
    moderator.save(update_fields=["account_status", "updated_at"])
    moderator.groups.add(Group.objects.get_or_create(name="MODERATOR")[0])
    admin = User.objects.create_superuser(email="admin@example.test", password="Synthetic-Admin-947!",
        display_name="Synthetic Admin")
    screenshots = Path("docs/screenshots")
    screenshots.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1000}, device_scale_factor=1)
        def capture(name, path):
            page.goto(f"{live_server.url}{path}", wait_until="networkidle")
            page.screenshot(path=str(screenshots / name), full_page=True)

        capture("homepage.png", "/")
        capture("registration.png", reverse("accounts:register"))
        capture("login.png", reverse("accounts:login"))
        page.goto(f"{live_server.url}{reverse('accounts:login')}")
        page.locator("input[name='username']").fill(donor.email)
        page.locator("input[name='password']").fill("Synthetic-Donor-947!")
        page.get_by_role("button", name="Sign in").click()
        capture("donor-discovery.png", reverse("donors:search"))
        capture("donor-profile.png", reverse("donors:profile"))
        page.goto(f"{live_server.url}{reverse('accounts:login')}")
        page.locator("input[name='username']").fill(recipient.email)
        page.locator("input[name='password']").fill("Synthetic-Recipient-947!")
        page.get_by_role("button", name="Sign in").click()
        capture("blood-request.png", reverse("requests:create"))
        page.goto(f"{live_server.url}{reverse('accounts:login')}")
        page.locator("input[name='username']").fill(moderator.email)
        page.locator("input[name='password']").fill("Synthetic-Mod-947!")
        page.get_by_role("button", name="Sign in").click()
        capture("moderator-dashboard.png", reverse("analytics:operational_dashboard"))
        page.goto(f"{live_server.url}/admin/")
        page.locator("input[name='username']").fill(admin.email)
        page.locator("input[name='password']").fill("Synthetic-Admin-947!")
        page.get_by_role("button", name="Log in").click()
        page.screenshot(path=str(screenshots / "django-admin.png"), full_page=True)
        browser.close()
