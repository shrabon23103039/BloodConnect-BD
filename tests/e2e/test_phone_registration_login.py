"""Complete phone signup, mock verification, sign-in and sign-out in Chromium."""

import pytest
from django.core.cache import cache
from django.urls import reverse
from playwright.sync_api import sync_playwright

from apps.accounts.verification import mock_verification_provider


PHONE = "01700000855"
PASSWORD = "Synthetic-Phone-Signup!572"


@pytest.mark.django_db(transaction=True)
def test_phone_signup_verification_signin_and_signout(live_server):
    cache.clear()
    mock_verification_provider.clear()
    page_errors = []
    console_errors = []
    failed_requests = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.set_default_timeout(8_000)
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.on(
            "console",
            lambda message: console_errors.append(message.text)
            if message.type == "error"
            else None,
        )
        page.on("requestfailed", lambda request: failed_requests.append(request.url.split("?")[0]))

        page.goto(f"{live_server.url}{reverse('accounts:register')}")
        page.locator(".registration-mode__option").filter(has_text="Phone").click()
        assert page.locator("input[name='phone_e164']").is_enabled()
        assert page.locator("input[name='email']").is_disabled()
        page.locator("input[name='display_name']").fill("Synthetic Phone Signup")
        page.locator("input[name='phone_e164']").fill(PHONE)
        page.locator("input[name='password1']").fill(PASSWORD)
        page.locator("input[name='password2']").fill(PASSWORD)
        page.locator("input[name='accept_terms']").check()
        page.locator("input[name='accept_privacy']").check()
        page.get_by_role("button", name="Create account").click()
        assert page.url.endswith(reverse("accounts:registration_submitted"))
        assert page.get_by_role(
            "heading", name="Account created — verification required"
        ).is_visible()

        page.get_by_role("link", name="Continue to verification").click()
        assert page.url.endswith(reverse("accounts:verification_start"))
        page.locator("input[name='identifier']").fill(PHONE)
        page.get_by_role("button", name="Send or resend code").click()
        assert page.url.endswith(reverse("accounts:verify"))
        assert page.locator("input[name='identifier']").input_value() == "+8801700000855"
        code = mock_verification_provider.messages[-1].code
        page.locator("input[name='code']").evaluate(
            """(input, code) => {
              input.value = code;
              input.dispatchEvent(new Event('input', {bubbles: true}));
            }""",
            code,
        )
        page.get_by_role("button", name="Verify account").click()
        assert page.url.endswith(reverse("accounts:login"))
        assert page.get_by_role("status").get_by_text(
            "Your phone has been verified. You can now sign in."
        ).is_visible()

        page.locator("input[name='username']").fill(PHONE)
        page.locator("input[name='password']").fill(PASSWORD)
        page.get_by_role("button", name="Sign in").click()
        assert page.url.endswith(reverse("home"))
        assert page.get_by_role("heading", name="Welcome back, Synthetic Phone Signup.").is_visible()
        page.get_by_role("button", name="Open navigation menu").click()
        navigation = page.get_by_role(
            "navigation", name="Mobile application navigation"
        )
        navigation.get_by_role("button", name="Sign out").click()
        assert page.url.endswith(reverse("home"))
        assert page.get_by_role("link", name="Create an account").is_visible()

        assert not page_errors, page_errors
        assert not console_errors, console_errors
        assert not failed_requests, failed_requests
        browser.close()
    cache.clear()
