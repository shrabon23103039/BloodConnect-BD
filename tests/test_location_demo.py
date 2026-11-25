from django.test import TestCase, override_settings
from django.urls import reverse


class LocationDemoTests(TestCase):
    @override_settings(DEBUG=True, GOOGLE_MAPS_BROWSER_API_KEY="")
    def test_demo_renders_without_a_browser_key(self):
        response = self.client.get(reverse("location_demo"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "GOOGLE_MAPS_BROWSER_API_KEY")
        self.assertContains(response, "Use my location")
        self.assertContains(response, "Confirm this location")
        self.assertContains(response, "Clear selection")
        self.assertContains(response, "static/js/location_picker.js")
        self.assertContains(response, "static/css/location_picker.css")
        self.assertNotContains(response, "maps.googleapis.com/maps/api/js")
        self.assertNotContains(response, "<form")

    @override_settings(DEBUG=True, GOOGLE_MAPS_BROWSER_API_KEY="synthetic-restricted-browser-key")
    def test_demo_renders_configured_browser_key_for_client_loader(self):
        response = self.client.get(reverse("location_demo"))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('data-google-maps-api-key="synthetic-restricted-browser-key"', content)
        self.assertEqual(content.count("synthetic-restricted-browser-key"), 1)
        self.assertContains(response, "data-location-picker")

    @override_settings(DEBUG=True)
    def test_demo_rejects_non_get_requests(self):
        response = self.client.post(reverse("location_demo"), data={"latitude": "23.8"})

        self.assertEqual(response.status_code, 405)

    @override_settings(DEBUG=False, GOOGLE_MAPS_BROWSER_API_KEY="must-not-be-rendered")
    def test_demo_is_unavailable_outside_development(self):
        response = self.client.get(reverse("location_demo"))

        self.assertEqual(response.status_code, 404)
        self.assertNotContains(response, "must-not-be-rendered", status_code=404)
