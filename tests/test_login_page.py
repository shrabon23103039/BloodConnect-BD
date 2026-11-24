"""Presentation contract checks for the existing sign-in page."""

from django.test import TestCase
from django.urls import reverse


class LoginPageTests(TestCase):
    def test_login_page_keeps_existing_auth_and_recovery_destinations(self):
        response = self.client.get(reverse("accounts:login"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sign in to")
        self.assertContains(response, 'name="csrfmiddlewaretoken"')
        self.assertContains(response, 'name="username"')
        self.assertContains(response, 'name="password"')
        for route_name in (
            "accounts:password_reset",
            "accounts:phone_password_reset",
            "accounts:verification_start",
            "accounts:register",
        ):
            with self.subTest(route=route_name):
                self.assertContains(response, reverse(route_name))

    def test_login_navigation_is_current_only_on_sign_in_page(self):
        response = self.client.get(reverse("accounts:login"))

        self.assertContains(
            response,
            f'href="{reverse("accounts:login")}" aria-current="page">Sign in</a>',
        )
