"""End-to-end phone reset using the authorized local mock verification provider."""

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone
from playwright.sync_api import sync_playwright

from apps.accounts.models import AccountStatus
from apps.accounts.verification import mock_verification_provider


VIEWPORTS = (360, 390, 768, 1024, 1366)
OLD_PASSWORD = "Synthetic-Phone-Reset-Old!572"
NEW_PASSWORD = "Synthetic-Phone-Reset-New!628"


def _paste_text(page, text):
    return page.locator("input[name='code']").evaluate(
        """(input, text) => {
          const clipboard = new DataTransfer();
          clipboard.setData('text/plain', text);
          const event = new ClipboardEvent('paste', {
            clipboardData: clipboard, bubbles: true, cancelable: true
          });
          input.dispatchEvent(event);
          return event.defaultPrevented;
        }""",
        text,
    )


@pytest.mark.django_db(transaction=True)
def test_phone_reset_sms_paste_flow_completes_with_mock_provider(live_server):
    cache.clear()
    mock_verification_provider.clear()
    user = get_user_model().objects.create_user(
        phone_e164="+8801700000852",
        display_name="Synthetic Phone Reset",
        password=OLD_PASSWORD,
    )
    user.account_status = AccountStatus.ACTIVE
    user.phone_verified_at = timezone.now()
    user.save(update_fields=["account_status", "phone_verified_at", "updated_at"])

    page_errors = []
    console_errors = []
    failed_requests = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1366, "height": 900})
        page.set_default_timeout(8_000)
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.on(
            "console",
            lambda message: console_errors.append(message.text)
            if message.type == "error"
            else None,
        )
        page.on("requestfailed", lambda request: failed_requests.append(request.url.split("?")[0]))

        page.goto(
            f"{live_server.url}{reverse('accounts:phone_password_reset')}",
            wait_until="domcontentloaded",
        )
        page.locator("input[name='phone_e164']").fill("01700000852")
        page.get_by_role("button", name="Request reset code").click()
        assert page.get_by_role("status").get_by_text(
            "If an active account matches"
        ).is_visible()
        page.get_by_role("link", name="Enter reset code").click()
        assert page.url.endswith(reverse("accounts:phone_password_reset_verify"))

        code = mock_verification_provider.messages[-1].code
        input_box = page.locator("input[name='code']")
        assert input_box.get_attribute("maxlength") == "6"
        assert input_box.get_attribute("inputmode") == "numeric"
        assert input_box.get_attribute("autocomplete") == "one-time-code"
        assert page.evaluate("document.activeElement.name") == "code"

        for width in VIEWPORTS:
            page.set_viewport_size({"width": width, "height": 900})
            assert page.evaluate(
                "document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1"
            ), f"Phone reset verification overflows at {width}px"

        assert _paste_text(page, f"Code 111111 and backup 222222")
        assert input_box.input_value() == ""
        assert page.get_by_text("This message contains more than one six-digit code.").is_visible()
        assert _paste_text(page, f"\nYour BloodConnect reset code is: [{code}].\n")
        assert input_box.input_value() == code
        assert page.get_by_text("One six-digit code was filled.").is_visible()
        page.locator("input[name='phone_e164']").fill("01700000852")
        page.get_by_role("button", name="Continue").click()
        assert page.url.endswith(reverse("accounts:phone_password_reset_confirm"))

        page.locator("input[name='new_password1']").fill(NEW_PASSWORD)
        page.locator("input[name='new_password2']").fill(NEW_PASSWORD)
        page.get_by_role("button", name="Save password").click()
        assert page.url.endswith(reverse("accounts:password_reset_complete"))

        assert page.get_by_role("heading", name="Password updated").is_visible()
        assert not page_errors, page_errors
        assert not console_errors, console_errors
        assert not failed_requests, failed_requests
        browser.close()
    cache.clear()
