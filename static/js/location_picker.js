(() => {
  const roots = document.querySelectorAll("[data-location-picker]");
  roots.forEach(initializeLocationPicker);

  function initializeLocationPicker(root) {
    const find = (name) => root.querySelector(`[data-role="${name}"]`);
    const mapElement = find("map");
    const mapFallback = find("map-fallback");
    const providerStatus = find("provider-status");
    const actionStatus = find("action-status");
    const searchMode = find("search-mode");
    const locationInput = find("location-input");
    const searchAddressButton = find("search-address");
    const suggestionsElement = find("place-suggestions");
    const locationAutocompleteHost = find("location-autocomplete");
    const hospitalAutocompleteHost = find("hospital-autocomplete");
    const hospitalSelection = find("hospital-selection");
    const useHospitalButton = find("use-hospital-location");
    const useLocationButton = find("use-my-location");
    const confirmButton = find("confirm-location");
    const clearButton = find("clear-location");
    const setCoordinateButton = find("set-coordinate-pin");
    const latitudeInput = find("latitude");
    const longitudeInput = find("longitude");
    const confirmedPanel = find("confirmed-location");
    const confirmedAddress = find("confirmed-address");
    const confirmedCoordinates = find("confirmed-coordinates");
    const emptyState = find("empty-state");
    const apiKey = root.dataset.googleMapsApiKey;
    const donorProfileMode = root.dataset.locationPickerMode === "donor-profile";
    const requestLocationMode = root.dataset.locationPickerMode === "blood-request";
    const placesOnlyMode = donorProfileMode || requestLocationMode;
    const donationAreaLabelInput = root.querySelector('[name="donation_area_label"]');
    const donationAreaLatitudeInput = root.querySelector('[name="donation_area_latitude"]');
    const donationAreaLongitudeInput = root.querySelector('[name="donation_area_longitude"]');
    const googlePlaceIdInput = root.querySelector('[name="google_place_id"]');
    const locationSourceInput = root.querySelector('[name="location_source"]');
    const locationConfirmedInput = root.querySelector('[name="location_confirmed"]');
    const storeDonationAreaInput = root.querySelector('[name="store_donation_area"]');
    const requestLocationLabelInput = root.querySelector('[name="request_location_label"]');
    const requestLocationLatitudeInput = root.querySelector('[name="request_location_latitude"]');
    const requestLocationLongitudeInput = root.querySelector('[name="request_location_longitude"]');
    const requestLocationPlaceIdInput = root.querySelector('[name="request_location_place_id"]');
    const requestLocationSourceInput = root.querySelector('[name="request_location_source"]');
    const requestLocationConfirmedInput = root.querySelector('[name="request_location_confirmed"]');

    let map = null;
    let marker = null;
    let radiusCircle = null;
    let geocoder = null;
    let candidate = null;
    let selectedHospital = null;
    let selectionVersion = 0;
    let placeRequestVersion = 0;
    let hospitalRequestVersion = 0;
    let suggestionRequestVersion = 0;
    let addressSearchVersion = 0;
    let mapsAvailable = false;
    let googleScriptStarted = false;
    let autocompleteSuggestionClass = null;
    let autocompleteSessionTokenClass = null;
    let autocompleteSessionToken = null;
    let addressInputInitialized = false;
    let suggestionTimer = null;
    let suggestions = [];
    let activeSuggestionIndex = -1;

    const setStatus = (element, message, kind) => {
      if (!element) return;
      element.textContent = message;
      element.classList.remove("alert", "alert-danger", "alert-warning", "alert-success", "alert-info");
      if (kind) element.classList.add("alert", `alert-${kind}`);
    };

    const asPoint = (latitude, longitude) => {
      if (String(latitude).trim() === "" || String(longitude).trim() === "") return null;
      const lat = Number(latitude);
      const lng = Number(longitude);
      if (!Number.isFinite(lat) || !Number.isFinite(lng) || lat < -90 || lat > 90 || lng < -180 || lng > 180) {
        return null;
      }
      return {lat, lng};
    };

    const formatCoordinate = (value) => Number(value).toFixed(8);

    const generalAreaLabel = (components, fallback, placeTypes = []) => {
      const priority = [
        "neighborhood",
        "sublocality_level_1",
        "sublocality",
        "locality",
        "administrative_area_level_3",
        "administrative_area_level_2",
        "administrative_area_level_1",
      ];
      for (const type of priority) {
        const component = components.find((item) => item.types?.includes(type));
        const label = component?.longText || component?.long_name;
        if (label) return String(label).trim().slice(0, 180);
      }
      const landmarkTypes = new Set([
        "establishment",
        "point_of_interest",
        "hospital",
        "park",
        "university",
        "tourist_attraction",
      ]);
      if (fallback && placeTypes.some((type) => landmarkTypes.has(type))) {
        return String(fallback).trim().slice(0, 180);
      }
      return "";
    };

    const closeSuggestions = () => {
      suggestions = [];
      activeSuggestionIndex = -1;
      if (suggestionsElement) suggestionsElement.replaceChildren();
      if (suggestionsElement) suggestionsElement.hidden = true;
      if (locationInput) {
        locationInput.setAttribute("aria-expanded", "false");
        locationInput.removeAttribute("aria-activedescendant");
      }
    };

    const updateActiveSuggestion = (index) => {
      if (!suggestionsElement || !suggestions.length) return;
      activeSuggestionIndex = (index + suggestions.length) % suggestions.length;
      const options = suggestionsElement.querySelectorAll("[role='option']");
      options.forEach((option, optionIndex) => {
        const active = optionIndex === activeSuggestionIndex;
        option.setAttribute("aria-selected", String(active));
        if (active) {
          locationInput.setAttribute("aria-activedescendant", option.id);
          option.scrollIntoView({block: "nearest"});
        }
      });
    };

    const renderSuggestions = (results) => {
      if (!suggestionsElement || !locationInput) return;
      closeSuggestions();
      suggestions = results
        .map((item) => item.placePrediction)
        .filter(Boolean)
        .slice(0, 6);
      if (!suggestions.length) return;

      suggestions.forEach((prediction, index) => {
        const item = document.createElement("li");
        item.setAttribute("role", "none");
        const option = document.createElement("button");
        option.type = "button";
        option.id = `${root.id}-place-option-${index}`;
        option.setAttribute("role", "option");
        option.setAttribute("aria-selected", "false");
        option.textContent = prediction.text?.toString() || prediction.mainText?.toString() || "Place suggestion";
        option.addEventListener("mousedown", (event) => event.preventDefault());
        option.addEventListener("click", () => selectSuggestion(index));
        item.appendChild(option);
        suggestionsElement.appendChild(item);
      });
      suggestionsElement.hidden = false;
      locationInput.setAttribute("aria-expanded", "true");
    };

    const requestSuggestions = (immediate = false) => {
      if (!locationInput || !autocompleteSuggestionClass || !autocompleteSessionToken) return;
      const query = locationInput.value.trim();
      const requestVersion = ++suggestionRequestVersion;
      window.clearTimeout(suggestionTimer);
      if (query.length < 2) {
        closeSuggestions();
        if (donorProfileMode && query) {
          setStatus(actionStatus, "Enter at least two characters to search Places, or choose a map pin.", "info");
        } else if (requestLocationMode && query) {
          setStatus(actionStatus, "Enter at least two characters to search Places, or choose a map pin.", "info");
        }
        return;
      }
      suggestionTimer = window.setTimeout(async () => {
        try {
          const response = await autocompleteSuggestionClass.fetchAutocompleteSuggestions({
            input: query,
            includedRegionCodes: ["bd"],
            sessionToken: autocompleteSessionToken,
          });
          if (requestVersion !== suggestionRequestVersion || query !== locationInput.value.trim()) return;
          renderSuggestions(response.suggestions || []);
          if (!suggestions.length) {
            setStatus(
              actionStatus,
              donorProfileMode
                ? "No place suggestions found. Try a broader area or choose a map pin."
                : requestLocationMode
                  ? "No place suggestions found. Try a broader area or choose a map pin."
                  : "No place suggestions found. You can still search the typed address.",
              "info",
            );
          }
        } catch {
          if (requestVersion === suggestionRequestVersion) {
            closeSuggestions();
            setStatus(
              actionStatus,
              donorProfileMode
                ? "Place suggestions failed. Check the connection or choose a map pin."
                : requestLocationMode
                  ? "Place suggestions failed. Check the connection or choose a map pin."
                  : "Place suggestions are unavailable. You can still search the typed address.",
              "warning",
            );
          }
        }
      }, immediate ? 0 : 250);
    };

    const reverseGeocodeCandidate = async (point, version) => {
      if (!geocoder) {
        if (version === selectionVersion) {
          setStatus(actionStatus, "Location selected. Address lookup is unavailable; review and confirm the pin.", "warning");
        }
        return;
      }
      try {
        const response = await geocoder.geocode({location: point});
        if (version !== selectionVersion) return;
        const result = response.results?.[0];
        const address = result?.formatted_address;
        if (donorProfileMode) {
          candidate.label = generalAreaLabel(result?.address_components || [], "");
          candidate.placeId = result?.place_id || "";
          if (!candidate.label) {
            setStatus(actionStatus, "No general area name was found. Search for a city, district, area, or nearby landmark.", "warning");
            return;
          }
          if (locationInput) locationInput.value = candidate.label;
          setStatus(actionStatus, "General area found. Review the pin, then confirm the donation area.", "info");
          return;
        }
        if (!address) {
          setStatus(actionStatus, "Location selected; no readable address was found. Review the pin and confirm it.", "warning");
          return;
        }
        candidate.address = address;
        if (locationInput) locationInput.value = address;
        setStatus(actionStatus, "Location selected and address found. Review the pin, then confirm.", "info");
      } catch {
        if (version === selectionVersion) {
          setStatus(actionStatus, "Location selected; address lookup is unavailable. Review the pin and confirm it.", "warning");
        }
      }
    };

    const clearConfirmed = (clearAreaConsent = false) => {
      root.dataset.locationConfirmed = "false";
      if (confirmedPanel) confirmedPanel.hidden = true;
      if (confirmedAddress) confirmedAddress.textContent = "";
      if (confirmedCoordinates) confirmedCoordinates.textContent = "";
      if (donorProfileMode && emptyState) emptyState.hidden = false;
      if (donorProfileMode) {
        if (donationAreaLabelInput) donationAreaLabelInput.value = "";
        if (donationAreaLatitudeInput) donationAreaLatitudeInput.value = "";
        if (donationAreaLongitudeInput) donationAreaLongitudeInput.value = "";
        if (googlePlaceIdInput) googlePlaceIdInput.value = "";
        if (locationSourceInput) locationSourceInput.value = "";
        if (locationConfirmedInput) locationConfirmedInput.value = "false";
        if (clearAreaConsent && storeDonationAreaInput) storeDonationAreaInput.checked = false;
      }
      if (requestLocationMode) {
        if (requestLocationLabelInput) requestLocationLabelInput.value = "";
        if (requestLocationLatitudeInput) requestLocationLatitudeInput.value = "";
        if (requestLocationLongitudeInput) requestLocationLongitudeInput.value = "";
        if (requestLocationPlaceIdInput) requestLocationPlaceIdInput.value = "";
        if (requestLocationSourceInput) requestLocationSourceInput.value = "";
        if (requestLocationConfirmedInput) requestLocationConfirmedInput.value = "false";
      }
    };

    const updateRadiusPreview = () => {
      if (!map || !candidate) return;
      const selectedRadius = root.querySelector("[data-radius][aria-pressed='true']");
      if (!selectedRadius) {
        if (radiusCircle) radiusCircle.setMap(null);
        return;
      }
      const radiusKm = Number(selectedRadius.dataset.radius);
      if (!Number.isFinite(radiusKm) || radiusKm <= 0) return;
      if (!radiusCircle) {
        radiusCircle = new google.maps.Circle({
          clickable: false,
          fillColor: "#B4232A",
          fillOpacity: 0.08,
          strokeColor: "#B4232A",
          strokeOpacity: 0.7,
          strokeWeight: 2,
        });
      }
      radiusCircle.setCenter(candidate.point);
      radiusCircle.setRadius(radiusKm * 1000);
      radiusCircle.setMap(map);
    };

    const setCandidate = (point, address, metadata = {}) => {
      selectionVersion += 1;
      candidate = {
        point,
        address: address || "",
        label: metadata.label || "",
        placeId: metadata.placeId || "",
        source: metadata.source || "MAP_PIN",
      };
      if (
        requestLocationMode
        || !donorProfileMode && root.dataset.locationConfirmed !== "true"
      ) clearConfirmed();
      if (donorProfileMode && emptyState) emptyState.hidden = true;
      closeSuggestions();
      if (locationInput) {
        locationInput.value = donorProfileMode
          ? candidate.label || candidate.address
          : candidate.address;
      }
      if (confirmButton) confirmButton.disabled = false;
      if (latitudeInput) latitudeInput.value = String(point.lat);
      if (longitudeInput) longitudeInput.value = String(point.lng);
      if (map && marker) {
        marker.setPosition(point);
        marker.setMap(map);
        map.panTo(point);
        map.setZoom(Math.max(map.getZoom(), 14));
      }
      updateRadiusPreview();
      setStatus(
        actionStatus,
        requestLocationMode && candidate.source === "MAP_PIN"
          ? "Pin adjusted. The area label is not a verified street address; confirm the selected point."
          : requestLocationMode
            ? "Place selected. Review the pin and confirm the request location."
            : "Location selected. Review the pin, then confirm.",
        null,
      );
      if (!placesOnlyMode && !candidate.address) {
        reverseGeocodeCandidate(point, selectionVersion);
      }
    };

    const showGpsError = (error) => {
      const messages = {
        1: "Location permission was denied. Allow it in your browser settings or choose a place or map pin.",
        2: "Your device could not determine a location. Try again or choose a place or map pin.",
        3: "The location request timed out. Try again or choose a place or map pin.",
      };
      setStatus(
        actionStatus,
        messages[error.code] || "Browser location is unavailable. Choose a place or map pin instead.",
        "warning",
      );
    };

    const requestDeviceLocation = () => {
      if (!navigator.geolocation) {
        setStatus(actionStatus, "This browser does not support location access. Choose a place or map pin.", "warning");
        return;
      }
      const requestVersion = selectionVersion;
      useLocationButton.disabled = true;
      setStatus(actionStatus, "Requesting your device location…", null);
      navigator.geolocation.getCurrentPosition(
        (position) => {
          const point = asPoint(position.coords.latitude, position.coords.longitude);
          useLocationButton.disabled = false;
          if (requestVersion !== selectionVersion) return;
          if (!point) {
            setStatus(actionStatus, "Your browser returned an invalid location. Choose a place or map pin.", "danger");
            return;
          }
          setCandidate(point, "");
          setStatus(
            actionStatus,
            "Device location selected. It is provided by your browser and is not independently verified.",
            "warning",
          );
        },
        (error) => {
          useLocationButton.disabled = false;
          if (requestVersion !== selectionVersion) return;
          showGpsError(error);
        },
        {enableHighAccuracy: true, maximumAge: 0, timeout: 15000},
      );
    };

    const confirmCandidate = async () => {
      if (!candidate) return;
      const selection = candidate;
      const version = selectionVersion;
      confirmButton.disabled = true;
      setStatus(
        actionStatus,
        donorProfileMode
          ? "Confirming the donation area…"
          : requestLocationMode
            ? "Confirming the request location…"
            : "Confirming the selected location…",
        null,
      );

      let address = selection.address;
      let addressAvailable = Boolean(address);
      let areaLabel = selection.label;
      const needsLookup = donorProfileMode ? !areaLabel : requestLocationMode ? false : !address;
      if (!placesOnlyMode && needsLookup && geocoder) {
        try {
          const response = await geocoder.geocode({location: selection.point});
          const result = response.results?.[0];
          address = result?.formatted_address || "";
          areaLabel = areaLabel || generalAreaLabel(result?.address_components || [], "");
          if (donorProfileMode && !selection.placeId) selection.placeId = result?.place_id || "";
          addressAvailable = donorProfileMode ? Boolean(areaLabel) : Boolean(address);
        } catch {
          addressAvailable = false;
        }
      } else if (needsLookup) {
        addressAvailable = false;
      }

      if (version !== selectionVersion) return;
      if (donorProfileMode) {
        if (!areaLabel) {
          confirmButton.disabled = false;
          setStatus(
            actionStatus,
            "No general area name was found. Search for a city, district, area, or nearby landmark before confirming.",
            "warning",
          );
          return;
        }
        selection.label = areaLabel;
        root.dataset.locationConfirmed = "true";
        if (donationAreaLabelInput) donationAreaLabelInput.value = areaLabel;
        if (donationAreaLatitudeInput) donationAreaLatitudeInput.value = formatCoordinate(selection.point.lat);
        if (donationAreaLongitudeInput) donationAreaLongitudeInput.value = formatCoordinate(selection.point.lng);
        if (googlePlaceIdInput) googlePlaceIdInput.value = selection.placeId || "";
        if (locationSourceInput) locationSourceInput.value = selection.source;
        if (locationConfirmedInput) locationConfirmedInput.value = "true";
        if (confirmedAddress) confirmedAddress.textContent = areaLabel;
        if (confirmedPanel) confirmedPanel.hidden = false;
        if (emptyState) emptyState.hidden = true;
        setStatus(
          actionStatus,
          "Donation area confirmed for this form. Save the profile to store it privately.",
          "success",
        );
        return;
      }
      if (requestLocationMode) {
        if (!areaLabel) {
          confirmButton.disabled = false;
          setStatus(
            actionStatus,
            "Choose a place with a general-area name, or select a map pin first.",
            "warning",
          );
          return;
        }
        selection.label = areaLabel;
        root.dataset.locationConfirmed = "true";
        if (requestLocationLabelInput) requestLocationLabelInput.value = areaLabel;
        if (requestLocationLatitudeInput) {
          requestLocationLatitudeInput.value = formatCoordinate(selection.point.lat);
        }
        if (requestLocationLongitudeInput) {
          requestLocationLongitudeInput.value = formatCoordinate(selection.point.lng);
        }
        if (requestLocationPlaceIdInput) {
          requestLocationPlaceIdInput.value = selection.source === "GOOGLE_PLACE"
            ? selection.placeId || ""
            : "";
        }
        if (requestLocationSourceInput) {
          requestLocationSourceInput.value = selection.source;
        }
        if (requestLocationConfirmedInput) requestLocationConfirmedInput.value = "true";
        if (confirmedAddress) confirmedAddress.textContent = areaLabel;
        if (confirmedPanel) confirmedPanel.hidden = false;
        setStatus(
          actionStatus,
          "Request area confirmed for this form. Exact coordinates and Place ID are not shown in public listings.",
          "success",
        );
        return;
      }
      candidate.address = address;
      if (address && locationInput) locationInput.value = address;
      root.dataset.locationConfirmed = "true";
      if (confirmedAddress) confirmedAddress.textContent = address || "Address unavailable.";
      if (confirmedCoordinates) {
        confirmedCoordinates.textContent = `${selection.point.lat.toFixed(6)}, ${selection.point.lng.toFixed(6)}`;
      }
      if (confirmedPanel) confirmedPanel.hidden = false;
      const mode = root.dataset.locationPickerMode;
      setStatus(
        actionStatus,
        mode === "find-donor"
          ? addressAvailable
            ? "Location confirmed in this page only. Nearby donor matching is not available yet; no search was submitted."
            : "Pin confirmed in this page only, but no readable address was found. Nearby donor matching is not available yet."
          : addressAvailable
            ? "Location confirmed in this page only. It has not been independently verified or saved."
            : "Location confirmed in this page only; its address is unavailable. It has not been independently verified or saved.",
        addressAvailable ? "success" : "warning",
      );
    };

    const searchTypedAddress = async () => {
      if (!locationInput) return;
      const query = locationInput.value.trim();
      if (!query) {
        setStatus(actionStatus, "Type an address or place to search.", "warning");
        return;
      }
      if (placesOnlyMode) {
        if (!autocompleteSuggestionClass || !autocompleteSessionToken) {
          setStatus(
            actionStatus,
            requestLocationMode
              ? "Places suggestions are unavailable. Choose a request area on the map instead."
              : "Places suggestions are unavailable. Choose a donation area on the map instead.",
            "warning",
          );
          return;
        }
        requestSuggestions(true);
        return;
      }
      if (!geocoder) {
        setStatus(
          actionStatus,
          requestLocationMode
            ? "Places search is unavailable until Google Maps is configured."
            : donorProfileMode
              ? "Place lookup is unavailable right now. You can continue without selecting a donation area."
              : "Address lookup is unavailable until Google Maps is configured. You can still use browser location or administrative filters.",
          "warning",
        );
        return;
      }
      const requestVersion = ++addressSearchVersion;
      const selectionAtStart = selectionVersion;
      if (searchAddressButton) searchAddressButton.disabled = true;
      setStatus(actionStatus, "Searching the typed address…", null);
      try {
        const response = await geocoder.geocode({
          address: query,
          componentRestrictions: {country: "BD"},
        });
        if (
          requestVersion !== addressSearchVersion
          || selectionAtStart !== selectionVersion
          || query !== locationInput.value.trim()
        ) return;
        const result = response.results?.[0];
        if (!result) {
          setStatus(actionStatus, "No location found. Try a more specific address or select a suggestion.", "warning");
          return;
        }
        const point = asPoint(result.geometry.location.lat(), result.geometry.location.lng());
        if (!point) {
          setStatus(actionStatus, "The address result did not include a valid location. Try another search.", "warning");
          return;
        }
        const areaLabel = generalAreaLabel(result.address_components || [], "");
        setCandidate(point, result.formatted_address || query, {
          label: areaLabel,
          placeId: result.place_id || "",
          source: "GOOGLE_GEOCODE",
        });
        setStatus(
          actionStatus,
          donorProfileMode
            ? areaLabel
              ? "General area found and pin moved. Review the location, then confirm."
              : "No general area name was found. Try a broader area or nearby landmark."
            : "Address found and pin moved. Review the location, then confirm.",
          areaLabel || !donorProfileMode ? "info" : "warning",
        );
      } catch {
        if (requestVersion === addressSearchVersion) {
          setStatus(actionStatus, "Address search failed. Check the connection or try another address.", "warning");
        }
      } finally {
        if (requestVersion === addressSearchVersion && searchAddressButton) searchAddressButton.disabled = false;
      }
    };

    const selectSuggestion = async (index) => {
      const prediction = suggestions[index];
      if (!prediction) return;
      const requestVersion = ++placeRequestVersion;
      const selectionAtStart = selectionVersion;
      const query = locationInput.value.trim();
      closeSuggestions();
      setStatus(actionStatus, "Loading the selected place…", null);
      try {
        const place = prediction.toPlace();
        await place.fetchFields({fields: ["formattedAddress", "location", "displayName", "addressComponents", "id", "types"]});
        if (
          requestVersion !== placeRequestVersion
          || selectionAtStart !== selectionVersion
          || query !== locationInput.value.trim()
        ) return;
        if (!place.location) {
          setStatus(actionStatus, "The selected place has no location. Try another suggestion.", "warning");
          return;
        }
        const point = asPoint(place.location.lat(), place.location.lng());
        if (!point) {
          setStatus(actionStatus, "The selected place has an invalid location. Try another suggestion.", "warning");
          return;
        }
        const address = place.formattedAddress || place.displayName?.toString() || query;
        const areaLabel = generalAreaLabel(
          place.addressComponents || [],
          place.displayName?.toString() || "",
          place.types || [],
        );
        if (placesOnlyMode && !areaLabel) {
          setStatus(
            actionStatus,
            requestLocationMode
              ? "The selected place did not provide a usable general-area name. Choose another place or a map pin."
              : "The selected place did not provide a usable general-area name. Choose another place or a map pin.",
            "warning",
          );
          return;
        }
        autocompleteSessionToken = new autocompleteSessionTokenClass();
        setCandidate(point, address, {
          label: areaLabel,
          placeId: place.id || "",
          source: "GOOGLE_PLACE",
        });
      } catch {
        setStatus(
          actionStatus,
          donorProfileMode
            ? "Place details could not provide a location. Try another suggestion or choose a map pin."
            : "Place details could not be loaded. Try another suggestion or search the typed address.",
          "warning",
        );
      }
    };

    const setupAddressSearch = () => {
      if (!locationInput || addressInputInitialized) return;
      addressInputInitialized = true;
      locationInput.addEventListener("input", requestSuggestions);
      locationInput.addEventListener("keydown", (event) => {
        if (event.key === "ArrowDown" && suggestions.length) {
          event.preventDefault();
          updateActiveSuggestion(activeSuggestionIndex + 1);
        } else if (event.key === "ArrowUp" && suggestions.length) {
          event.preventDefault();
          updateActiveSuggestion(activeSuggestionIndex < 0 ? suggestions.length - 1 : activeSuggestionIndex - 1);
        } else if (event.key === "Escape") {
          closeSuggestions();
        } else if (event.key === "Enter") {
          event.preventDefault();
          if (activeSuggestionIndex >= 0) selectSuggestion(activeSuggestionIndex);
          else searchTypedAddress();
        }
      });
      locationInput.addEventListener("blur", () => {
        window.setTimeout(closeSuggestions, 120);
      });
      if (searchAddressButton) searchAddressButton.addEventListener("click", searchTypedAddress);
    };

    const setPointFromCoordinateInputs = () => {
      const point = asPoint(latitudeInput.value, longitudeInput.value);
      if (!point) {
        setStatus(actionStatus, "Enter a valid latitude (-90 to 90) and longitude (-180 to 180).", "danger");
        return;
      }
      setCandidate(point, "");
      if (map) map.setZoom(14);
    };

    const resetSelection = () => {
      selectionVersion += 1;
      suggestionRequestVersion += 1;
      addressSearchVersion += 1;
      placeRequestVersion += 1;
      window.clearTimeout(suggestionTimer);
      suggestionTimer = null;
      candidate = null;
      selectedHospital = null;
      clearConfirmed(donorProfileMode);
      if (confirmButton) confirmButton.disabled = true;
      if (latitudeInput) latitudeInput.value = "";
      if (longitudeInput) longitudeInput.value = "";
      if (locationInput) locationInput.value = "";
      if (searchAddressButton) searchAddressButton.disabled = false;
      closeSuggestions();
      if (marker) marker.setMap(null);
      if (radiusCircle) radiusCircle.setMap(null);
      if (locationAutocompleteHost) locationAutocompleteHost.replaceChildren();
      if (hospitalAutocompleteHost) hospitalAutocompleteHost.replaceChildren();
      if (hospitalSelection) {
        hospitalSelection.textContent = "";
        hospitalSelection.hidden = true;
      }
      if (useHospitalButton) useHospitalButton.disabled = true;
      if (mapsAvailable) {
        createLocationAutocomplete();
        createHospitalAutocomplete();
      }
      setStatus(
        actionStatus,
        donorProfileMode
          ? "Donation area cleared from this form. Save the profile to remove the saved area."
          : requestLocationMode
            ? "Request-area selection cleared. Select and confirm a location before publishing."
            : "Selection cleared from this page.",
        null,
      );
    };

    const loadPlace = async (event, requestVersion, isHospital) => {
      const selectionAtStart = selectionVersion;
      try {
        const prediction = event.placePrediction;
        if (!prediction) throw new Error("No place was selected");
        const place = prediction.toPlace();
        await place.fetchFields({fields: ["formattedAddress", "location", "displayName"]});
        const currentVersion = isHospital ? hospitalRequestVersion : placeRequestVersion;
        if (requestVersion !== currentVersion || selectionAtStart !== selectionVersion) return;
        if (!place.location) throw new Error("The selected place has no location");
        const point = asPoint(place.location.lat(), place.location.lng());
        if (!point) throw new Error("The selected place has invalid coordinates");
        const address = place.formattedAddress || place.displayName || "";

        if (isHospital) {
          selectedHospital = {point, address};
          if (hospitalSelection) {
            hospitalSelection.textContent = `Selected place: ${address || "Hospital location selected"}. It has not changed your search location.`;
            hospitalSelection.hidden = false;
          }
          if (useHospitalButton) useHospitalButton.disabled = false;
        } else {
          setCandidate(point, address);
        }
      } catch {
        const currentVersion = isHospital ? hospitalRequestVersion : placeRequestVersion;
        if (requestVersion === currentVersion && selectionAtStart === selectionVersion) {
          setStatus(
            actionStatus,
            isHospital
              ? "Hospital/place details could not be loaded. Your search location has not changed."
              : "Place details could not be loaded. Try another result or place a pin.",
            "warning",
          );
        }
      }
    };

    const createAutocomplete = (host, isHospital) => {
      if (!host) return;
      const autocomplete = new google.maps.places.PlaceAutocompleteElement({
        includedRegionCodes: ["bd"],
        requestedLanguage: "en",
      });
      if (isHospital) autocomplete.includedPrimaryTypes = ["hospital"];
      autocomplete.placeholder = isHospital ? "Search for a hospital or facility" : "Search for an address or place";
      autocomplete.setAttribute("aria-label", autocomplete.placeholder);
      autocomplete.addEventListener("gmp-select", (event) => {
        const requestVersion = isHospital ? ++hospitalRequestVersion : ++placeRequestVersion;
        loadPlace(event, requestVersion, isHospital);
      });
      autocomplete.addEventListener("gmp-error", () => {
        setStatus(
          actionStatus,
          requestLocationMode
            ? "Place search is temporarily unavailable. Retry when the map service is available."
            : donorProfileMode
              ? "Place search is temporarily unavailable. Retry when the map service is available."
              : "Place search is temporarily unavailable. Use the map or browser location.",
          "warning",
        );
      });
      host.replaceChildren(autocomplete);
      return autocomplete;
    };

    function createLocationAutocomplete() {
      const autocomplete = createAutocomplete(locationAutocompleteHost, false);
      if (autocomplete && searchMode) {
        autocomplete.includedPrimaryTypes = searchMode.value === "hospital" ? ["hospital"] : [];
      }
    }

    function createHospitalAutocomplete() {
      createAutocomplete(hospitalAutocompleteHost, true);
    }

    const initializeGoogleMaps = async () => {
      try {
        const mapsLibrary = await google.maps.importLibrary("maps");
        const Map = mapsLibrary.Map;
        if (!Map) throw new Error("Google Maps library is unavailable");

        map = new Map(mapElement, {
          center: {lat: 23.8103, lng: 90.4125},
          zoom: 7,
          mapTypeControl: false,
          streetViewControl: false,
          fullscreenControl: true,
        });
        marker = new google.maps.Marker({draggable: true});
        marker.addListener("dragend", (event) => {
          const point = asPoint(event.latLng.lat(), event.latLng.lng());
          if (point) {
            const pinLabel = requestLocationMode
              ? candidate?.label || "Map-selected area"
              : donorProfileMode
                ? "Adjusted donation area"
                : "";
            setCandidate(
              point,
              pinLabel,
              placesOnlyMode
                ? {label: pinLabel, placeId: "", source: "MAP_PIN"}
                : {},
            );
          }
        });
        map.addListener("click", (event) => {
          if (!event.latLng) return;
          const point = asPoint(event.latLng.lat(), event.latLng.lng());
          if (point) {
            const pinLabel = requestLocationMode
              ? candidate?.label || "Map-selected area"
              : donorProfileMode
                ? candidate ? "Adjusted donation area" : "Map-selected donation area"
                : "";
            setCandidate(
              point,
              pinLabel,
              placesOnlyMode
                ? {label: pinLabel, placeId: "", source: "MAP_PIN"}
                : {},
            );
          }
        });
        if (candidate) {
          marker.setPosition(candidate.point);
          marker.setMap(map);
          map.setCenter(candidate.point);
          map.setZoom(14);
        }
        if (!placesOnlyMode) {
          try {
            const geocodingLibrary = await google.maps.importLibrary("geocoding");
            if (geocodingLibrary.Geocoder) geocoder = new geocodingLibrary.Geocoder();
          } catch {
            geocoder = null;
          }
        }
        let placesAvailable = false;
        try {
          const placesLibrary = await google.maps.importLibrary("places");
          autocompleteSuggestionClass = placesLibrary.AutocompleteSuggestion || null;
          autocompleteSessionTokenClass = placesLibrary.AutocompleteSessionToken || null;
          placesAvailable = Boolean(
            (locationInput && autocompleteSuggestionClass && autocompleteSessionTokenClass)
            || (!locationInput && placesLibrary.PlaceAutocompleteElement)
          );
          if (locationInput && autocompleteSessionTokenClass) {
            autocompleteSessionToken = new autocompleteSessionTokenClass();
          }
        } catch {
          autocompleteSuggestionClass = null;
          autocompleteSessionTokenClass = null;
        }
        if (!placesOnlyMode && candidate && !candidate.address) {
          reverseGeocodeCandidate(candidate.point, selectionVersion);
        }
        mapsAvailable = true;
        if (mapFallback) mapFallback.hidden = true;
        if (locationInput) setupAddressSearch();
        else if (placesAvailable) createLocationAutocomplete();
        if (hospitalAutocompleteHost && placesAvailable) createHospitalAutocomplete();
        if (placesAvailable && (placesOnlyMode || geocoder)) {
          setStatus(
            providerStatus,
            requestLocationMode
              ? "Map and Places request-area search are ready."
              : donorProfileMode
                ? "Map and Places address search are ready."
                : "Map and address search are ready.",
            "success",
          );
        } else {
          const unavailable = [
            !placesAvailable ? "Place suggestions" : "",
            !placesOnlyMode && !geocoder ? "Address lookup" : "",
          ].filter(Boolean).join(" and ");
          setStatus(
            providerStatus,
            requestLocationMode
              ? "Map is ready; Places suggestions are unavailable. You can still select and confirm a map pin."
              : donorProfileMode
                ? "Map is ready; Places suggestions are unavailable. You can still select a general area on the map."
                : `Map is ready; ${unavailable} is unavailable.`,
            "warning",
          );
        }
        if (locationInput && !placesAvailable) {
          setStatus(
            actionStatus,
            requestLocationMode
              ? "Place suggestions are unavailable. Choose a request area on the map instead."
              : donorProfileMode
                ? "Place suggestions are unavailable. Choose a donation area on the map instead."
                : geocoder
                  ? "Place suggestions are unavailable. Type an address and use Search address."
                  : "Place suggestions and address lookup are unavailable. Use browser location or administrative filters.",
            "warning",
          );
        }
      } catch {
        if (mapFallback) mapFallback.hidden = false;
        setStatus(
          providerStatus,
          requestLocationMode
            ? "Google Maps or Places could not be initialized. Request-area selection is unavailable."
            : donorProfileMode
              ? "Map search is unavailable right now. You can continue without selecting a donation area."
              : "Google Maps or Places could not be initialized. Browser GPS may still be available; administrative donor search remains usable.",
          "warning",
        );
      }
    };

    document.addEventListener("bloodconnect:search-map-visible", () => {
      if (!map || !window.google?.maps) return;
      google.maps.event.trigger(map, "resize");
      if (candidate) map.setCenter(candidate.point);
    });

    const loadGoogleMaps = () => {
      if (!apiKey) {
        setStatus(
          providerStatus,
          requestLocationMode
            ? "Google Maps is not configured. Set GOOGLE_MAPS_BROWSER_API_KEY to enable request-area search and map selection."
            : root.dataset.locationPickerMode === "find-donor"
              ? "Map and address lookup are unavailable. Configure GOOGLE_MAPS_BROWSER_API_KEY for the development server. Browser location and administrative search remain available."
              : donorProfileMode
                ? "Map search is unavailable right now. You can continue without selecting a donation area."
                : "Google Maps is not configured. Set GOOGLE_MAPS_BROWSER_API_KEY to enable the map and Places search. Browser GPS may still be available.",
          "warning",
        );
        return;
      }
      if (googleScriptStarted) return;
      googleScriptStarted = true;
      setStatus(providerStatus, "Loading Google Maps and Places…", null);
      window.initBloodConnectLocationPicker = initializeGoogleMaps;
      window.gm_authFailure = () => {
        mapsAvailable = false;
        if (mapFallback) mapFallback.hidden = false;
        setStatus(
          providerStatus,
          requestLocationMode
            ? "Google Maps authorization failed. Check the browser key's referrer/API restrictions and Places API setup."
            : donorProfileMode
              ? "Map search is unavailable right now. You can continue without selecting a donation area."
              : "Google Maps authorization failed. Check the browser key's referrer/API restrictions and Cloud API setup. Administrative donor search remains usable.",
          "danger",
        );
      };
      const script = document.createElement("script");
      const url = new URL("https://maps.googleapis.com/maps/api/js");
      url.searchParams.set("key", apiKey);
      url.searchParams.set("loading", "async");
      url.searchParams.set("callback", "initBloodConnectLocationPicker");
      url.searchParams.set("v", "weekly");
      script.src = url.toString();
      script.async = true;
      script.onerror = () => {
        if (mapFallback) mapFallback.hidden = false;
        setStatus(
          providerStatus,
          requestLocationMode
            ? "Google Maps could not be loaded. Request-area selection is unavailable."
            : donorProfileMode
              ? "Map search is unavailable right now. You can continue without selecting a donation area."
              : "Google Maps could not be loaded. Browser GPS and administrative donor search may still be available.",
          "warning",
        );
      };
      document.head.appendChild(script);
    };

    if (useLocationButton) useLocationButton.addEventListener("click", requestDeviceLocation);
    if (confirmButton) confirmButton.addEventListener("click", confirmCandidate);
    if (locationInput) {
      locationInput.addEventListener("input", () => {
        if (candidate) {
          selectionVersion += 1;
          candidate = null;
          if (requestLocationMode || !donorProfileMode || root.dataset.locationConfirmed !== "true") {
            clearConfirmed();
          }
          if (confirmButton) confirmButton.disabled = true;
          if (marker) marker.setMap(null);
          if (radiusCircle) radiusCircle.setMap(null);
          setStatus(
            actionStatus,
            requestLocationMode
              ? "Search and select a new request area, or choose a map pin, then confirm it."
              : donorProfileMode
                ? "Search a new area or choose a suggestion. The saved area remains until you confirm a replacement or clear it."
                : "Address changed. Search it or choose a suggestion to move the pin.",
            null,
          );
        }
      });
      setupAddressSearch();
    }
    if (clearButton) clearButton.addEventListener("click", resetSelection);
    root.querySelectorAll("[data-radius]").forEach((button) => {
      button.addEventListener("click", () => {
        window.setTimeout(updateRadiusPreview, 0);
      });
    });
    if (setCoordinateButton) setCoordinateButton.addEventListener("click", setPointFromCoordinateInputs);
    if (useHospitalButton) {
      useHospitalButton.addEventListener("click", () => {
        if (selectedHospital) setCandidate(selectedHospital.point, selectedHospital.address);
      });
    }
    if (searchMode) {
      searchMode.addEventListener("change", () => {
        const autocomplete = locationAutocompleteHost.querySelector("gmp-place-autocomplete");
        if (autocomplete) {
          autocomplete.includedPrimaryTypes = searchMode.value === "hospital" ? ["hospital"] : [];
          autocomplete.placeholder = searchMode.value === "hospital"
            ? "Search for a hospital"
            : "Search for an address or place";
          autocomplete.setAttribute("aria-label", autocomplete.placeholder);
        }
      });
    }

    const initialPoint = donorProfileMode
      ? asPoint(donationAreaLatitudeInput?.value, donationAreaLongitudeInput?.value)
      : requestLocationMode
        ? asPoint(requestLocationLatitudeInput?.value, requestLocationLongitudeInput?.value)
        : null;
    const initialAreaLabel = donorProfileMode
      ? donationAreaLabelInput?.value || ""
      : requestLocationLabelInput?.value || "";
    const hasConfirmedInitialArea = Boolean(
      placesOnlyMode
      && initialPoint
      && initialAreaLabel
      && (
        donorProfileMode
          ? locationConfirmedInput?.value === "true"
          : requestLocationConfirmedInput?.value?.toLowerCase() === "true"
      ),
    );
    root.dataset.locationConfirmed = String(hasConfirmedInitialArea);
    if (hasConfirmedInitialArea) {
      candidate = {
        point: initialPoint,
        address: initialAreaLabel,
        label: initialAreaLabel,
        placeId: donorProfileMode
          ? googlePlaceIdInput?.value || ""
          : requestLocationPlaceIdInput?.value || "",
        source: donorProfileMode
          ? locationSourceInput?.value || "MAP_PIN"
          : requestLocationSourceInput?.value || "MAP_PIN",
      };
      if (locationInput) locationInput.value = initialAreaLabel;
      if (confirmedAddress) confirmedAddress.textContent = initialAreaLabel;
      if (confirmedPanel) confirmedPanel.hidden = false;
      if (emptyState) emptyState.hidden = true;
    }
    loadGoogleMaps();
  }
})();
