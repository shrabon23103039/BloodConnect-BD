import tempfile
from pathlib import Path

import pytest
from django.core.cache import cache
from django.urls import reverse
from playwright.sync_api import sync_playwright


@pytest.mark.django_db(transaction=True)
def test_registration_redesign_is_responsive_and_retains_controls(live_server, settings):
    cache.clear()
    settings.GOOGLE_OAUTH_ENABLED = True
    settings.GOOGLE_OAUTH_CLIENT_ID = "synthetic-ui-client"
    settings.GOOGLE_OAUTH_CLIENT_SECRET = "synthetic-ui-secret"
    settings.SOCIALACCOUNT_PROVIDERS["google"]["APP"].update(
        {"client_id": "synthetic-ui-client", "secret": "synthetic-ui-secret"}
    )
    console_errors = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda error: console_errors.append(str(error)))
        for width in (360, 390, 768, 1366):
            page.set_viewport_size({"width": width, "height": 900})
            page.goto(f"{live_server.url}{reverse('accounts:register')}")
            assert page.get_by_role("heading", name="Create your account").is_visible()
            assert page.get_by_role("button", name="Continue with Google").is_enabled()
            assert page.locator("body").evaluate("node => node.scrollWidth <= innerWidth")
            assert page.locator("input[name='email']").count() == 1
            assert page.locator("input[name='phone_e164']").count() == 1
            assert page.locator("input[name='password1']").count() == 1
            assert page.locator("input[name='password2']").count() == 1
            assert page.locator("#main-content").get_by_role("link", name="Sign in").is_visible()
            if width in (390, 1366):
                label = "mobile" if width == 390 else "desktop"
                page.screenshot(
                    path=str(Path(tempfile.gettempdir()) / f"bloodconnect-create-account-{label}.png"),
                    full_page=True,
                )
        page.locator(".registration-mode__option").filter(has_text="Phone").click()
        assert page.locator("input[name='phone_e164']").is_visible()
        assert page.locator("input[name='email']").is_disabled()
        page.locator("[data-password-toggle='id_password1']").click()
        assert page.locator("input[name='password1']").get_attribute("type") == "text"
        assert not console_errors
        browser.close()
    cache.clear()
