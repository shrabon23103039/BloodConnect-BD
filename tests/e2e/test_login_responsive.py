"""Read-only responsive checks for the existing sign-in workflow."""

import os
from pathlib import Path

from django.urls import reverse
from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[2]
SCREENSHOT_DIR = ROOT / "tests" / "ui" / "screenshots" / "sign-in"
VIEWPORTS = (320, 375, 390, 414, 480, 768, 1024, 1280, 1366, 1440, 1920)
CAPTURE_WIDTHS = {390: "mobile", 1366: "desktop"}


def test_sign_in_responsive_routes_and_navigation(live_server):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1366, "height": 900})
        page.set_default_timeout(8_000)
        page_errors = []
        console_errors = []
        failed_requests = []
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.on(
            "console",
            lambda message: console_errors.append(message.text)
            if message.type == "error"
            else None,
        )
        page.on(
            "requestfailed",
            lambda request: failed_requests.append(request.url.split("?")[0]),
        )

        response = page.goto(
            f"{live_server.url}{reverse('accounts:login')}",
            wait_until="domcontentloaded",
        )
        assert response and response.status == 200
        assert page.get_by_role("heading", name="Sign in to BloodConnect BD").is_visible()
        assert page.get_by_role("heading", name="Sign in", exact=True).is_visible()
        assert page.locator("form.login-form input[name='csrfmiddlewaretoken']").count() == 1
        assert page.locator("form.login-form input[name='username']").count() == 1
        assert page.locator("form.login-form input[name='password']").count() == 1
        assert page.locator("input[type='password']").count() == 1
        assert page.locator("a[aria-current='page']").get_attribute("href") == reverse("accounts:login")

        destinations = (
            "accounts:password_reset",
            "accounts:phone_password_reset",
            "accounts:verification_start",
            "accounts:register",
            "how_it_works",
            "safety",
            "privacy",
            "donors:search",
            "terms",
            "contact",
        )
        for route_name in destinations:
            destination = reverse(route_name)
            result = page.request.get(f"{live_server.url}{destination}")
            assert result.status < 400, f"Destination failed: {destination}"

        for width in VIEWPORTS:
            page.set_viewport_size({"width": width, "height": 900})
            dimensions = page.evaluate(
                """() => ({
                  viewport: document.documentElement.clientWidth,
                  document: document.documentElement.scrollWidth,
                  main: document.querySelector('#main-content').scrollWidth
                })"""
            )
            overflow = max(dimensions["document"], dimensions["main"]) - dimensions["viewport"]
            assert overflow <= 1, f"Sign-in page overflows by {overflow}px at {width}px"

            if width in CAPTURE_WIDTHS and os.environ.get("BLOODCONNECT_CAPTURE_LOGIN_SCREENSHOTS") == "1":
                screenshot_folder = SCREENSHOT_DIR / CAPTURE_WIDTHS[width]
                screenshot_folder.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(screenshot_folder / "baseline.png"), full_page=True)

        page.set_viewport_size({"width": 390, "height": 844})
        toggler = page.get_by_role("button", name="Toggle navigation")
        assert toggler.is_visible()
        toggler.click()
        navigation = page.locator("#site-navigation")
        assert navigation.is_visible()
        assert navigation.get_by_role("link", name="How it works").is_visible()
        navigation.get_by_role("link", name="How it works").click()
        assert page.url.endswith(reverse("how_it_works"))

        keyboard_page = browser.new_page(viewport={"width": 1366, "height": 900})
        keyboard_page.goto(
            f"{live_server.url}{reverse('accounts:login')}",
            wait_until="domcontentloaded",
        )
        assert keyboard_page.evaluate("document.activeElement.name") == "username"
        keyboard_page.keyboard.press("Tab")
        assert keyboard_page.evaluate("document.activeElement.name") == "password"
        assert not page_errors, page_errors
        assert not console_errors, console_errors
        assert not failed_requests, failed_requests
        browser.close()
