(() => {
  const form = document.querySelector("[data-donor-search-form]");
  if (!form) return;

  const viewButtons = Array.from(form.querySelectorAll("[data-results-view]"));
  const resultPanels = Array.from(form.querySelectorAll("[data-results-panel]"));
  const resultsLayout = form.querySelector("[data-results-layout]");
  const setResultsView = (view) => {
    viewButtons.forEach((button) => {
      const active = button.dataset.resultsView === view;
      button.setAttribute("aria-pressed", String(active));
      button.classList.toggle("is-active", active);
    });
    resultPanels.forEach((panel) => {
      panel.hidden = false;
    });
    resultsLayout?.classList.toggle("is-map-view", view === "map");
    if (view === "map") document.dispatchEvent(new Event("bloodconnect:search-map-visible"));
  };
  viewButtons.forEach((button) => button.addEventListener("click", () => {
    setResultsView(button.dataset.resultsView);
  }));
  setResultsView("list");

  const radiusButtons = Array.from(form.querySelectorAll("[data-radius]"));
  const selectedRadius = () => radiusButtons.find((button) => button.getAttribute("aria-pressed") === "true");

  const setRadius = (selectedButton) => {
    radiusButtons.forEach((button) => {
      button.setAttribute("aria-pressed", String(button === selectedButton));
    });
  };

  radiusButtons.forEach((button) => button.addEventListener("click", () => {
    setRadius(selectedRadius() === button ? null : button);
  }));

  const division = form.elements.division;
  const district = form.elements.district;
  const upazila = form.elements.upazila;
  const union = form.elements.union;
  const corporation = form.elements.city_corporation;
  const zone = form.elements.city_zone;
  const ward = form.elements.ward;
  const endpoint = form.dataset.locationOptionsUrl;
  const generations = new WeakMap();
  const statuses = new WeakMap();
  if (!division || !district || !upazila || !union || !corporation || !zone || !ward || !endpoint) return;

  const load = async (field, level, parentId, emptyLabel) => {
    const generation = (generations.get(field) || 0) + 1;
    generations.set(field, generation);
    let status = statuses.get(field);
    if (!status) {
      status = document.createElement("p");
      status.className = "form-text";
      status.setAttribute("role", "status");
      field.insertAdjacentElement("afterend", status);
      statuses.set(field, status);
    }
    status.textContent = "";
    field.replaceChildren(new Option(emptyLabel, ""));
    field.removeAttribute("aria-busy");
    if (!parentId) return;
    field.setAttribute("aria-busy", "true");
    try {
      const url = endpoint.replace("DISTRICT", level) + `?parent=${encodeURIComponent(parentId)}`;
      const response = await fetch(url, {headers: {"Accept": "application/json"}});
      if (!response.ok) throw new Error("Location options request failed");
      const payload = await response.json();
      if (!Array.isArray(payload.results)) throw new Error("Invalid location options response");
      if (generations.get(field) !== generation) return;
      payload.results.forEach((item) => {
        if (typeof item.id === "string" && typeof item.name_en === "string") {
          field.add(new Option(item.name_en, item.id));
        }
      });
    } catch {
      if (generations.get(field) === generation) {
        status.textContent = "Location options are temporarily unavailable. Try changing the parent again.";
      }
    } finally {
      if (generations.get(field) === generation) field.removeAttribute("aria-busy");
    }
  };

  const clear = (field, label) => field && load(field, "", "", label);
  division.addEventListener("change", () => {
    clear(upazila, "Any upazila");
    clear(union, "Any union");
    clear(corporation, "Any city corporation");
    clear(zone, "Any city zone");
    clear(ward, "Any ward");
    load(district, "DISTRICT", division.value, "Any district");
  });
  district.addEventListener("change", () => {
    clear(union, "Any union");
    clear(zone, "Any city zone");
    clear(ward, "Any ward");
    load(upazila, "UPAZILA", district.value, "Any upazila");
    load(corporation, "CITY_CORPORATION", district.value, "Any city corporation");
  });
  upazila.addEventListener("change", () => load(union, "UNION", upazila.value, "Any union"));
  corporation.addEventListener("change", () => {
    clear(zone, "Any city zone");
    clear(ward, "Any ward");
    load(zone, "ZONE", corporation.value, "Any city zone");
    load(ward, "WARD", corporation.value, "Any ward");
  });
  zone.addEventListener("change", () => load(ward, "WARD", zone.value, "Any ward"));
})();
