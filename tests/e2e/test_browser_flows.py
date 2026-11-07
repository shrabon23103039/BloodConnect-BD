"""Browser-level coverage for the consent-gated contact workflow."""

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from playwright.sync_api import sync_playwright

from apps.accounts.models import AccountStatus
from apps.accounts.verification import mock_verification_provider
from apps.donors.models import (
    AvailabilityStatus,
    BloodGroup,
    DonorProfile,
    DonorProfileStatus,
    PreferredContactMethod,
)
from apps.governance.models import ConsentType, record_consent
from apps.locations.models import Location, LocationLevel
from apps.requests.models import RequestUrgency
from apps.requests.services import create_blood_request


User = get_user_model()
RECIPIENT_EMAIL = "browser-recipient@example.test"
RECIPIENT_PASSWORD = "Synthetic-Unique-Password!947"
DONOR_EMAIL = "browser-donor@example.test"
DONOR_PASSWORD = "Synthetic-Donor-Password!947"


@pytest.mark.django_db(transaction=True)
def test_registration_search_contact_request_accept_flow(live_server, settings):
    settings.ALLOW_MOCK_VERIFICATION = True
    mock_verification_provider.clear()
    division = Location.objects.create(
        name_en="Browser synthetic division",
        level=LocationLevel.DIVISION,
        source_name="Synthetic browser fixture",
        source_version="synthetic-v1",
    )
    district = Location.objects.create(
        name_en="Browser synthetic district",
        level=LocationLevel.DISTRICT,
        parent=division,
        source_name="Synthetic browser fixture",
        source_version="synthetic-v1",
    )

    donor_user = User.objects.create_user(
        email=DONOR_EMAIL,
        password=DONOR_PASSWORD,
        display_name="Synthetic browser donor",
    )
    donor_user.account_status = AccountStatus.ACTIVE
    donor_user.email_verified_at = timezone.now()
    donor_user.save(update_fields=["account_status", "email_verified_at", "updated_at"])
    donor = DonorProfile.objects.create(
        user=donor_user,
        blood_group=BloodGroup.O_POSITIVE,
        division=division,
        district=district,
        availability_status=AvailabilityStatus.AVAILABLE,
        visibility_enabled=True,
        profile_status=DonorProfileStatus.ACTIVE,
        public_alias="Synthetic browser alias",
        preferred_contact_method=PreferredContactMethod.EMAIL_AFTER_ACCEPT,
        share_email_after_accept=True,
    )
    for consent_type in (
        ConsentType.DONOR_DISCOVERY,
        ConsentType.EMAIL_SHARE_AFTER_ACCEPT,
    ):
        record_consent(
            user=donor_user,
            consent_type=consent_type,
            policy_version="draft-1",
            granted=True,
        )

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        recipient_context = browser.new_context()
        recipient_page = recipient_context.new_page()
        recipient_page.set_default_timeout(8_000)

        recipient_page.goto(f"{live_server.url}{reverse('accounts:register')}")
        recipient_page.get_by_label("Display name").fill("Synthetic browser recipient")
        recipient_page.get_by_label("Email").fill(RECIPIENT_EMAIL)
        recipient_page.locator("input[name='password1']").fill(RECIPIENT_PASSWORD)
        recipient_page.locator("input[name='password2']").fill(RECIPIENT_PASSWORD)
        recipient_page.get_by_label("I accept the Terms of Service.").check()
        recipient_page.get_by_label("I acknowledge the Privacy Notice.").check()
        recipient_page.get_by_role("button", name="Create account").click()
        assert recipient_page.get_by_role(
            "heading", name="Registration request received"
        ).is_visible()
        recipient_page.get_by_role("link", name="Continue to verification").click()
        recipient_page.get_by_label("Email or phone").fill(RECIPIENT_EMAIL)
        recipient_page.get_by_role("button", name="Send or resend code").click()
        code = mock_verification_provider.messages[-1].code
        recipient_page.goto(f"{live_server.url}{reverse('accounts:verify')}")
        recipient_page.get_by_label("Email or phone").fill(RECIPIENT_EMAIL)
        recipient_page.locator("input[name='code']").fill(code)
        recipient_page.get_by_role("button", name="Verify account").click()
        assert recipient_page.url.endswith(reverse("accounts:login"))

        recipient_page.locator("input[name='username']").fill(RECIPIENT_EMAIL)
        recipient_page.locator("input[name='password']").fill(RECIPIENT_PASSWORD)
        recipient_page.get_by_role("button", name="Sign in").click()
        assert recipient_page.get_by_role("button", name="Sign out").is_visible()

        recipient_state = recipient_context.storage_state()
        recipient_context.close()
        browser.close()

    recipient = User.objects.get(email=RECIPIENT_EMAIL)
    blood_request = create_blood_request(
        user=recipient,
        values={
            "blood_group": BloodGroup.O_POSITIVE,
            "units_requested": 1,
            "required_at": timezone.now() + timedelta(days=2),
            "division": division,
            "district": district,
            "upazila": None,
            "facility_name": "Synthetic browser facility",
            "facility_address": "Synthetic browser address",
            "urgency": RequestUrgency.NORMAL,
            "description": "Synthetic browser request",
            "public_listing_enabled": True,
            "expires_at": timezone.now() + timedelta(days=3),
        },
        publish=True,
    )

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        recipient_context = browser.new_context(storage_state=recipient_state)
        recipient_page = recipient_context.new_page()
        recipient_page.set_default_timeout(8_000)
        recipient_page.goto(f"{live_server.url}{reverse('donors:search')}")
        assert recipient_page.get_by_role("heading", name="Synthetic browser alias").is_visible()
        recipient_page.get_by_role("link", name="Request contact").click()
        recipient_page.locator("select[name='donor_profile']").select_option(str(donor.pk))
        recipient_page.locator("select[name='blood_request']").select_option(str(blood_request.pk))
        recipient_page.get_by_label("Message").fill("Synthetic browser contact request")
        recipient_page.get_by_role("button", name="Send contact request").click()
        recipient_detail_text = recipient_page.locator("body").inner_text()
        assert "Status: Pending" in recipient_detail_text
        assert DONOR_EMAIL not in recipient_detail_text

        contact_request_url = recipient_page.url
        assert DONOR_EMAIL not in recipient_page.locator("body").inner_text()
        recipient_context.close()
        browser.close()

    contact_request = recipient.outgoing_contact_requests.get()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        donor_context = browser.new_context()
        donor_page = donor_context.new_page()
        donor_page.set_default_timeout(8_000)
        donor_page.goto(f"{live_server.url}{reverse('accounts:login')}")
        donor_page.locator("input[name='username']").fill(DONOR_EMAIL)
        donor_page.locator("input[name='password']").fill(DONOR_PASSWORD)
        donor_page.get_by_role("button", name="Sign in").click()
        donor_page.goto(f"{live_server.url}{reverse('connections:incoming')}")
        donor_page.get_by_role("link", name="O+ request · Pending").click()
        donor_page.get_by_role("button", name="Accept").click()
        assert "Status: Accepted" in donor_page.locator("body").inner_text()
        donor_context.close()
        browser.close()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        recipient_context = browser.new_context(storage_state=recipient_state)
        recipient_page = recipient_context.new_page()
        recipient_page.set_default_timeout(8_000)
        recipient_page.goto(contact_request_url)
        recipient_page.get_by_role("link", name="View accepted connection").click()
        assert recipient_page.get_by_text(DONOR_EMAIL, exact=True).is_visible()
        recipient_context.close()
        browser.close()
