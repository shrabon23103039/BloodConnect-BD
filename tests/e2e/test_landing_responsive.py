"""Responsive and navigation smoke coverage for the public landing page."""

import os
from pathlib import Path

import pytest
from django.urls import reverse
from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[2]
SCREENSHOT_DIR = ROOT / "tests" / "ui" / "screenshots" / "home"
VIEWPORTS = (320, 375, 390, 414, 480, 768, 1024, 1280, 1366, 1440, 1920)
CAPTURE_WIDTHS = {390: "mobile", 1366: "desktop"}


def test_landing_responsive_navigation_and_routes(live_server):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1366, "height": 900})
        page.set_default_timeout(8_000)
        response = page.goto(f"{live_server.url}{reverse('home')}", wait_until="domcontentloaded")
        assert response and response.status == 200
        assert page.get_by_role("heading", name="Make it easier to reach a potential donor.").is_visible()
        assert page.get_by_role("link", name="See how it works").is_visible()

        route_names = (
            "how_it_works",
            "safety",
            "privacy",
            "donors:search",
            "accounts:login",
            "accounts:register",
        )
        for route_name in route_names:
            destination = reverse(route_name)
            matching_links = page.locator(f'a[href="{destination}"]')
            assert matching_links.count() > 0, f"Missing landing-page link for {route_name}"
            route_response = page.request.get(f"{live_server.url}{destination}")
            assert route_response.status < 400, f"Destination failed: {destination}"

        route_metrics = []
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
            route_metrics.append({"width": width, "overflow": max(0, overflow)})
            assert overflow <= 1, f"Landing page overflows by {overflow}px at {width}px"

            if width in CAPTURE_WIDTHS and os.environ.get("BLOODCONNECT_CAPTURE_HOME_SCREENSHOTS") == "1":
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

        page.goto(f"{live_server.url}{reverse('home')}", wait_until="domcontentloaded")
        page.keyboard.press("Tab")
        assert page.evaluate("document.activeElement.classList.contains('skip-link')")
        browser.close()
