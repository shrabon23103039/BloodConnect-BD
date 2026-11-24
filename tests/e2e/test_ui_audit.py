"""Read-only route, responsive, screenshot, and axe baseline audit.

All authenticated browsing uses one synthetic account in pytest's isolated DB.
No form is submitted and the suite never accesses a user's live session.
"""

import json
import os
from pathlib import Path
import subprocess
import tempfile

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from playwright.sync_api import sync_playwright

from apps.accounts.models import AccountStatus
from tests.ui.audit_config import (
    ACTIVE_NAVIGATION,
    PAGES,
    SCREENSHOT_PAGES,
    NOT_IN_BASELINE,
    SCREENSHOT_WIDTHS,
    UNAVAILABLE_DOCUMENTED_PAGES,
    VIEWPORT_WIDTHS,
)


ROOT = Path(__file__).resolve().parents[2]
REPORT_PATH = ROOT / "tests" / "ui" / "baseline-results.json"
SCREENSHOT_ROOT = ROOT / "tests" / "ui" / "screenshots"
SCREENSHOT_DIFF_SCRIPT = ROOT / "tests" / "ui" / "compare_screenshots.mjs"
SYNTHETIC_EMAIL = "ui-audit@example.test"
SYNTHETIC_PASSWORD = "Synthetic-UI-Audit-Password!947"


@pytest.mark.django_db(transaction=True)
def test_read_only_ui_baseline(live_server, settings):
    """Visit actual route inventory at each requested width and record findings."""
    user = get_user_model().objects.create_user(
        email=SYNTHETIC_EMAIL,
        password=SYNTHETIC_PASSWORD,
        display_name="Synthetic UI Audit",
    )
    user.account_status = AccountStatus.ACTIVE
    user.email_verified_at = timezone.now()
    user.save(update_fields=["account_status", "email_verified_at", "updated_at"])

    axe_script = ROOT / "node_modules" / "axe-core" / "axe.min.js"
    assert axe_script.is_file(), "Install locked test dependency with npm ci first."
    audit = {
        "environment": "pytest live_server + isolated in-memory SQLite + synthetic user",
        "authenticated_session": "synthetic pytest user; existing human browser session was not accessed",
        "viewports": list(VIEWPORT_WIDTHS),
        "pages": [],
        "unavailable_documented_pages": UNAVAILABLE_DOCUMENTED_PAGES,
        "not_in_baseline": NOT_IN_BASELINE,
    }
    route_errors = []
    visual_regression_failures = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        public_context = browser.new_context()
        public_page = public_context.new_page()
        auth_context = browser.new_context()
        auth_page = auth_context.new_page()
        for active_page in (public_page, auth_page):
            active_page.set_default_timeout(10_000)
        page_errors = []
        console_errors = []
        failed_requests = []
        public_page.on("pageerror", lambda error: page_errors.append(str(error)))
        auth_page.on("pageerror", lambda error: page_errors.append(str(error)))
        public_page.on(
            "console",
            lambda message: console_errors.append(message.text)
            if message.type == "error"
            else None,
        )
        auth_page.on(
            "console",
            lambda message: console_errors.append(message.text)
            if message.type == "error"
            else None,
        )
        public_page.on(
            "requestfailed",
            lambda request: failed_requests.append(
                {"url": request.url.split("?")[0], "error": request.failure}
            ),
        )
        auth_page.on(
            "requestfailed",
            lambda request: failed_requests.append(
                {"url": request.url.split("?")[0], "error": request.failure}
            ),
        )

        auth_page.goto(f"{live_server.url}{reverse('accounts:login')}")
        auth_page.locator("input[name='username']").fill(SYNTHETIC_EMAIL)
        auth_page.locator("input[name='password']").fill(SYNTHETIC_PASSWORD)
        auth_page.get_by_role("button", name="Sign in").click()
        assert auth_page.get_by_role("button", name="Sign out").is_visible()

        for item in PAGES:
            target_url = reverse(item.url_name)
            item_result = {
                "key": item.key,
                "label": item.label,
                "url": target_url,
                "authenticated": item.authenticated,
                "status": "PASS",
                "viewports": [],
            }
            page = auth_page if item.authenticated else public_page
            response = page.goto(f"{live_server.url}{target_url}", wait_until="domcontentloaded")
            status = response.status if response else None
            if status is None or status >= 400:
                item_result["status"] = "ISSUES FOUND"
                route_errors.append({"page": item.key, "http_status": status})
            for width in VIEWPORT_WIDTHS:
                page.set_viewport_size({"width": width, "height": 900})
                metrics = page.evaluate(
                    """() => ({
                      viewportWidth: document.documentElement.clientWidth,
                      documentWidth: document.documentElement.scrollWidth,
                      title: document.title,
                      headingCount: document.querySelectorAll('h1').length,
                      bodyFont: getComputedStyle(document.body).fontFamily,
                      bodyFontSize: getComputedStyle(document.body).fontSize,
                      bodyLineHeight: getComputedStyle(document.body).lineHeight
                    })"""
                )
                metrics["currentNavigationHrefs"] = page.locator(
                    '.app-nav-link[aria-current="page"]'
                ).evaluate_all("els => els.map(el => el.getAttribute('href'))")
                expected_navigation = ACTIVE_NAVIGATION.get(item.key)
                metrics["expectedNavigationHref"] = (
                    reverse(expected_navigation) if expected_navigation else None
                )
                if metrics["expectedNavigationHref"] and metrics["expectedNavigationHref"] not in metrics["currentNavigationHrefs"]:
                    findings.append("expected active navigation item missing")
                    item_result["status"] = "ISSUES FOUND"
                metrics["horizontalOverflowPx"] = max(
                    0, metrics["documentWidth"] - metrics["viewportWidth"]
                )
                findings = []
                if metrics["horizontalOverflowPx"] > 1:
                    findings.append("horizontal overflow")
                    item_result["status"] = "ISSUES FOUND"

                # Run axe only at representative desktop/mobile sizes to bound suite cost.
                axe_result = None
                if width in SCREENSHOT_WIDTHS:
                    page.add_script_tag(path=str(axe_script))
                    axe_result = page.evaluate(
                        """async () => {
                          const result = await axe.run(document, {
                            runOnly: {type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']}
                          });
                          return result.violations.map(v => ({
                            id: v.id, impact: v.impact, description: v.description,
                            nodes: v.nodes.map(n => ({target: n.target, summary: n.failureSummary}))
                          }));
                        }"""
                    )
                    metrics["axeViolations"] = axe_result
                    if axe_result:
                        item_result["status"] = "ISSUES FOUND"
                    if (
                        os.environ.get("BLOODCONNECT_CAPTURE_UI_AUDIT") == "1"
                        and item.key in SCREENSHOT_PAGES
                    ):
                        device = SCREENSHOT_WIDTHS[width]
                        screenshot_dir = SCREENSHOT_ROOT / item.key / device
                        screenshot_dir.mkdir(parents=True, exist_ok=True)
                        page.screenshot(path=str(screenshot_dir / "baseline.png"), full_page=True)
                    elif (
                        os.environ.get("BLOODCONNECT_COMPARE_UI_AUDIT") == "1"
                        and item.key in SCREENSHOT_PAGES
                    ):
                        device = SCREENSHOT_WIDTHS[width]
                        baseline_path = SCREENSHOT_ROOT / item.key / device / "baseline.png"
                        if not baseline_path.is_file():
                            metrics["visualRegression"] = {"status": "MISSING_BASELINE"}
                            visual_regression_failures.append(item.key)
                        else:
                            diff_dir = ROOT / "tests" / "ui" / "diffs" / item.key / device
                            diff_dir.mkdir(parents=True, exist_ok=True)
                            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as current_file:
                                current_path = Path(current_file.name)
                            try:
                                page.screenshot(path=str(current_path), full_page=True)
                                comparison = subprocess.run(
                                    [
                                        "node",
                                        str(SCREENSHOT_DIFF_SCRIPT),
                                        str(baseline_path),
                                        str(current_path),
                                        str(diff_dir / "diff.png"),
                                    ],
                                    check=False,
                                    capture_output=True,
                                    text=True,
                                )
                                result_line = comparison.stdout.strip().splitlines()[-1]
                                metrics["visualRegression"] = json.loads(result_line)
                                if comparison.returncode:
                                    visual_regression_failures.append(item.key)
                                    item_result["status"] = "ISSUES FOUND"
                            finally:
                                current_path.unlink(missing_ok=True)
                metrics["findings"] = findings
                item_result["viewports"].append({"width": width, **metrics})
            audit["pages"].append(item_result)

        audit["browser_errors"] = {
            "page_errors": page_errors,
            "console_errors": console_errors,
            "failed_requests": failed_requests,
        }
        audit["route_errors"] = route_errors

        navigation_smoke = []
        auth_page.set_viewport_size({"width": 1366, "height": 900})
        auth_page.goto(f"{live_server.url}{reverse('home')}", wait_until="domcontentloaded")
        for url_name in (
            "donors:search",
            "requests:list",
            "donors:profile",
            "governance:privacy_settings",
            "accounts:google_link",
            "safety",
        ):
            destination = reverse(url_name)
            link = auth_page.locator(f'.app-nav a[href="{destination}"]').first
            link.click()
            assert auth_page.url.endswith(destination)
            navigation_smoke.append({"href": destination, "status": "PASS"})

        auth_page.set_viewport_size({"width": 390, "height": 844})
        auth_page.goto(f"{live_server.url}{reverse('home')}", wait_until="domcontentloaded")
        auth_page.get_by_role("button", name="Open navigation menu").click()
        drawer = auth_page.locator("#mobile-app-navigation")
        assert drawer.is_visible()
        mobile_link = drawer.locator(f'a[href="{reverse("requests:list")}"]')
        mobile_link_visible = mobile_link.is_visible()
        mobile_link_href = mobile_link.get_attribute("href")
        mobile_link.click()
        mobile_navigation = "PASS" if auth_page.url.endswith(reverse("requests:list")) else "ISSUES FOUND"
        navigation_smoke.append(
            {
                "href": mobile_link_href,
                "visible_in_drawer": mobile_link_visible,
                "status": mobile_navigation,
                "viewport": 390,
                "final_path": auth_page.url.split(live_server.url)[-1],
            }
        )
        audit["navigation_smoke"] = navigation_smoke

        public_context.close()
        auth_context.close()
        browser.close()

    REPORT_PATH.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    assert not route_errors, f"UI route errors recorded in {REPORT_PATH}"
    assert not visual_regression_failures, (
        f"Visual baseline differences for {sorted(set(visual_regression_failures))}; "
        f"see {REPORT_PATH} and tests/ui/diffs/"
    )
