import pytest
from django.core.cache import cache
from playwright.sync_api import sync_playwright
from django.urls import reverse


@pytest.mark.django_db(transaction=True)
def test_google_action_is_responsive_and_starts_stateful_oauth(live_server, settings):
    cache.clear()
    settings.GOOGLE_OAUTH_ENABLED = True
    settings.GOOGLE_OAUTH_CLIENT_ID = "browser-synthetic-client"
    settings.GOOGLE_OAUTH_CLIENT_SECRET = "browser-synthetic-secret"
    settings.SOCIALACCOUNT_PROVIDERS["google"]["APP"].update(
        {"client_id": "browser-synthetic-client", "secret": "browser-synthetic-secret"}
    )
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.set_default_timeout(8_000)
        for width in (360, 390, 768, 1366):
            page.set_viewport_size({"width": width, "height": 850})
            page.goto(f"{live_server.url}{reverse('accounts:login')}")
            button = page.get_by_role("button", name="Continue with Google")
            assert button.is_visible()
            assert page.locator("body").evaluate(
                "element => element.scrollWidth <= window.innerWidth"
            )

        page.locator("[data-google-oauth-form]").evaluate(
            "form => form.addEventListener('submit', event => event.preventDefault())"
        )
        page.get_by_role("button", name="Continue with Google").click()
        button = page.locator("[data-google-oauth-form] button")
        assert button.is_disabled()
        assert button.get_attribute("aria-busy") == "true"
        assert page.locator("[data-google-oauth-status]").inner_text() == "Connecting to Google. Please wait."
        browser.close()
        cache.clear()
