"""Real Chromium coverage for location selectors using synthetic locations only."""

import json
from datetime import timedelta
from urllib.parse import parse_qs, urlparse

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from playwright.sync_api import expect, sync_playwright

from apps.accounts.models import AccountStatus
from apps.donors.models import (
    AvailabilityStatus,
    BloodGroup,
    DonorProfile,
    DonorProfileStatus,
    PreferredContactMethod,
)
from apps.governance.models import ConsentType, record_consent
from apps.locations.models import Location, LocationLevel
from apps.requests.models import BloodRequest


User = get_user_model()
PASSWORD = "Synthetic-Browser-Password!947"


def make_location(name, level, parent=None):
    return Location.objects.create(
        name_en=name,
        level=level,
        parent=parent,
        source_name="Synthetic browser fixture",
        source_version="browser-test-v1",
    )


def make_hierarchy():
    branches = []
    for suffix in ("A", "B"):
        division = make_location(f"Synthetic Division {suffix}", LocationLevel.DIVISION)
        district = make_location(
            f"Synthetic District {suffix}", LocationLevel.DISTRICT, division
        )
        upazila = make_location(
            f"Synthetic Upazila {suffix}", LocationLevel.UPAZILA, district
        )
        branches.append((division, district, upazila))
    return branches


def make_active_user(email, display_name):
    user = User.objects.create_user(
        email=email, password=PASSWORD, display_name=display_name
    )
    user.account_status = AccountStatus.ACTIVE
    user.email_verified_at = timezone.now()
    user.save(update_fields=["account_status", "email_verified_at", "updated_at"])
    return user


def login(page, live_server, email):
    page.goto(f"{live_server.url}{reverse('accounts:login')}")
    page.locator("input[name='username']").fill(email)
    page.locator("input[name='password']").fill(PASSWORD)
    page.get_by_role("button", name="Sign in").click()
    desktop_navigation = page.get_by_role("complementary", name="Application navigation")
    expect(desktop_navigation.get_by_role("button", name="Sign out")).to_be_visible()


@pytest.mark.django_db(transaction=True)
def test_blood_request_create_form_renders_responsively_without_overflow(live_server):
    user = make_active_user("request-form-layout@example.test", "Synthetic Requester")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.set_default_timeout(8_000)
        login(page, live_server, user.email)
        page.goto(f"{live_server.url}{reverse('requests:create')}")

        expect(page.get_by_role("heading", name="Create blood request")).to_be_visible()
        expect(page.get_by_role("navigation", name="Breadcrumb")).to_be_visible()
        form = page.locator("form[data-location-picker]")
        expect(form.locator("input[name='csrfmiddlewaretoken']")).to_have_count(1)
        expect(form.locator("select[name='blood_group']")).to_have_attribute("required", "")
        expect(form.locator("input[name='units_requested']")).to_have_attribute("required", "")
        expect(form.locator("input[name='required_at']")).to_have_attribute("required", "")
        expect(form.locator("select[name='urgency']")).to_have_attribute("required", "")
        expect(form.locator("[data-role='location-input']")).to_be_visible()
        expect(form.locator("[data-role='map']")).to_be_visible()
        assert form.locator("[data-role='map']").evaluate(
            "(element) => element.getBoundingClientRect().height"
        ) <= 130
        expect(form.locator("[data-role='confirm-location']")).to_be_disabled()
        expect(form.locator("textarea[name='description']")).to_be_visible()
        expect(page.get_by_text("Additional information", exact=True)).to_be_visible()
        expect(form.locator("input[name='facility_name']")).to_have_count(1)
        expect(form.locator("input[name='facility_address']")).to_have_count(1)
        expect(form.locator("input[name='expires_at']")).to_have_count(1)
        expect(form.locator("input[name='public_listing_enabled']")).to_have_count(1)
        expect(page.get_by_role("link", name="Cancel")).to_have_attribute(
            "href", reverse("requests:list")
        )
        expect(form.locator("button[name='action'][value='draft']")).to_be_visible()
        expect(form.locator("button[name='action'][value='publish']")).to_be_visible()
        expect(page.locator('link[href*="css/request_form.css"]')).to_have_count(1)
        assert "linear-gradient" in page.locator(".request-create-hero").evaluate(
            "(element) => getComputedStyle(element).backgroundImage"
        )
        desktop_fields = page.evaluate(
            """() => {
              const form = document.querySelector(".request-create-form");
              const field = (name) => form.querySelector(`[name="${name}"]`)
                .closest(".request-create-field").getBoundingClientRect();
              const blood = field("blood_group");
              const location = form.querySelector(".request-create-field--location")
                .getBoundingClientRect();
              const units = field("units_requested");
              const urgency = field("urgency");
              const needed = field("required_at");
              return {
                bloodTop: blood.top,
                locationTop: location.top,
                unitsTop: units.top,
                urgencyTop: urgency.top,
                neededTop: needed.top,
              };
            }"""
        )
        assert abs(desktop_fields["bloodTop"] - desktop_fields["locationTop"]) < 1
        assert abs(desktop_fields["unitsTop"] - desktop_fields["urgencyTop"]) < 1
        assert desktop_fields["neededTop"] > desktop_fields["urgencyTop"]

        for width in (320, 375, 390, 414, 480, 768, 1024, 1280, 1440, 1920):
            page.set_viewport_size({"width": width, "height": 1000})
            dimensions = page.evaluate(
                """() => ({
                  viewport: document.documentElement.clientWidth,
                  page: document.documentElement.scrollWidth,
                  formRight: document.querySelector(".request-create-form")
                    .getBoundingClientRect().right,
                })"""
            )
            assert dimensions["page"] <= dimensions["viewport"], (
                f"Horizontal overflow at {width}px: {dimensions}"
            )
            assert dimensions["formRight"] <= dimensions["viewport"] + 1, (
                f"Form clipped at {width}px: {dimensions}"
            )
            assert page.locator("[data-role='map']").evaluate(
                "(element) => element.getBoundingClientRect().height"
            ) <= 130
        browser.close()

    assert BloodRequest.objects.filter(requester=user).count() == 0


@pytest.mark.django_db(transaction=True)
def test_profile_area_picker_login_csrf_and_owner_save(live_server):
    user = make_active_user("profile-selector@example.test", "Synthetic Profile")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.set_default_timeout(8_000)
        login(page, live_server, user.email)
        page.goto(f"{live_server.url}{reverse('donors:profile')}")

        form = page.locator("form[data-location-picker]")
        expect(form.locator("input[name='csrfmiddlewaretoken']")).to_have_count(1)
        expect(form.locator("select[name='blood_group']")).to_have_attribute("required", "")
        expect(page.locator("label[for='id_blood_group'] .profile-required-indicator")).to_have_text("*")
        expect(form.locator("input[name='share_email_after_accept']")).to_have_attribute(
            "aria-describedby", "profile-contact-help"
        )
        expect(page.get_by_role("heading", name="Blood & location")).to_be_visible()
        expect(form.locator("select[name='division']")).to_have_count(0)
        expect(form.locator("select[name='district']")).to_have_count(0)
        expect(form.locator("[data-role='use-my-location']")).to_have_count(0)
        expect(form.locator("[data-role='empty-state']")).to_be_visible()
        form.locator("input[name='csrfmiddlewaretoken']").evaluate("element => element.remove()")
        with page.expect_navigation(wait_until="load") as csrf_navigation:
            form.evaluate("element => element.requestSubmit()")
        assert csrf_navigation.value.status == 403

        page.goto(f"{live_server.url}{reverse('donors:profile')}")
        form = page.locator("form[data-location-picker]")
        form.locator("select[name='blood_group']").select_option(BloodGroup.O_POSITIVE)
        form.locator("select[name='availability_status']").select_option(
            AvailabilityStatus.AVAILABLE
        )
        form.locator("select[name='preferred_contact_method']").select_option(
            PreferredContactMethod.IN_APP
        )
        form.locator("input[name='visibility_enabled']").check()
        form.locator("input[name='public_alias']").fill("Synthetic Browser Donor")

        def set_hidden(name, value):
            form.locator(f"input[name='{name}']").evaluate(
                "(element, value) => { element.value = value; }",
                value,
            )

        set_hidden("donation_area_label", "Synthetic General Area")
        set_hidden("donation_area_latitude", "23.74650000")
        set_hidden("donation_area_longitude", "90.37600000")
        set_hidden("google_place_id", "synthetic-browser-place")
        set_hidden("location_source", "GOOGLE_PLACE")
        set_hidden("location_confirmed", "on")
        form.locator("input[name='store_donation_area']").check()
        form.get_by_role("button", name="Save profile").click()
        expect(page.get_by_text("Your donor profile has been saved", exact=False)).to_be_visible()
        browser.close()

    profile = DonorProfile.objects.get(user=user)
    assert profile.donation_area_label == "Synthetic General Area"
    assert str(profile.donation_area_latitude) == "23.74650000"
    assert str(profile.donation_area_longitude) == "90.37600000"
    assert profile.google_place_id == "synthetic-browser-place"
    assert profile.location_source == "GOOGLE_PLACE"
    assert profile.location_confirmed_at is not None
    assert profile.division_id is None
    assert profile.district_id is None


@pytest.mark.django_db(transaction=True)
def test_donor_profile_form_matches_responsive_workspace_layout(live_server, tmp_path):
    user = make_active_user("profile-layout@example.test", "Synthetic Profile Layout")
    widths = (320, 375, 390, 414, 480, 768, 1024, 1280, 1366, 1440, 1920)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.set_default_timeout(8_000)
        login(page, live_server, user.email)
        page.goto(f"{live_server.url}{reverse('donors:profile')}")
        expect(page.get_by_role("heading", name="Create Donor Profile")).to_be_visible()
        expect(page.get_by_role("heading", name="Quick tips")).to_be_visible()
        expect(page.get_by_role("status").filter(has_text="Map search is unavailable right now.")).to_be_visible()
        expect(page.get_by_text("GOOGLE_MAPS_BROWSER_API_KEY")).to_have_count(0)
        expect(page.get_by_role("link", name="Back to Find Donors")).to_have_attribute(
            "href", reverse("donors:search")
        )
        expect(page.get_by_role("link", name="Cancel")).to_have_attribute(
            "href", reverse("donors:profile")
        )
        expect(page.get_by_role("button", name="Save Profile")).to_be_visible()
        expect(page.locator(".app-sidebar .app-nav-link[aria-current='page']")).to_have_text(
            "Donor profile"
        )
        for width in widths:
            page.set_viewport_size({"width": width, "height": 1000})
            dimensions = page.evaluate(
                "({viewport: innerWidth, page: document.documentElement.scrollWidth})"
            )
            assert dimensions["page"] <= dimensions["viewport"], (
                f"Profile editor overflows at {width}px: {dimensions}"
            )
            heading_sizes = page.locator(".profile-card-heading h2").evaluate_all(
                "elements => elements.map(element => parseFloat(getComputedStyle(element).fontSize))"
            )
            assert all(size >= (19 if width <= 520 else 22) for size in heading_sizes), (
                f"Section heading is too small at {width}px: {heading_sizes}"
            )
            action_heights = page.locator(".profile-form-actions .btn").evaluate_all(
                "elements => elements.map(element => element.getBoundingClientRect().height)"
            )
            assert all(height >= 44 for height in action_heights), (
                f"Profile action is too small at {width}px: {action_heights}"
            )
            assert page.locator("[data-role='confirm-location']").evaluate(
                "element => element.getBoundingClientRect().height"
            ) >= 44, f"Location confirmation target is too small at {width}px"
            card_edges = page.locator(".profile-form-card").evaluate_all(
                "elements => elements.map(element => element.getBoundingClientRect().right)"
            )
            assert all(right <= width + 1 for right in card_edges), (
                f"Profile card is clipped at {width}px: {card_edges}"
            )
            if width in {390, 1440}:
                page.screenshot(
                    path=str(tmp_path / f"donor-profile-{width}.png"),
                    full_page=True,
                )
        browser.close()


@pytest.mark.django_db(transaction=True)
@override_settings(DEBUG=True, GOOGLE_MAPS_BROWSER_API_KEY="synthetic-browser-key")
def test_donor_profile_uses_places_and_pin_coordinates_without_geocoding(live_server):
    user = make_active_user("places-profile@example.test", "Synthetic Places Profile")
    maps_script = """
      (() => {
        const state = window.__locationPickerTest = {
          libraries: [],
          geocoderCalls: 0,
          requestedFields: [],
          selectedPlace: {lat: 23.7465, lng: 90.3760},
          mapCenter: null,
        };
        class MockMap {
          constructor(element, options) {
            this.zoom = options.zoom;
            state.mapCenter = options.center;
          }
          addListener(name, callback) {
            if (name === "click") state.mapClick = callback;
          }
          panTo(point) { state.mapCenter = point; }
          setCenter(point) { state.mapCenter = point; }
          setZoom(zoom) { this.zoom = zoom; }
          getZoom() { return this.zoom; }
        }
        class MockMarker {
          addListener(name, callback) {
            if (name === "dragend") state.dragMarker = callback;
          }
          setPosition(point) { state.markerPosition = point; }
          setMap(map) { state.markerMap = map; }
        }
        const suggestion = {
          placePrediction: {
            text: {toString: () => "Dhanmondi, Dhaka"},
            toPlace: () => ({
              async fetchFields({fields}) {
                state.requestedFields = fields;
                this.formattedAddress = "Dhanmondi, Dhaka";
                this.displayName = {toString: () => "Dhanmondi"};
                this.location = {
                  lat: () => state.selectedPlace.lat,
                  lng: () => state.selectedPlace.lng,
                };
                this.addressComponents = [{longText: "Dhanmondi", types: ["neighborhood"]}];
                this.types = ["neighborhood"];
                this.id = "synthetic-place-id";
              },
            }),
          },
        };
        const sessionToken = class {};
        window.google = {
          maps: {
            Marker: MockMarker,
            event: {trigger() {}},
            async importLibrary(name) {
              state.libraries.push(name);
              if (name === "maps") return {Map: MockMap};
              if (name === "places") {
                return {
                  AutocompleteSessionToken: sessionToken,
                  AutocompleteSuggestion: {
                    async fetchAutocompleteSuggestions({input}) {
                      state.query = input;
                      return {suggestions: [suggestion]};
                    },
                  },
                };
              }
              if (name === "geocoding") {
                return {
                  Geocoder: class {
                    async geocode() {
                      state.geocoderCalls += 1;
                      throw new Error("Geocoding must not be used by donor profiles");
                    }
                  },
                };
              }
              throw new Error(`Unexpected Maps library: ${name}`);
            },
          },
        };
        window.initBloodConnectLocationPicker();
      })();
    """
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.set_default_timeout(8_000)
        page.route(
            "https://maps.googleapis.com/maps/api/js**",
            lambda route: route.fulfill(
                status=200,
                content_type="application/javascript",
                body=maps_script,
            ),
        )
        login(page, live_server, user.email)
        page.goto(f"{live_server.url}{reverse('donors:profile')}")

        form = page.locator("form[data-location-picker]")
        search = form.locator("[data-role='location-input']")
        search.fill("Dhanmondi")
        page.get_by_role("button", name="Search").click()
        suggestion_option = page.get_by_role("option", name="Dhanmondi, Dhaka")
        expect(suggestion_option).to_be_visible()
        suggestion_option.click()
        expect(form.locator("[data-role='confirm-location']")).to_be_enabled()
        expect(search).to_have_value("Dhanmondi")
        expect(form.locator("[data-role='map']")).to_be_visible()
        expect(form.locator("input[name='donation_area_latitude']")).to_have_value("")
        expect(form.locator("input[name='donation_area_longitude']")).to_have_value("")
        expect(form.locator("input[name='location_confirmed']")).to_have_value("false")
        page.get_by_role("button", name="Confirm donation area").click()

        expect(form.locator("input[name='donation_area_label']")).to_have_value("Dhanmondi")
        expect(form.locator("input[name='donation_area_latitude']")).to_have_value("23.74650000")
        expect(form.locator("input[name='donation_area_longitude']")).to_have_value("90.37600000")
        expect(form.locator("input[name='google_place_id']")).to_have_value("synthetic-place-id")
        expect(form.locator("input[name='location_source']")).to_have_value("GOOGLE_PLACE")
        expect(form.locator("input[name='location_confirmed']")).to_have_value("true")
        expect(form.locator("input[name='store_donation_area']")).not_to_be_checked()

        page.evaluate(
            """() => window.__locationPickerTest.dragMarker({
              latLng: {lat: () => 23.751, lng: () => 90.381},
            })"""
        )
        expect(form.locator("input[name='donation_area_latitude']")).to_have_value("23.74650000")
        expect(form.locator("input[name='location_source']")).to_have_value("GOOGLE_PLACE")
        page.get_by_role("button", name="Confirm donation area").click()
        expect(form.locator("input[name='donation_area_label']")).to_have_value("Adjusted donation area")
        expect(form.locator("input[name='donation_area_latitude']")).to_have_value("23.75100000")
        expect(form.locator("input[name='donation_area_longitude']")).to_have_value("90.38100000")
        expect(form.locator("input[name='google_place_id']")).to_have_value("")
        expect(form.locator("input[name='location_source']")).to_have_value("MAP_PIN")
        expect(form.locator("input[name='location_confirmed']")).to_have_value("true")

        state = page.evaluate("() => window.__locationPickerTest")
        assert state["query"] == "Dhanmondi"
        assert {"formattedAddress", "displayName", "location"} <= set(state["requestedFields"])
        assert "places" in state["libraries"]
        assert "geocoding" not in state["libraries"]
        assert state["geocoderCalls"] == 0
        assert state["mapCenter"] == {"lat": 23.751, "lng": 90.381}
        browser.close()


@pytest.mark.django_db(transaction=True)
@override_settings(DEBUG=True, GOOGLE_MAPS_BROWSER_API_KEY="synthetic-browser-key")
def test_blood_request_uses_places_confirmed_area_without_geocoding(live_server):
    user = make_active_user("request-places@example.test", "Synthetic Requester")
    maps_script = """
      (() => {
        const state = window.__requestLocationTest = {
          libraries: [],
          geocoderCalls: 0,
          requestedFields: [],
          mapCenter: null,
        };
        class MockMap {
          constructor(element, options) {
            this.zoom = options.zoom;
            state.mapCenter = options.center;
          }
          addListener(name, callback) {
            if (name === "click") state.mapClick = callback;
          }
          panTo(point) { state.mapCenter = point; }
          setCenter(point) { state.mapCenter = point; }
          setZoom(zoom) { this.zoom = zoom; }
          getZoom() { return this.zoom; }
        }
        class MockMarker {
          addListener(name, callback) {
            if (name === "dragend") state.dragMarker = callback;
          }
          setPosition(point) { state.markerPosition = point; }
          setMap(map) { state.markerMap = map; }
        }
        const suggestion = {
          placePrediction: {
            text: {toString: () => "Synthetic Hospital, Synthetic City"},
            toPlace: () => ({
              async fetchFields({fields}) {
                state.requestedFields = fields;
                this.formattedAddress = "Private synthetic formatted address";
                this.displayName = {toString: () => "Synthetic Hospital"};
                this.location = {
                  lat: () => 23.7465,
                  lng: () => 90.3760,
                };
                this.addressComponents = [{
                  longText: "Synthetic General Area",
                  types: ["neighborhood"],
                }];
                this.types = ["hospital"];
                this.id = "synthetic-private-place-id";
              },
            }),
          },
        };
        window.google = {
          maps: {
            Marker: MockMarker,
            event: {trigger() {}},
            async importLibrary(name) {
              state.libraries.push(name);
              if (name === "maps") return {Map: MockMap};
              if (name === "places") {
                return {
                  AutocompleteSessionToken: class {},
                  AutocompleteSuggestion: {
                    async fetchAutocompleteSuggestions({input}) {
                      state.query = input;
                      return {suggestions: [suggestion]};
                    },
                  },
                };
              }
              if (name === "geocoding") {
                return {
                  Geocoder: class {
                    async geocode() {
                      state.geocoderCalls += 1;
                      throw new Error("Request picker must not use Geocoding");
                    }
                  },
                };
              }
              throw new Error(`Unexpected Maps library: ${name}`);
            },
          },
        };
        window.initBloodConnectLocationPicker();
      })();
    """
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.set_default_timeout(8_000)
        page.route(
            "https://maps.googleapis.com/maps/api/js**",
            lambda route: route.fulfill(
                status=200,
                content_type="application/javascript",
                body=maps_script,
            ),
        )
        login(page, live_server, user.email)
        page.goto(f"{live_server.url}{reverse('requests:create')}")

        form = page.locator("form[data-location-picker]")
        expect(page.get_by_role("heading", name="Request location")).to_be_visible()
        expect(form.locator("select[name='division']")).to_have_count(0)
        expect(form.locator("select[name='district']")).to_have_count(0)
        expect(form.locator("[data-role='use-my-location']")).to_have_count(0)
        form.locator("select[name='blood_group']").select_option("A+")
        form.locator("input[name='units_requested']").fill("1")
        form.locator("input[name='required_at']").fill(
            (timezone.now() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M")
        )
        form.locator("select[name='urgency']").select_option("NORMAL")
        page.get_by_text(
            "Optional facility details and request settings", exact=True
        ).click()
        form.locator("input[name='facility_name']").fill("Synthetic hospital text")
        form.locator("input[name='facility_address']").fill("Synthetic directions text")

        search = form.locator("[data-role='location-input']")
        search.fill("Synthetic Hospital")
        search.press("Enter")
        suggestion_option = page.get_by_role(
            "option", name="Synthetic Hospital, Synthetic City"
        )
        expect(suggestion_option).to_be_visible()
        suggestion_option.click()
        expect(form.locator("[data-role='confirm-location']")).to_be_enabled()
        expect(form.locator("input[name='request_location_latitude']")).to_have_value("")
        expect(search).to_have_value("Private synthetic formatted address")
        expect(page.get_by_text("Private synthetic formatted address")).to_have_count(0)

        page.evaluate(
            """() => window.__requestLocationTest.dragMarker({
              latLng: {lat: () => 23.751, lng: () => 90.381},
            })"""
        )
        page.get_by_role("button", name="Confirm request location").click()
        expect(form.locator("input[name='request_location_label']")).to_have_value(
            "Synthetic General Area"
        )
        expect(form.locator("input[name='request_location_latitude']")).to_have_value(
            "23.75100000"
        )
        expect(form.locator("input[name='request_location_longitude']")).to_have_value(
            "90.38100000"
        )
        expect(form.locator("input[name='request_location_place_id']")).to_have_value("")
        expect(form.locator("input[name='request_location_source']")).to_have_value("MAP_PIN")
        expect(form.locator("input[name='request_location_confirmed']")).to_have_value("true")
        expect(form.locator("[data-role='confirmed-address']")).to_have_text(
            "Synthetic General Area"
        )

        state = page.evaluate("() => window.__requestLocationTest")
        assert state["query"] == "Synthetic Hospital"
        assert {"formattedAddress", "displayName", "location"} <= set(state["requestedFields"])
        assert "places" in state["libraries"]
        assert "geocoding" not in state["libraries"]
        assert state["geocoderCalls"] == 0
        assert state["mapCenter"] == {"lat": 23.751, "lng": 90.381}

        page.get_by_role("button", name="Create request").click()
        expect(page.get_by_text("Synthetic General Area")).to_be_visible()
        expect(page.get_by_text("Synthetic hospital text")).to_be_visible()
        expect(page.get_by_text("Synthetic directions text")).to_be_visible()
        expect(page.get_by_text("23.75100000")).to_have_count(0)
        browser.close()

    from apps.requests.models import BloodRequest

    request = BloodRequest.objects.get(requester=user)
    assert request.request_location_label == "Synthetic General Area"
    assert str(request.request_location_latitude) == "23.75100000"
    assert str(request.request_location_longitude) == "90.38100000"
    assert request.request_location_place_id == ""
    assert request.request_location_source == "MAP_PIN"
    assert request.request_location_confirmed_at is not None
    assert request.facility_name == "Synthetic hospital text"
    assert request.facility_address == "Synthetic directions text"


@pytest.mark.django_db(transaction=True)
def test_donor_search_list_and_location_map_preview_toggle(live_server):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.set_default_timeout(8_000)
        page.goto(f"{live_server.url}{reverse('donors:search')}")

        results = page.locator("[data-results-panel='list']")
        map_panel = page.locator("[data-results-panel='map']")
        expect(results).to_be_visible()
        expect(map_panel).to_be_visible()
        page.get_by_role("button", name="Map view").click()
        expect(map_panel).to_be_visible()
        expect(results).to_be_visible()
        expect(page.locator("[data-results-layout]")).to_have_class(
            "donor-search__results-stage is-map-view"
        )
        expect(page.get_by_role("button", name="List view")).to_have_attribute("aria-pressed", "false")
        expect(page.get_by_role("button", name="Map view")).to_have_attribute("aria-pressed", "true")
        page.get_by_role("button", name="List view").click()
        expect(results).to_be_visible()
        expect(map_panel).to_be_visible()
        expect(page.locator("[data-results-layout]")).not_to_have_class(
            "donor-search__results-stage is-map-view"
        )
        expect(page.get_by_text("Donor locations are not plotted.", exact=False)).to_be_attached()

        browser.close()


@pytest.mark.django_db(transaction=True)
def test_finder_selectors_filter_synthetic_donor(live_server):
    (division, district, upazila), _ = make_hierarchy()
    donor_user = make_active_user("finder-selector@example.test", "Synthetic Finder Donor")
    DonorProfile.objects.create(
        user=donor_user,
        blood_group=BloodGroup.O_POSITIVE,
        division=division,
        district=district,
        upazila=upazila,
        availability_status=AvailabilityStatus.AVAILABLE,
        visibility_enabled=True,
        profile_status=DonorProfileStatus.ACTIVE,
        public_alias="Synthetic Finder Result",
        preferred_contact_method=PreferredContactMethod.IN_APP,
    )
    record_consent(
        user=donor_user,
        consent_type=ConsentType.DONOR_DISCOVERY,
        policy_version="browser-test-v1",
        granted=True,
    )

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.set_default_timeout(8_000)
        page.route(
            "**/app/location-options/options/CITY_CORPORATION/**",
            lambda route: route.fulfill(
                status=200,
                content_type="application/json",
                body='{"results":[]}',
            ),
        )
        page.goto(f"{live_server.url}{reverse('donors:search')}")
        page.locator("details.donor-search__advanced > summary").click()
        form = page.locator("form[data-location-options-url]")
        form.locator("select[name='division']").select_option(str(division.pk))
        expect(
            form.locator("select[name='district'] option").filter(
                has_text=district.name_en
            )
        ).to_have_count(1)
        form.locator("select[name='district']").select_option(str(district.pk))
        expect(
            form.locator("select[name='upazila'] option").filter(
                has_text=upazila.name_en
            )
        ).to_have_count(1)
        form.locator("select[name='upazila']").select_option(str(upazila.pk))
        form.locator("select[name='blood_group']").select_option("O+")
        form.get_by_role(
            "button", name="Search donors"
        ).click()
        expect(page.get_by_role("heading", name="Synthetic Finder Result")).to_be_visible()
        browser.close()


@pytest.mark.django_db(transaction=True)
def test_inactive_ancestor_options_and_results_are_hidden(live_server):
    (division, district, _), _ = make_hierarchy()
    donor_user = make_active_user("inactive-ancestor@example.test", "Synthetic Inactive Donor")
    DonorProfile.objects.create(
        user=donor_user,
        blood_group=BloodGroup.O_POSITIVE,
        division=division,
        district=district,
        availability_status=AvailabilityStatus.AVAILABLE,
        visibility_enabled=True,
        profile_status=DonorProfileStatus.ACTIVE,
        public_alias="Must Not Appear",
        preferred_contact_method=PreferredContactMethod.IN_APP,
    )
    record_consent(
        user=donor_user,
        consent_type=ConsentType.DONOR_DISCOVERY,
        policy_version="browser-test-v1",
        granted=True,
    )
    Location.objects.filter(pk=division.pk).update(is_active=False)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.set_default_timeout(8_000)
        page.goto(f"{live_server.url}{reverse('donors:search')}")
        page.locator("details.donor-search__advanced > summary").click()
        form = page.locator("form[data-location-options-url]")
        expect(
            form.locator("select[name='division'] option").filter(
                has_text=division.name_en
            )
        ).to_have_count(0)
        response = page.request.get(
            f"{live_server.url}{reverse('locations:child_options', args=[LocationLevel.UPAZILA])}",
            params={"parent": str(district.pk)},
        )
        assert response.json() == {"results": []}
        page.goto(
            f"{live_server.url}{reverse('donors:search')}?division={division.pk}"
            f"&district={district.pk}"
        )
        expect(page.get_by_role("heading", name="Must Not Appear")).to_have_count(0)
        expect(page.get_by_text("invalid", exact=False)).to_be_visible()
        browser.close()


@pytest.mark.django_db(transaction=True)
def test_finder_empty_options_and_network_failure_announcement(live_server):
    division = make_location("Synthetic Empty Division", LocationLevel.DIVISION)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.set_default_timeout(8_000)
        page.goto(f"{live_server.url}{reverse('donors:search')}")
        page.locator("details.donor-search__advanced > summary").click()
        form = page.locator("form[data-location-options-url]")
        expect(form.locator("select[name='district'] option")).to_have_count(1)

        page.route(
            "**/app/location-options/options/DISTRICT/**",
            lambda route: route.abort("failed"),
        )
        form.locator("select[name='division']").select_option(str(division.pk))
        expect(
            form.locator("[role='status']").filter(
                has_text="Location options are temporarily unavailable"
            )
        ).to_be_visible()
        expect(form.locator("select[name='district'] option")).to_have_count(1)
        browser.close()


@pytest.mark.django_db(transaction=True)
def test_finder_ignores_stale_parent_response(live_server):
    (division_a, district_a, _), (division_b, district_b, _) = make_hierarchy()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.set_default_timeout(8_000)
        page.goto(f"{live_server.url}{reverse('donors:search')}")
        page.locator("details.donor-search__advanced > summary").click()
        form = page.locator("form[data-location-options-url]")
        held_routes = []

        def hold_a_request(route):
            parent_id = parse_qs(urlparse(route.request.url).query).get("parent", [""])[0]
            if parent_id == str(division_a.pk):
                held_routes.append(route)
            else:
                route.continue_()

        page.route("**/app/location-options/options/DISTRICT/**", hold_a_request)
        form.locator("select[name='division']").select_option(str(division_a.pk))
        page.wait_for_function(
            "document.querySelector('#id_district').getAttribute('aria-busy') === 'true'"
        )
        assert len(held_routes) == 1

        form.locator("select[name='division']").select_option(str(division_b.pk))
        district_select = form.locator("select[name='district']")
        expect(district_select).to_contain_text(district_b.name_en)
        held_routes[0].fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({"results": [{"id": str(district_a.pk), "name_en": district_a.name_en}]}),
        )
        expect(district_select).to_contain_text(district_b.name_en)
        expect(district_select.locator("option").filter(has_text=district_a.name_en)).to_have_count(0)
        browser.close()


@pytest.mark.django_db(transaction=True)
def test_finder_nearby_ui_does_not_submit_coordinates_or_radius(live_server):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(geolocation={"latitude": 23.8, "longitude": 90.4})
        context.grant_permissions(["geolocation"])
        page = context.new_page()
        page.set_default_timeout(8_000)
        page.goto(f"{live_server.url}{reverse('donors:search')}")

        page.get_by_role("button", name="Use my location").click()
        expect(page.get_by_role("status").filter(has_text="Device location selected")).to_be_visible()
        page.get_by_role("button", name="Confirm location").click()
        expect(
            page.get_by_role("status").filter(
                has_text="Nearby donor matching is not available yet"
            )
        ).to_be_visible()
        page.get_by_role("button", name="10 km").click()
        expect(page.get_by_role("button", name="10 km")).to_have_attribute("aria-pressed", "true")
        assert page.url.rstrip("/").endswith(reverse("donors:search").rstrip("/"))
        assert "23.8" not in page.url
        assert "90.4" not in page.url
        assert "radius" not in page.url

        page.locator("details.donor-search__advanced > summary").click()
        with page.expect_navigation(wait_until="domcontentloaded"):
            page.get_by_role("button", name="Search donors").click()
        assert "latitude" not in page.url
        assert "longitude" not in page.url
        assert "radius" not in page.url
        assert "hospital" not in page.url
        browser.close()


@pytest.mark.django_db(transaction=True)
def test_finder_keeps_editable_address_input_when_maps_key_is_missing(live_server):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.set_default_timeout(8_000)
        page.goto(f"{live_server.url}{reverse('donors:search')}")

        address = page.get_by_role("combobox", name="Location")
        expect(address).to_be_visible()
        address.fill("Synthetic address, Dhaka")
        page.get_by_role("button", name="Search address", exact=True).click()
        expect(address).to_have_value("Synthetic address, Dhaka")
        expect(
            page.get_by_role("status").filter(
                has_text="Map and address lookup are unavailable"
            )
        ).to_be_visible()
        assert "Synthetic address" not in page.url

        browser.close()


@pytest.mark.django_db(transaction=True)
def test_finder_layout_is_responsive_without_overflow(live_server):
    (division, district, upazila), _ = make_hierarchy()
    requester = make_active_user(
        "responsive-finder-requester@example.test", "Synthetic Finder Requester"
    )
    donor_user = make_active_user(
        "responsive-finder@example.test", "Synthetic Responsive Donor"
    )
    DonorProfile.objects.create(
        user=donor_user,
        blood_group=BloodGroup.O_POSITIVE,
        division=division,
        district=district,
        upazila=upazila,
        availability_status=AvailabilityStatus.AVAILABLE,
        visibility_enabled=True,
        profile_status=DonorProfileStatus.ACTIVE,
        public_alias="Synthetic Responsive Result",
        preferred_contact_method=PreferredContactMethod.IN_APP,
    )
    record_consent(
        user=donor_user,
        consent_type=ConsentType.DONOR_DISCOVERY,
        policy_version="browser-test-v1",
        granted=True,
    )

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.set_default_timeout(8_000)
        login(page, live_server, requester.email)
        page.goto(f"{live_server.url}{reverse('donors:search')}")
        expect(page.locator(".app-topbar-label")).to_contain_text("Your account")
        expect(page.locator(".app-sidebar .app-nav-link.is-active")).to_have_text(
            "Find donors"
        )
        expect(
            page.get_by_role("heading", name="Synthetic Responsive Result")
        ).to_be_visible()
        expect(page.get_by_text("1 potential donor found")).to_be_visible()

        for width in (320, 375, 390, 414, 768, 1024, 1280, 1440, 1920):
            page.set_viewport_size({"width": width, "height": 900})
            if width <= 900:
                expect(page.locator(".app-sidebar")).to_be_hidden()
                expect(
                    page.get_by_role("button", name="Open navigation menu")
                ).to_be_visible()
                if width == 320:
                    page.get_by_role("button", name="Open navigation menu").click()
                    expect(page.locator(".app-mobile-drawer")).to_be_visible()
                    expect(
                        page.locator(
                            ".app-mobile-drawer .app-nav-link.is-active"
                        )
                    ).to_have_text("Find donors")
                    page.get_by_role("button", name="Close navigation").click()
                    expect(page.locator(".app-mobile-drawer")).to_be_hidden()
            else:
                expect(page.locator(".app-sidebar")).to_be_visible()
            page.get_by_role("button", name="Map view").click()
            map_metrics = page.evaluate(
                """() => {
                  const rect = selector => {
                    const element = document.querySelector(selector);
                    const value = element.getBoundingClientRect();
                    return {
                      x: value.x,
                      y: value.y,
                      width: value.width,
                      height: value.height,
                      right: value.right,
                      bottom: value.bottom,
                    };
                  };
                  return {
                    resultsStage: rect(".donor-search__results-stage"),
                    results: rect(".donor-search__results"),
                    mapColumn: rect(".donor-search__map-column"),
                    map: rect(".donor-search__map"),
                    card: rect(".donor-search__result"),
                    mapToggle: rect("[data-results-view='map']"),
                    documentWidth: document.documentElement.scrollWidth,
                    clientWidth: document.documentElement.clientWidth,
                  };
                }"""
            )
            assert 210 <= map_metrics["map"]["height"] <= 860, map_metrics
            assert map_metrics["map"]["width"] > 0, map_metrics
            assert map_metrics["documentWidth"] <= map_metrics["clientWidth"], map_metrics
            assert map_metrics["mapToggle"]["height"] >= 40, map_metrics
            if width >= 992:
                assert abs(map_metrics["results"]["y"] - map_metrics["mapColumn"]["y"]) < 1, map_metrics
                assert map_metrics["results"]["right"] < map_metrics["mapColumn"]["x"], map_metrics
            else:
                assert map_metrics["results"]["bottom"] <= map_metrics["mapColumn"]["y"], map_metrics
            expect(page.get_by_role("button", name="Map view")).to_have_attribute(
                "aria-pressed", "true"
            )

            page.get_by_role("button", name="List view").click()
            expect(page.locator("[data-results-panel='list']")).to_be_visible()
            if width >= 992:
                expect(page.locator("[data-results-panel='map']")).to_be_visible()
            else:
                expect(page.locator("[data-results-panel='map']")).to_be_hidden()
            metrics = page.evaluate(
                """() => {
                  const rect = selector => {
                    const { x, y, width, height, right, bottom } =
                      document.querySelector(selector).getBoundingClientRect();
                    return { x, y, width, height, right, bottom };
                  };
                  return {
                    viewport: window.innerWidth,
                    clientWidth: document.documentElement.clientWidth,
                    documentWidth: document.documentElement.scrollWidth,
                    bodyWidth: document.body.scrollWidth,
                    filters: rect(".donor-search__search-card"),
                    searchPrimary: rect(".donor-search__submit-group .btn-brand"),
                    resultsStage: rect(".donor-search__results-stage"),
                    toolbar: rect(".donor-search__results-toolbar"),
                    resultsPanel: rect("[data-results-panel='list']"),
                    mapPanel: rect("[data-results-panel='map']"),
                    sort: rect(".donor-search__sort"),
                    card: rect(".donor-search__result"),
                    bloodMark: rect(".donor-search__blood-badge"),
                    person: rect(".donor-search__result-person"),
                    actions: rect(".donor-search__result-actions"),
                    contact: rect(".donor-search__result-actions .btn"),
                  };
                }"""
            )
            assert metrics["documentWidth"] <= metrics["clientWidth"], metrics
            assert metrics["bodyWidth"] <= metrics["clientWidth"], metrics
            assert metrics["searchPrimary"]["height"] >= 44, metrics
            assert metrics["sort"]["height"] >= 40, metrics
            assert metrics["resultsPanel"]["width"] > 0, metrics
            if width >= 992:
                assert metrics["mapPanel"]["width"] > 0, metrics
            else:
                assert metrics["mapPanel"]["width"] == 0, metrics
            assert metrics["filters"]["width"] > 0, metrics
            assert metrics["card"]["width"] >= min(300, width - 30), metrics
            assert metrics["contact"]["right"] <= metrics["card"]["right"] + 1, metrics

            if width >= 992:
                assert metrics["bloodMark"]["right"] < metrics["person"]["x"], metrics
                assert metrics["person"]["right"] < metrics["actions"]["x"], metrics

        browser.close()
