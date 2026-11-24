"""Responsive browser coverage for the existing three-step signup journey."""

import os
from pathlib import Path

import pytest
from allauth.account.models import EmailAddress
from allauth.socialaccount.adapter import get_adapter
from allauth.socialaccount.models import SocialAccount, SocialLogin
from django.contrib.auth import get_user_model
from django.test import Client, RequestFactory
from django.urls import reverse
from playwright.sync_api import sync_playwright

from apps.accounts.models import AccountStatus
from apps.accounts.verification import mock_verification_provider


ROOT = Path(__file__).resolve().parents[2]
SCREENSHOT_ROOT = ROOT / "tests" / "ui" / "screenshots" / "signup"
VIEWPORTS = (320, 375, 390, 414, 480, 768, 1024, 1280, 1366, 1440, 1920)
CAPTURE_WIDTHS = {390: "mobile", 1366: "desktop"}
SYNTHETIC_EMAIL = "signup-flow@example.test"


def _capture_if_requested(page, page_key, width):
    label = CAPTURE_WIDTHS.get(width)
    if label and os.environ.get("BLOODCONNECT_CAPTURE_SIGNUP_SCREENSHOTS") == "1":
        folder = SCREENSHOT_ROOT / page_key / label
        folder.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(folder / "baseline.png"), full_page=True)


def _assert_axe_clean(page, axe_script, page_key):
    page.add_script_tag(path=str(axe_script))
    violations = page.evaluate(
        """async () => {
          const result = await axe.run(document, {
            runOnly: {type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']}
          });
          return result.violations.map(v => ({id: v.id, targets: v.nodes.map(n => n.target)}));
        }"""
    )
    assert not violations, f"{page_key} axe violations: {violations}"


def _seed_social_signup_session(settings):
    client_id = "synthetic-signup-client"
    settings.GOOGLE_OAUTH_ENABLED = True
    settings.GOOGLE_OAUTH_CLIENT_ID = client_id
    settings.GOOGLE_OAUTH_CLIENT_SECRET = "synthetic-signup-secret"
    settings.SOCIALACCOUNT_PROVIDERS["google"]["APP"].update(
        {"client_id": client_id, "secret": "synthetic-signup-secret"}
    )
    request = RequestFactory().get("/accounts/3rdparty/signup/")
    provider = get_adapter().get_provider(request, "google", client_id=client_id)
    email = "social-signup@example.test"
    user = get_user_model()(email=email, display_name="Synthetic Signup")
    login = SocialLogin(
        user=user,
        account=SocialAccount(provider="google", uid="synthetic-signup-subject"),
        provider=provider,
        email_addresses=[EmailAddress(email=email, verified=True)],
    )
    client = Client()
    session = client.session
    session["socialaccount_sociallogin"] = login.serialize()
    session.save()
    return session.session_key, email


@pytest.mark.django_db(transaction=True)
def test_three_signup_pages_render_and_complete_existing_flows(live_server, settings):
    mock_verification_provider.clear()
    session_key, google_email = _seed_social_signup_session(settings)
    user = get_user_model().objects.create_user(
        email=SYNTHETIC_EMAIL,
        display_name="Synthetic Verification",
        password="Synthetic-Verification-Password!947",
    )
    user.account_status = AccountStatus.PENDING
    user.save(update_fields=["account_status", "updated_at"])

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context()
        context.add_cookies([
            {
                "name": settings.SESSION_COOKIE_NAME,
                "value": session_key,
                "url": live_server.url,
            }
        ])
        page = context.new_page()
        page.set_viewport_size({"width": 1366, "height": 900})
        page.set_default_timeout(8_000)
        page_errors = []
        axe_script = ROOT / "node_modules" / "axe-core" / "axe.min.js"
        assert axe_script.is_file(), "Install the locked UI audit dependencies with npm ci."
        console_errors = []
        failed_requests = []
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.on(
            "console",
            lambda message: console_errors.append(message.text)
            if message.type == "error"
            else None,
        )
        page.on("requestfailed", lambda request: failed_requests.append(request.url.split("?")[0]))

        registration_url = f"{live_server.url}{reverse('accounts:register')}"
        response = page.goto(registration_url, wait_until="domcontentloaded")
        assert response and response.status == 200
        assert page.get_by_role("heading", name="Create your account").is_visible()
        google_button = page.get_by_role("button", name="Continue with Google")
        assert google_button.is_visible()
        assert google_button.is_enabled()
        assert page.locator("form[data-google-oauth-form] input[name='csrfmiddlewaretoken']").count() == 1
        assert page.locator("form[data-registration-form] input[name='csrfmiddlewaretoken']").count() == 1
        assert page.locator("input[name='email']").count() == 1
        assert page.locator("input[name='phone_e164']").count() == 1
        assert page.locator("input[name='accept_terms']").count() == 1
        assert page.locator("input[name='accept_privacy']").count() == 1

        for width in VIEWPORTS:
            page.set_viewport_size({"width": width, "height": 900})
            dimensions = page.evaluate(
                """() => ({viewport: document.documentElement.clientWidth,
                  document: document.documentElement.scrollWidth})"""
            )
            assert dimensions["document"] <= dimensions["viewport"] + 1, (
                f"Registration overflow at {width}px: {dimensions}"
            )
            _capture_if_requested(page, "register", width)

        page.set_viewport_size({"width": 390, "height": 844})
        _assert_axe_clean(page, axe_script, "register/mobile")
        page.set_viewport_size({"width": 1366, "height": 900})
        _assert_axe_clean(page, axe_script, "register/desktop")

        # Click the rendered allauth button and inspect its real Google redirect.
        oauth_page = context.new_page()
        oauth_page.set_default_timeout(8_000)
        oauth_page.goto(registration_url, wait_until="domcontentloaded")
        oauth_page.route("https://accounts.google.com/**", lambda route: route.abort())
        with oauth_page.expect_response(
            lambda candidate: candidate.request.method == "POST"
            and candidate.url.rstrip("/").endswith("/accounts/google/login")
        ) as oauth_start_response:
            oauth_page.get_by_role("button", name="Continue with Google").click()
        oauth_response = oauth_start_response.value
        assert oauth_response.status == 302
        google_redirect = oauth_response.headers.get("location", "")
        assert google_redirect.startswith("https://accounts.google.com/")
        assert "client_id=synthetic-signup-client" in google_redirect
        assert "code_challenge_method=S256" in google_redirect
        oauth_page.close()

        page.locator(".registration-mode__option").filter(has_text="Phone").click()
        assert page.locator("input[name='phone_e164']").is_visible()
        assert page.locator("input[name='email']").is_disabled()
        page.locator("[data-password-toggle='id_password1']").click()
        assert page.locator("input[name='password1']").get_attribute("type") == "text"
        page.locator("[data-password-toggle='id_password1']").click()
        assert page.locator("input[name='password1']").get_attribute("type") == "password"

        # An empty submission exercises real Django validation and creates no account.
        with page.expect_navigation(wait_until="domcontentloaded"):
            page.locator("[data-registration-submit]").click()
        assert "Please review the highlighted fields." in page.locator("body").inner_text()
        assert page.get_by_text("This field is required.").first.is_visible()
        _assert_axe_clean(page, axe_script, "register/validation-error")

        social_url = f"{live_server.url}{reverse('socialaccount_signup')}"
        response = page.goto(social_url, wait_until="domcontentloaded")
        assert response and response.status == 200
        assert page.get_by_role("heading", name="Finish creating your account").is_visible()
        assert page.locator("input[name='email']").is_disabled()
        assert page.locator("input[name='email']").input_value() == google_email
        assert page.locator("input[name='display_name']").input_value() == "Synthetic Signup"
        assert page.get_by_role("link", name="Cancel and return to registration").get_attribute(
            "href"
        ) == reverse("accounts:register")
        page.get_by_role("link", name="Cancel and return to registration").click()
        assert page.url.endswith(reverse("accounts:register"))
        page.goto(social_url, wait_until="domcontentloaded")
        for width in VIEWPORTS:
            page.set_viewport_size({"width": width, "height": 900})
            dimensions = page.evaluate(
                """() => ({viewport: document.documentElement.clientWidth,
                  document: document.documentElement.scrollWidth})"""
            )
            assert dimensions["document"] <= dimensions["viewport"] + 1, (
                f"Third-party signup overflow at {width}px: {dimensions}"
            )
            _capture_if_requested(page, "third-party", width)

        page.set_viewport_size({"width": 390, "height": 844})
        _assert_axe_clean(page, axe_script, "third-party/mobile")
        page.set_viewport_size({"width": 1366, "height": 900})
        _assert_axe_clean(page, axe_script, "third-party/desktop")

        page.locator("input[name='display_name']").fill("Synthetic Signup Person")
        with page.expect_navigation(wait_until="domcontentloaded"):
            page.get_by_role("button", name="Create pending account").click()
        assert "Please review the highlighted information." in page.locator("body").inner_text()
        _assert_axe_clean(page, axe_script, "third-party/validation-error")
        page.locator("input[name='accept_terms']").check()
        page.locator("input[name='accept_privacy']").check()
        page.get_by_role("button", name="Create pending account").click()
        assert page.wait_for_url(f"**{reverse('accounts:verify')}") is None
        assert page.get_by_role("heading", name="Verify your account").is_visible()
        assert page.locator("input[name='code']").count() == 1
        assert page.locator("input[name='identifier']").get_attribute("type") == "hidden"
        assert page.get_by_text(google_email).is_visible()

        for width in VIEWPORTS:
            page.set_viewport_size({"width": width, "height": 900})
            dimensions = page.evaluate(
                """() => ({viewport: document.documentElement.clientWidth,
                  document: document.documentElement.scrollWidth})"""
            )
            assert dimensions["document"] <= dimensions["viewport"] + 1, (
                f"Verification overflow at {width}px: {dimensions}"
            )
            _capture_if_requested(page, "verify", width)

        page.set_viewport_size({"width": 390, "height": 844})
        _assert_axe_clean(page, axe_script, "verify/mobile")
        page.set_viewport_size({"width": 1366, "height": 900})
        _assert_axe_clean(page, axe_script, "verify/desktop")

        assert page.get_by_role("link", name="Request or resend a code").get_attribute(
            "href"
        ) == reverse("accounts:verification_start")
        page.get_by_role("link", name="Request or resend a code").click()
        assert page.url.endswith(reverse("accounts:verification_start"))
        page.goto(f"{live_server.url}{reverse('accounts:verify')}", wait_until="domcontentloaded")
        social_code = mock_verification_provider.messages[-1].code
        invalid_code = "999999" if social_code != "999999" else "000000"
        page.locator("input[name='code']").fill(invalid_code)
        page.get_by_role("button", name="Verify account").click()
        assert page.get_by_role("alert").is_visible()
        assert page.get_by_role("alert").get_by_text(
            "The code is invalid, expired, or already used."
        ).is_visible()
        _assert_axe_clean(page, axe_script, "verify/invalid-code")
        page.locator("input[name='code']").fill(social_code)
        page.get_by_role("button", name="Verify account").click()
        assert page.wait_for_url(f"**{reverse('accounts:login')}") is None
        assert page.get_by_role("status").get_by_text("Your email has been verified.").is_visible()

        assert not page_errors, page_errors
        assert not console_errors, console_errors
        assert not failed_requests, failed_requests
        browser.close()
