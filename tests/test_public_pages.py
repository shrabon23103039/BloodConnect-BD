from django.test import TestCase
from django.urls import reverse


class PublicPageTests(TestCase):
    def test_public_404_page_uses_safe_shared_error_shell(self):
        response = self.client.get("/definitely-not-a-real-page/")

        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "This page is not available", status_code=404)
        self.assertContains(response, "Error 404", status_code=404)
        self.assertContains(response, 'class="public-auth-card"', status_code=404)

    def test_public_information_routes_render(self):
        for route in ("home", "how_it_works", "privacy", "safety", "terms", "contact"):
            with self.subTest(route=route):
                response = self.client.get(reverse(route))
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response["Content-Type"], "text/html; charset=utf-8")
                self.assertContains(response, 'name="viewport"')
                self.assertContains(response, "Skip to main content")
                self.assertContains(response, "vendor/bootstrap/bootstrap.min.css")

    def test_safety_page_sets_medical_and_emergency_boundaries(self):
        response = self.client.get(reverse("safety"))

        self.assertContains(
            response,
            "Medical suitability and compatibility must be assessed by an authorized healthcare professional.",
        )
        self.assertContains(response, "Not an emergency service.")
        self.assertContains(response, "cannot provide urgent medical help")
        self.assertContains(response, "Availability is self-reported")

    def test_privacy_page_describes_consent_gated_contact_and_draft_status(self):
        response = self.client.get(reverse("privacy"))

        self.assertContains(response, "not a final legal privacy notice")
        self.assertContains(response, "must explicitly accept")
        self.assertContains(response, "must not appear in public results")
        self.assertContains(response, "no real donor data should be entered")

    def test_home_discloses_registration_and_search_status(self):
        response = self.client.get(reverse("home"))

        self.assertContains(response, "Discovery workflows are implemented")
        self.assertContains(response, "Reviewed Bangladesh location data is not yet loaded")
        self.assertContains(response, reverse("accounts:register"))
        self.assertNotContains(response, 'href="/donors/"')

    def test_home_preserves_consent_safety_copy_and_navigation(self):
        response = self.client.get(reverse("home"))

        for text in (
            "Community-led donor discovery",
            "Make it easier",
            "potential donor.",
            "See how it works",
            "Read the safety guidance",
            "Reviewed Bangladesh location data is not yet loaded.",
            "Consent comes first",
            "Your details stay private until you choose to connect.",
            "Three steps to start a conversation",
            "Find potential donors",
            "Request contact",
            "The donor decides",
            "Potential contacts, not medical advice",
            "Read all safety guidance",
        ):
            self.assertContains(response, text)

        for route_name in (
            "how_it_works",
            "safety",
            "privacy",
            "donors:search",
            "accounts:login",
            "accounts:register",
        ):
            self.assertContains(response, f'href="{reverse(route_name)}"')

        self.assertContains(response, 'class="landing-page"')
        self.assertContains(response, "Skip to main content")

    def test_site_styles_include_mobile_layout_and_reduced_motion(self):
        with open("static/css/site.css", encoding="utf-8") as stylesheet:
            css = stylesheet.read()

        self.assertIn("@media (min-width: 992px)", css)
        self.assertIn("@media (prefers-reduced-motion: reduce)", css)
        self.assertIn("--color-primary-700: #9f1d20", css)
