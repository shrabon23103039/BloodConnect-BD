"""Read-only responsive audit of the shared public/auth web experience."""

import os
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.cache import cache
from django.test import Client
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[2]
SCREENSHOT_ROOT = ROOT / "tests" / "ui" / "screenshots" / "public-web-sync"
VIEWPORTS = (320, 375, 390, 414, 480, 768, 1024, 1280, 1366, 1440, 1920)
SCREENSHOT_WIDTHS = {390: "mobile", 1366: "desktop"}
SCREENSHOT_PAGES = {
    "home", "login", "register", "registration-submitted", "verify",
    "password-reset", "phone-password-reset",
}


def _capture(page, key, width):
    device = SCREENSHOT_WIDTHS.get(width)
    if device and key in SCREENSHOT_PAGES and os.environ.get("BLOODCONNECT_CAPTURE_PUBLIC_WEB") == "1":
        folder = SCREENSHOT_ROOT / key / device
        folder.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(folder / "baseline.png"), full_page=True)


def _assert_public_shell(page, key):
    assert page.locator("body.public-site").count() == 1, f"{key} missing public shell class"
    assert page.locator('link[href*="css/public_web.css"]').count() == 1, (
        f"{key} missing shared public stylesheet"
    )
    assert page.locator(".site-header .brand-mark").count() == 1, f"{key} header missing"
    assert page.locator(".site-footer .footer-links a").count() == 5, f"{key} footer incomplete"


def _assert_no_overflow(page, key, width):
    dimensions = page.evaluate(
        """() => ({viewport: document.documentElement.clientWidth,
          document: document.documentElement.scrollWidth})"""
    )
    assert dimensions["document"] <= dimensions["viewport"] + 1, (
        f"{key} horizontal overflow at {width}px: {dimensions}"
    )


def _assert_axe_clean(page, axe_script, key):
    page.add_script_tag(path=str(axe_script))
    violations = page.evaluate(
        """async () => {
          const result = await axe.run(document, {
            runOnly: {type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']}
          });
          return result.violations.map(v => ({id: v.id, targets: v.nodes.map(n => n.target)}));
        }"""
    )
    assert not violations, f"{key} axe violations: {violations}"


@pytest.mark.django_db(transaction=True)
def test_public_and_auth_pages_share_shell_and_fit_all_requested_widths(live_server, settings):
    cache.clear()
    User = get_user_model()
    user = User.objects.create_user(
        email="public-web-reset@example.test",
        display_name="Synthetic Web Check",
        password="Synthetic-Web-Check-Password!572",
    )
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    phone_user = User.objects.create_user(
        phone_e164="+8801700000572",
        display_name="Synthetic Phone Reset",
        password="Synthetic-Web-Check-Password!572",
    )
    reset_client = Client()
    session = reset_client.session
    session["phone_password_reset_user_id"] = str(phone_user.pk)
    session.save()

    pages = (
        ("home", reverse("home"), 200),
        ("how-it-works", reverse("how_it_works"), 200),
        ("privacy", reverse("privacy"), 200),
        ("safety", reverse("safety"), 200),
        ("terms", reverse("terms"), 200),
        ("contact", reverse("contact"), 200),
        ("login", reverse("accounts:login"), 200),
        ("register", reverse("accounts:register"), 200),
        ("registration-submitted", reverse("accounts:registration_submitted"), 200),
        ("verification-request", reverse("accounts:verification_start"), 200),
        ("verify", reverse("accounts:verify"), 200),
        ("password-reset", reverse("accounts:password_reset"), 200),
        ("password-reset-done", reverse("accounts:password_reset_done"), 200),
        ("password-reset-confirm", reverse("accounts:password_reset_confirm", kwargs={"uidb64": uid, "token": token}), 200),
        ("password-reset-complete", reverse("accounts:password_reset_complete"), 200),
        ("phone-password-reset", reverse("accounts:phone_password_reset"), 200),
        ("phone-password-reset-verify", reverse("accounts:phone_password_reset_verify"), 200),
        ("phone-password-reset-confirm", reverse("accounts:phone_password_reset_confirm"), 200),
    )
    axe_script = ROOT / "node_modules" / "axe-core" / "axe.min.js"
    assert axe_script.is_file(), "Install the locked UI audit dependency with npm ci."

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context()
        context.add_cookies([{
            "name": settings.SESSION_COOKIE_NAME,
            "value": session.session_key,
            "url": live_server.url,
        }])
        page = context.new_page()
        page.set_viewport_size({"width": 1366, "height": 900})
        page.set_default_timeout(8_000)
        page_errors = []
        failed_requests = []
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.on("requestfailed", lambda request: failed_requests.append(request.url.split("?")[0]))

        for key, path, expected_status in pages:
            response = page.goto(f"{live_server.url}{path}", wait_until="domcontentloaded")
            assert response and response.status == expected_status, f"{key}: {response.status if response else None}"
            _assert_public_shell(page, key)
            for width in VIEWPORTS:
                page.set_viewport_size({"width": width, "height": 900})
                _assert_no_overflow(page, key, width)
                _capture(page, key, width)
            if key in {"home", "login", "register", "registration-submitted", "verification-request", "verify", "password-reset", "phone-password-reset"}:
                page.set_viewport_size({"width": 390, "height": 844})
                _assert_axe_clean(page, axe_script, f"{key}/mobile")
                page.set_viewport_size({"width": 1366, "height": 900})
                _assert_axe_clean(page, axe_script, f"{key}/desktop")

        page.set_viewport_size({"width": 390, "height": 844})
        page.goto(f"{live_server.url}{reverse('home')}", wait_until="domcontentloaded")
        menu = page.get_by_role("button", name="Toggle navigation")
        menu.click()
        assert page.locator("#site-navigation").is_visible()
        assert page.locator(f"#site-navigation a[href='{reverse('accounts:register')}']").is_visible()
        assert not page_errors, page_errors
        assert not failed_requests, failed_requests
        context.close()
        browser.close()
