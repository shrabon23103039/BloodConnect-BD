"""Browser-level coverage for the consent-gated contact workflow."""

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from playwright.sync_api import sync_playwright

from apps.accounts.models import AccountStatus
from apps.accounts.verification import mock_verification_provider
from apps.connections.models import ContactRequestStatus
from apps.connections.services import create_contact_request, transition_contact_request
from apps.donors.models import (
    AvailabilityStatus,
    BloodGroup,
    DonorProfile,
    DonorProfileStatus,
    PreferredContactMethod,
)
from apps.governance.models import ConsentType, record_consent
from apps.locations.models import Location, LocationLevel
from apps.requests.models import BloodRequestStatus, RequestUrgency
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
        recipient_page.get_by_label("Email address").fill(RECIPIENT_EMAIL)
        recipient_page.locator("input[name='password1']").fill(RECIPIENT_PASSWORD)
        recipient_page.get_by_role("button", name="Show password").click()
        assert recipient_page.locator("input[name='password1']").get_attribute("type") == "text"
        recipient_page.get_by_role("button", name="Hide password").click()
        recipient_page.locator("input[name='password2']").fill(RECIPIENT_PASSWORD)
        recipient_page.get_by_label("I accept the Terms of Service.").check()
        recipient_page.get_by_label("I acknowledge the Privacy Notice.").check()
        recipient_page.get_by_role("button", name="Create account").click()
        assert recipient_page.get_by_role(
            "heading", name="Account created — verification required"
        ).is_visible()
        recipient_page.get_by_role("link", name="Continue to verification").click()
        recipient_page.get_by_label("Email or phone").fill(RECIPIENT_EMAIL)
        recipient_page.get_by_role("button", name="Send or resend code").click()
        assert recipient_page.url.endswith(reverse("accounts:verify"))
        code = mock_verification_provider.messages[-1].code
        assert (
            recipient_page.locator("input[name='identifier']").input_value()
            == RECIPIENT_EMAIL
        )
        assert len(mock_verification_provider.messages) == 1
        recipient_page.locator("input[name='code']").fill(code)
        recipient_page.get_by_role("button", name="Verify account").click()
        assert recipient_page.url.endswith(reverse("accounts:login"))
        assert recipient_page.get_by_text(
            "Your email has been verified. You can now sign in."
        ).is_visible()

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


@pytest.mark.django_db(transaction=True)
def test_request_workspace_is_responsive_and_filters_real_requests(live_server):
    user = User.objects.create_user(
        email="request-workspace@example.test",
        password="Synthetic-Requests-Password!947",
        display_name="Synthetic requests user",
    )
    user.account_status = AccountStatus.ACTIVE
    user.email_verified_at = timezone.now()
    user.save(update_fields=["account_status", "email_verified_at", "updated_at"])
    division = Location.objects.create(
        name_en="Synthetic request division",
        level=LocationLevel.DIVISION,
        source_name="Synthetic browser fixture",
        source_version="synthetic-v1",
    )
    district = Location.objects.create(
        name_en="Synthetic request district",
        level=LocationLevel.DISTRICT,
        parent=division,
        source_name="Synthetic browser fixture",
        source_version="synthetic-v1",
    )
    peer = User.objects.create_user(
        email="request-workspace-peer@example.test",
        password="Synthetic-Peer-Password!947",
        display_name="Synthetic peer",
    )
    peer.account_status = AccountStatus.ACTIVE
    peer.email_verified_at = timezone.now()
    peer.save(update_fields=["account_status", "email_verified_at", "updated_at"])

    user_donor = DonorProfile.objects.create(
        user=user,
        blood_group=BloodGroup.A_POSITIVE,
        division=division,
        district=district,
        availability_status=AvailabilityStatus.AVAILABLE,
        visibility_enabled=True,
        profile_status=DonorProfileStatus.ACTIVE,
        public_alias="Synthetic workspace donor",
        preferred_contact_method=PreferredContactMethod.IN_APP,
    )
    peer_donor = DonorProfile.objects.create(
        user=peer,
        blood_group=BloodGroup.A_POSITIVE,
        division=division,
        district=district,
        availability_status=AvailabilityStatus.AVAILABLE,
        visibility_enabled=True,
        profile_status=DonorProfileStatus.ACTIVE,
        public_alias="Synthetic workspace peer",
        preferred_contact_method=PreferredContactMethod.IN_APP,
    )
    for account in (user, peer):
        record_consent(
            user=account,
            consent_type=ConsentType.DONOR_DISCOVERY,
            policy_version="draft-1",
            granted=True,
        )

    values = {
        "blood_group": "A+",
        "units_requested": 1,
        "required_at": timezone.now() + timedelta(days=2),
        "urgency": RequestUrgency.NORMAL,
        "division": division,
        "district": district,
    }
    create_blood_request(user=user, values=values)
    user_requests = [
        create_blood_request(user=user, values=values, publish=True)
        for _ in range(2)
    ]
    peer_requests = [
        create_blood_request(user=peer, values=values, publish=True)
        for _ in range(2)
    ]
    outgoing_requests = [
        create_contact_request(
            recipient=user,
            donor_profile_id=peer_donor.pk,
            blood_request_id=blood_request.pk,
        )
        for blood_request in user_requests
    ]
    incoming_requests = [
        create_contact_request(
            recipient=peer,
            donor_profile_id=user_donor.pk,
            blood_request_id=blood_request.pk,
        )
        for blood_request in peer_requests
    ]
    transition_contact_request(
        user=peer,
        contact_request_id=outgoing_requests[1].pk,
        target_status=ContactRequestStatus.DECLINED,
    )
    transition_contact_request(
        user=user,
        contact_request_id=incoming_requests[1].pk,
        target_status=ContactRequestStatus.DECLINED,
    )

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.set_default_timeout(8_000)
        page.goto(f"{live_server.url}{reverse('accounts:login')}")
        page.locator("input[name='username']").fill(user.email)
        page.locator("input[name='password']").fill("Synthetic-Requests-Password!947")
        page.get_by_role("button", name="Sign in").click()
        page.goto(f"{live_server.url}{reverse('requests:list')}")
        page.set_viewport_size({"width": 1714, "height": 1000})
        page.goto(f"{live_server.url}{reverse('donors:search')}")
        finder_metrics = page.locator(".donor-search__container").evaluate(
            """(element) => {
              const main = document.querySelector(".app-main");
              const mainRect = main.getBoundingClientRect();
              const style = getComputedStyle(main);
              return {
                mainWidth: mainRect.width,
                paddingLeft: parseFloat(style.paddingLeft),
                paddingRight: parseFloat(style.paddingRight),
                contentRight: mainRect.right - parseFloat(style.paddingRight),
              };
            }"""
        )
        page.goto(f"{live_server.url}{reverse('requests:list')}")
        request_metrics = page.locator(".request-workspace-page").evaluate(
            """(element) => {
              const rect = element.getBoundingClientRect();
              const main = document.querySelector(".app-main");
              const mainRect = main.getBoundingClientRect();
              const style = getComputedStyle(main);
              return {
                width: rect.width,
                mainWidth: mainRect.width,
                paddingLeft: parseFloat(style.paddingLeft),
                paddingRight: parseFloat(style.paddingRight),
                contentRight: mainRect.right - parseFloat(style.paddingRight),
              };
            }"""
        )
        request_width = request_metrics["width"]
        request_available_width = (
            request_metrics["mainWidth"]
            - request_metrics["paddingLeft"]
            - request_metrics["paddingRight"]
        )
        assert abs(request_width - request_available_width) <= 1, (
            f"Requests content width {request_width}px does not fill its "
            f"{request_available_width}px available width at 1714px. "
            f"Requests metrics: {request_metrics}; Find Donors metrics: {finder_metrics}"
        )
        assert request_metrics["paddingLeft"] == finder_metrics["paddingLeft"]
        assert request_metrics["paddingRight"] == finder_metrics["paddingRight"]
        assert abs(
            request_metrics["contentRight"] - finder_metrics["contentRight"]
        ) <= 1

        def assert_no_horizontal_overflow():
            for width in (
                320, 375, 390, 414, 480, 768, 1024, 1280, 1366, 1440, 1714, 1920
            ):
                page.set_viewport_size({"width": width, "height": 1000})
                dimensions = page.evaluate(
                    "() => ({viewport: document.documentElement.clientWidth, "
                    "page: document.documentElement.scrollWidth})"
                )
                assert dimensions["page"] <= dimensions["viewport"], (
                    f"Horizontal overflow at {width}px: {dimensions}"
                )

        assert page.get_by_role("heading", name="Blood requests", exact=True).is_visible()
        assert page.locator('link[href*="css/requests.css"]').count() == 1
        assert "linear-gradient" in page.locator(".request-hero").evaluate(
            "(element) => getComputedStyle(element).backgroundImage"
        )
        assert page.locator("[data-summary-count='my-requests']").inner_text() == "3"
        assert page.locator("[data-summary-count='incoming']").inner_text() == "2"
        assert page.locator("[data-summary-count='outgoing']").inner_text() == "2"
        assert page.locator("[data-request-row]").count() == 3
        page.locator("[data-request-status-filter]").select_option(
            value=BloodRequestStatus.OPEN.label.lower()
        )
        assert page.locator("[data-request-visible-count]").inner_text() == "2"
        assert page.locator("[data-request-row]:visible").count() == 2
        page.locator("[data-request-status-filter]").select_option(value="all")

        view_link = page.get_by_role("link", name="View", exact=True).first
        view_url = view_link.get_attribute("href")
        response = page.goto(f"{live_server.url}{view_url}")
        assert response is not None and response.status == 200
        page.goto(f"{live_server.url}{reverse('requests:list')}")
        manage_link = page.get_by_role("link", name="Manage", exact=True).first
        manage_url = manage_link.get_attribute("href")
        response = page.goto(f"{live_server.url}{manage_url}")
        assert response is not None and response.status == 200
        assert page.get_by_role("heading", name="Edit blood request").is_visible()

        page.goto(f"{live_server.url}{reverse('requests:list')}")
        create_link = page.get_by_role("link", name="Create request", exact=True)
        create_url = create_link.get_attribute("href")
        response = page.goto(f"{live_server.url}{create_url}")
        assert response is not None and response.status == 200
        assert page.locator(".request-create-form").is_visible()
        create_metrics = page.locator(".request-create-page").evaluate(
            """(element) => {
              const rect = element.getBoundingClientRect();
              const main = document.querySelector(".app-main");
              const mainRect = main.getBoundingClientRect();
              const style = getComputedStyle(main);
              return {
                width: rect.width,
                mainWidth: mainRect.width,
                paddingLeft: parseFloat(style.paddingLeft),
                paddingRight: parseFloat(style.paddingRight),
              };
            }"""
        )
        create_available_width = (
            create_metrics["mainWidth"]
            - create_metrics["paddingLeft"]
            - create_metrics["paddingRight"]
        )
        assert abs(create_metrics["width"] - create_available_width) <= 1, (
            f"Create content width {create_metrics['width']}px does not fill its "
            f"{create_available_width}px available width at 1714px"
        )
        assert page.get_by_role("link", name="Cancel").get_attribute("href") == reverse(
            "requests:list"
        )

        page.goto(f"{live_server.url}{reverse('requests:list')}")
        assert_no_horizontal_overflow()

        page.locator(
            f".request-workspace-tabs__links a[href='{reverse('connections:incoming')}']"
        ).click()
        assert page.get_by_role("heading", name="Incoming requests", exact=True).is_visible()
        assert page.locator("[data-summary-count='my-requests']").inner_text() == "3"
        assert page.locator("[data-summary-count='incoming']").inner_text() == "2"
        assert page.locator("[data-summary-count='outgoing']").inner_text() == "2"
        assert page.locator("[data-request-row]").count() == 2
        page.locator("[data-request-status-filter]").select_option(
            value=ContactRequestStatus.PENDING.label.lower()
        )
        assert page.locator("[data-request-visible-count]").inner_text() == "1"
        page.locator("[data-request-status-filter]").select_option(value="all")
        assert_no_horizontal_overflow()
        incoming_detail_url = page.locator(
            ".contact-request-card .request-action-link"
        ).first.get_attribute("href")
        page.locator(
            f".request-workspace-tabs__links a[href='{reverse('connections:outgoing')}']"
        ).click()
        assert page.get_by_role("heading", name="Outgoing requests", exact=True).is_visible()
        page.locator(
            f".request-workspace-tabs__links a[href='{reverse('connections:incoming')}']"
        ).click()
        assert page.get_by_role("heading", name="Incoming requests", exact=True).is_visible()
        response = page.goto(f"{live_server.url}{incoming_detail_url}")
        assert response is not None and response.status == 200
        assert peer.email not in page.locator("body").inner_text()

        page.goto(f"{live_server.url}{reverse('connections:outgoing')}")
        assert page.get_by_role("heading", name="Outgoing requests", exact=True).is_visible()
        assert page.locator("[data-summary-count='my-requests']").inner_text() == "3"
        assert page.locator("[data-summary-count='incoming']").inner_text() == "2"
        assert page.locator("[data-summary-count='outgoing']").inner_text() == "2"
        assert page.locator("[data-request-row]").count() == 2
        page.locator("[data-request-status-filter]").select_option(
            value=ContactRequestStatus.PENDING.label.lower()
        )
        assert page.locator("[data-request-visible-count]").inner_text() == "1"
        assert_no_horizontal_overflow()
        outgoing_detail_url = page.locator(
            ".contact-request-card .request-action-link"
        ).first.get_attribute("href")
        response = page.goto(f"{live_server.url}{outgoing_detail_url}")
        assert response is not None and response.status == 200
        assert peer.email not in page.locator("body").inner_text()
        browser.close()
