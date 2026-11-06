from django.test import TestCase
from django.urls import reverse


class PublicPageTests(TestCase):
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

    def test_home_does_not_claim_search_or_registration_is_live(self):
        response = self.client.get(reverse("home"))

        self.assertContains(response, "Donor discovery and account registration are not available")
        self.assertNotContains(response, 'href="/donors/"')
        self.assertNotContains(response, 'href="/accounts/register/"')

    def test_site_styles_include_mobile_layout_and_reduced_motion(self):
        with open("static/css/site.css", encoding="utf-8") as stylesheet:
            css = stylesheet.read()

        self.assertIn("@media (min-width: 992px)", css)
        self.assertIn("@media (prefers-reduced-motion: reduce)", css)
        self.assertIn("--color-primary-700: #9f1d20", css)
