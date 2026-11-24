"""Browser coverage for the registration status and verification request steps."""

import os
from pathlib import Path

import pytest
from django.core.cache import cache
from django.urls import reverse
from playwright.sync_api import sync_playwright

from apps.accounts.verification import mock_verification_provider


ROOT = Path(__file__).resolve().parents[2]
SCREENSHOT_ROOT = ROOT / "tests" / "ui" / "screenshots" / "account-status"
VIEWPORTS = (320, 375, 390, 414, 768, 1024, 1280, 1440)
CAPTURE_WIDTHS = {390: "mobile", 1280: "desktop"}


def _capture(page, page_key, width):
    label = CAPTURE_WIDTHS.get(width)
    if label and os.environ.get("BLOODCONNECT_CAPTURE_ACCOUNT_STATUS") == "1":
        folder = SCREENSHOT_ROOT / page_key / label
        folder.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(folder / "baseline.png"), full_page=True)


def _assert_no_overflow(page, page_key):
    dimensions = page.evaluate(
        """() => ({viewport: document.documentElement.clientWidth,
          document: document.documentElement.scrollWidth})"""
    )
    assert dimensions["document"] <= dimensions["viewport"] + 1, (
        f"{page_key} overflow: {dimensions}"
    )


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


@pytest.mark.django_db(transaction=True)
def test_registration_status_verification_request_and_code_flow(live_server):
    cache.clear()
    mock_verification_provider.clear()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.set_default_timeout(8_000)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        axe_script = ROOT / "node_modules" / "axe-core" / "axe.min.js"
        assert axe_script.is_file(), "Install the locked UI audit dependencies with npm ci."

        page.goto(f"{live_server.url}{reverse('accounts:register')}")
        page.locator("input[name='display_name']").fill("Synthetic Status Flow")
        page.locator("input[name='email']").fill("status-flow@example.test")
        page.locator("input[name='password1']").fill("Synthetic-Status-Password!572")
        page.locator("input[name='password2']").fill("Synthetic-Status-Password!572")
        page.locator("input[name='accept_terms']").check()
        page.locator("input[name='accept_privacy']").check()
        page.get_by_role("button", name="Create account").click()
        assert page.wait_for_url(f"**{reverse('accounts:registration_submitted')}") is None
        assert page.get_by_role("heading", name="Account created — verification required").is_visible()
        assert page.get_by_role("link", name="Continue to verification").is_visible()
        assert page.get_by_role("link", name="Return home").is_visible()
        assert page.locator(".navbar-nav a.btn-brand").get_attribute("aria-current") == "page"

        for width in VIEWPORTS:
            page.set_viewport_size({"width": width, "height": 900})
            _assert_no_overflow(page, f"submitted/{width}")
            _capture(page, "submitted", width)
        page.set_viewport_size({"width": 390, "height": 844})
        _assert_axe_clean(page, axe_script, "submitted/mobile")

        page.get_by_role("link", name="Continue to verification").click()
        assert page.wait_for_url(f"**{reverse('accounts:verification_start')}") is None
        assert page.get_by_role("heading", name="Request a verification code").is_visible()
        assert page.locator(".navbar-nav a.btn-brand").get_attribute("aria-current") == "page"
        identifier = page.locator("input[name='identifier']")
        assert identifier.is_visible()
        identifier.fill("status-flow@example.test")

        for width in VIEWPORTS:
            page.set_viewport_size({"width": width, "height": 900})
            _assert_no_overflow(page, f"request-code/{width}")
            _capture(page, "request-code", width)
        page.set_viewport_size({"width": 390, "height": 844})
        _assert_axe_clean(page, axe_script, "request-code/mobile")

        page.get_by_role("button", name="Send or resend code").click()
        assert page.wait_for_url(f"**{reverse('accounts:verify')}") is None
        assert page.get_by_role("heading", name="Verify your account").is_visible()
        assert page.locator("input[name='code']").count() == 1
        assert page.locator("input[name='identifier']").input_value() == "status-flow@example.test"
        page.set_viewport_size({"width": 390, "height": 844})
        _assert_axe_clean(page, axe_script, "verify-code/mobile")

        for width in VIEWPORTS:
            page.set_viewport_size({"width": width, "height": 900})
            _assert_no_overflow(page, f"verify-code/{width}")
            _capture(page, "verify-code", width)

        code = mock_verification_provider.messages[-1].code
        wrong_code = "999999" if code != "999999" else "000000"
        page.locator("input[name='code']").fill(wrong_code)
        page.get_by_role("button", name="Verify account").click()
        assert page.get_by_role("alert").get_by_text(
            "The code is invalid, expired, or already used."
        ).is_visible()
        page.locator("input[name='code']").fill(code)
        page.get_by_role("button", name="Verify account").click()
        assert page.wait_for_url(f"**{reverse('accounts:login')}") is None
        assert page.get_by_role("status").get_by_text("Your email has been verified.").is_visible()
        assert not errors, errors
        browser.close()
