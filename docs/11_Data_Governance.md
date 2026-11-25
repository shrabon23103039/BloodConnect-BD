# 11 — Data Governance, Privacy and Safety

## 1. Data minimization

Collect only data needed for account access, donor discovery, request coordination, safety and lawful operation.

Do not collect NID numbers, medical records, laboratory results, diagnoses or exact street addresses. Under the revised, not-yet-implemented concept, a donor may explicitly confirm a location point and separately consent to its private storage and server-side use for discovery. Do not assume the selected point is the donor's home.

## 2. Data classification

| Class | Examples | Handling |
|---|---|---|
| Public | Product pages, approved organization address | Public |
| User-private | Email, phone, profile settings | Owner/authorized access |
| Sensitive location | Donor-confirmed latitude/longitude | Private profile data; owner-only read/write and server-side matching; never public |
| Sensitive coordination | Blood group, request details, contact decisions | Restricted, minimized |
| Security | Audit events, auth events | Highly restricted |
| Secret | Password hashes, tokens, provider credentials | Never expose/log |

Blood group and request context should be treated as sensitive personal information even if a specific legal classification may vary.

## 3. Consent

Capture separate, versioned consent for:
- donor profile discoverability;
- contact channel disclosure after donor acceptance;
- optional notifications;
- donor-selected area storage (`donor_area_storage`);
- donor location storage/use for matching (`donor_location_matching`);
- optional location/map display;
- future organization sharing, if introduced.

Consent must be clear, purpose-specific, revocable where applicable and recorded with policy version and timestamp.

## 4. Donor privacy

- Donor contact details are hidden by default.
- Donor profile is discoverable only after explicit opt-in.
- For the profile-only picker, donor coordinates and area metadata are stored only after explicit confirmation and separate `donor_area_storage` consent. These private fields are not used for matching or public display.
- Only the donor's own profile form may read or update the saved point. Do not include it in public serializers, donor search, logs, analytics, notifications or exports.
- The donor may replace/remove the point or withdraw area-storage consent. Clearing immediately removes coordinates, label, Place ID, source and confirmation timestamp. Future matching consent and retention rules remain separate decisions.
- Generalized area is displayed; exact address is not.
- Donor can pause or hide their profile.
- Donor may accept/decline contact requests.
- Only donor-selected contact channels are disclosed after acceptance.
- Avoid displaying last donation date publicly.

## 5. Medical and safety boundaries

- Platform does not assess donor eligibility.
- Platform does not calculate transfusion compatibility.
- Exact blood-group search is a discovery filter only.
- Healthcare professionals and authorized facilities determine clinical suitability and compatibility.
- Platform does not guarantee that a donor will respond or donate.
- Users should coordinate through an authorized healthcare facility.
- Emergency messaging must not imply the platform replaces emergency services.

## 6. Verification terminology

Allowed:
- Phone verified.
- Email verified.
- Account reviewed.
- Organization identity reviewed (scope shown).

Not allowed:
- Medically verified donor.
- Safe donor.
- Clinically eligible.
- Compatible donor.
- Blood guaranteed.

## 7. Bangladesh legal and regulatory review

Before real public launch, obtain qualified local legal and healthcare review of:
- applicable personal-data protection requirements;
- cyber/security obligations;
- consent and retention rules;
- electronic communications and OTP/SMS provider obligations;
- blood transfusion and blood-bank regulatory boundaries;
- terms, privacy notice and incident response.

Do not claim legal compliance solely because a feature exists. Government or health-data integration requires written authorization, API documentation, data-sharing basis and security review.

## 8. Retention and deletion

- Define retention schedule for accounts, requests, reports, audit events and backups.
- Deactivation immediately excludes a donor from all matching.
- Account deletion removes precise coordinates from the active database as part of deletion processing.
- Proposed maximum backup purge window for deleted or consent-revoked precise coordinates: 30 days. This is subject to final privacy/legal policy approval; backups and restore workflows must ensure the coordinates are no longer retained after that deadline.
- Provide an account/data request workflow.
- Preserve records only where a documented legal, safety or security reason requires it.
- Apply deletion/retention policy consistently to backups and third-party providers.
- Record administrative exceptions.

## 9. Analytics

- Prefer aggregate counts.
- Avoid small-cell reporting that could re-identify individuals.
- Do not expose individual donor histories to public analytics.
- Do not use sensitive attributes for advertising or ranking.

## 10. Administrative location data provenance

Location snapshots must be reviewed for source, version/retrieval date, source identifiers, division–district–upazila parent links, bilingual naming, counts, duplicate paths, missing parents, encoding, license/terms and attribution before import. “Non Restricted” security classification alone does not grant redistribution or derivative-data rights. Preserve the source IDs and attribution when the source permits use; do not publish or redistribute source data until the provider terms are confirmed.

**2026-11-21 source review:** `https://gis.gov.bd/en/gis_file.php?id=15` returned a 459-byte Vite + React placeholder document with no downloadable administrative dataset. The NSDI Survey of Bangladesh catalog (`https://new.nsdi.gov.bd/datacatalog/`) lists a 2023 (work ongoing) ESRI geodatabase for 495 upazilas as “Non Restricted,” but its public catalog exposes no direct file, names/IDs, lineage or specific reuse terms. The FAQ states public information does not necessarily require sign-in and provider-specific usage terms may vary; it does not establish reuse rights for a specific data product. BBS GIS metadata advertises administrative-boundary downloads, but its site timed out during this review. No data was downloaded or imported; counts, IDs, hierarchy attributes, alternate names, license and attribution remain unverified. Keep P10-10 blocked pending an accessible official file and applicable terms.
**2026-11-21 candidate dataset review:** Open Admin Data's repository commit `1731ee8585a32ad62f5c898f8e8e3f7659b1aa5a` (`2026.09`, retrieved 2026-11-21) was inspected and transformed under CC BY 4.0. The actual JSON has 8/64/495 records and passes structural integrity checks; IDs are Open Admin Data identifiers, not confirmed government geocodes. Raw hashes, attribution, transformation and license are in `data/locations/ATTRIBUTION.md` and `data/locations/CC-BY-4.0.txt`. The source's 72-row `all-flat.csv` omits upazilas; they were taken from the dedicated upazila JSON. Only 8/567 records provide a direct source URL.

**2026-11-22 Dhaka city schema review:** Official DNCC [Location and Area](https://dncc.gov.bd/pages/static-pages/6922ded3933eb65569e1da8e) page reports 10 zones and 54 wards and provides a ward/area list. Official DSCC [Overview](https://dscc.gov.bd/pages/static-pages/6922df02933eb65569e1f260) reports 75 wards; an official DSCC [2025 notice](https://dscc.gov.bd/pages/notices/695ba2b035ce18e1c05b0008) references 10 zones and 75 wards. Pages checked on 2026-11-22; page-specific last-updated dates and stable row identifiers were not available from the retrieved page content. No downloadable complete machine-readable ward/zone data or explicit reuse/redistribution license was verified. These counts are validation targets only, not imported records. No government codes have been inferred. Keep all city rows inactive until an authoritative source file, exact hierarchy, source IDs, retrieval/version metadata, and reuse terms are confirmed. Thana is currently represented only as optional self-reported profile text, not as a verified administrative location or search field; no thana-to-ward mapping is asserted.

**2026-11-22 Dhaka city data acquisition follow-up (retrieval date 2026-11-22):** Examined the official DNCC [Location and Area](https://dncc.gov.bd/pages/static-pages/6922ded3933eb65569e1da8e) content, official DNCC [map page](https://dncc.gov.bd/pages/static-pages/6922e133933eb65569e2ad72), official DSCC [Zone/Ward page](https://dscc.gov.bd/pages/static-pages/6922db5a933eb65569e099b7), DSCC [regional office/ward listing](https://dscc.gov.bd/pages/static-pages/6922dba8933eb65569e0b9ed), [overview](https://dscc.gov.bd/pages/static-pages/6922df02933eb65569e1f260), [2025 notice](https://dscc.gov.bd/pages/notices/695ba2b035ce18e1c05b0008), [Bangladesh GIS Platform geocode page](https://gis.gov.bd/en/gis_file.php?id=15), [NSDI/SOB catalogue](https://new.nsdi.gov.bd/datacatalog/), and [NSDI FAQ](https://new.nsdi.gov.bd/faqs/). The DNCC Location/Area page links a [387,155-byte PDF](https://objectstorage.ap-dcc-gazipur-1.oraclecloud15.com/n/axvjbnqprylg/b/V2Ministry/o/office-dncc/2024/12/7f1f5f6f2d104aaebba9c5e53fccdb51.pdf); the DNCC map page links a [566,270-byte PDF](https://objectstorage.ap-dcc-gazipur-1.oraclecloud15.com/n/axvjbnqprylg/b/V2Ministry/o/office-dncc/2024/12/bbb660576ab842a3a47475713bedfe69.pdf); the DSCC Zone/Ward page links a [103,614-byte PDF](https://objectstorage.ap-dcc-gazipur-1.oraclecloud15.com/n/axvjbnqprylg/b/V2Ministry/o/office-dscc/2024/12/f5cf45f22fe447fb9b1a29ea48f16472.pdf); and the DSCC notice links a [268,751-byte PDF](https://objectstorage.ap-dcc-gazipur-1.oraclecloud15.com/n/axvjbnqprylg/b/V2Ministry/o/office-dscc/2024/12/045ff7379c5b4ceb9e6470052af7c821.pdf). Their GET responses were `application/pdf`; their contents were not extracted or treated as location records. The DNCC HTML gives a 10-region/54-ward allocation and Bengali locality descriptions, but no machine-readable tabular source, separately identified zone entities, formal machine IDs, English/Bengali name pairs or publication/version metadata. The DSCC Zone/Ward page identifies its content as last updated 2016-12-08; its linked PDF was reachable in this continuation but not text-extracted. The more recent DSCC regional-office page includes ward lists but is operational HTML, not a versioned data product. The DSCC overview/count page and 2025 notice establish the 75-ward/10-zone count target, not every parent edge. The GIS URL returned HTTP 200 but its actual body was only a 459-byte default “Vite + React” shell (`<title>Vite + React</title>`, empty `#root`, one app bundle reference); no geocode API, workbook, file, metadata or terms were obtainable at that URL. The NSDI catalogue identifies SOB Dhaka North and South guide maps as MXD/PDF/hard copy and “Non Restricted,” but gives no guide-map preparation/revision year, downloadable structured rows, zone/ward IDs or reuse license; classification is not a license. The FAQ says public catalog access does not necessarily require sign-in, but provider-specific usage terms may vary. The current DTCA [2023 Survey Zone PDF URL](https://dtca.gov.bd/sites/default/files/files/dtca.portal.gov.bd/notices/26e28ce1_642d_4401_a23c_00e8c77f2a87/2023-03-16-06-46-2d317c9258145f12c6d977169f459a8d.pdf) returned HTTP 404 (`text/html`, 64,404 bytes) on this retrieval; its prior-described content was not re-verified from this response. The inspected candidate sources therefore do not jointly provide a verified, complete, current, reusable city-corporation → zone → ward snapshot. They provide no explicit thana-to-ward mapping. No snapshot was created, no location row was imported or activated, and no candidate names/IDs were inferred from counts. The existing rural candidate source remains Open Admin Data `2026.09` under CC BY 4.0 and contains only 8 divisions, 64 districts and 495 upazilas; it does not supply city records.

**Exact unblock request:** request from DNCC and DSCC (or the authorized LGD/NSDI data custodian) one current, versioned CSV/XLSX/GeoPackage/GeoJSON export per corporation with (a) all 10 zone/region records and all 54 DNCC / 75 DSCC ward records, (b) official stable source IDs or written confirmation that corporation-scoped ward/zone numbers are the official identifiers, (c) explicit ward-to-zone/corporation parent IDs, (d) source English and Bangla names where maintained, (e) effective/publication date and corrections history, (f) confirmation of coverage/completeness, and (g) written reuse/redistribution and derivative-database terms plus attribution wording. Request a separate thana list and explicit thana/ward relationships only if the corporations maintain them. Once received, preserve the unmodified files and hashes, compare parent assignments and counts (DNCC 10/54; DSCC 10/75), validate hierarchy/duplicates, document permission, then prepare an inactive reviewed manifest for approval before any activation.

The snapshot is not activated: it omits units appearing in 2026 government/BSS reports, and available public sources disagree about the effective count (BSS reports 498 after July approvals; an unofficial 2026-07 community dataset reports 502 upazilas plus 74 thanas). The 567 imported candidate records remain stored but inactive pending official reconciliation. No existing donor profiles referenced them. The source JSON, attribution and license remain in the repository for review, but `.dockerignore` excludes `data/locations/` from runtime build contexts. No application runtime requires this candidate file. Do not use this candidate for current location selection until unit status, names, boundaries/parents, identifiers and authoritative reuse terms are resolved.

**2026-11-22 source acquisition verification (retrieved 2026-11-22):** Direct HTTP GETs of the official DNCC [Location and Area](https://dncc.gov.bd/pages/static-pages/6922ded3933eb65569e1da8e), [map](https://dncc.gov.bd/pages/static-pages/6922e133933eb65569e2ad72), DSCC [Zone/Ward](https://dscc.gov.bd/pages/static-pages/6922db5a933eb65569e099b7), [regional offices/ward listing](https://dscc.gov.bd/pages/static-pages/6922dba8933eb65569e0b9ed), [overview](https://dscc.gov.bd/pages/static-pages/6922df02933eb65569e1f260), [2025 notice](https://dscc.gov.bd/pages/notices/695ba2b035ce18e1c05b0008), [Bangladesh GIS Platform geocode page](https://gis.gov.bd/en/gis_file.php?id=15), [NSDI/SOB catalog](https://new.nsdi.gov.bd/datacatalog/), and [NSDI FAQ](https://new.nsdi.gov.bd/faqs/) returned HTTP 200. The GIS response was exactly 459 bytes (`text/html`): a default Vite + React page with an empty `#root`, no data/API metadata or download link. It is not a usable dataset.

The official HTML pages provide lists, map references and count evidence, not a versioned machine-readable hierarchy. Linked files returned only PDF responses: DNCC attachments 387,155 and 566,270 bytes; DSCC Zone/Ward attachment 103,614 bytes; DSCC notice attachment 268,751 bytes. These responses were checked as `application/pdf`; their contents were not extracted or treated as location records (no PDF extraction tool/library was available in the existing environment). The current DTCA [2023 Survey Zone PDF URL](https://dtca.gov.bd/sites/default/files/files/dtca.portal.gov.bd/notices/26e28ce1_642d_4401_a23c_00e8c77f2a87/2023-03-16-06-46-2d317c9258145f12c6d977169f459a8d.pdf) returned HTTP 404 (`text/html`, 64,404 bytes) on this retrieval; prior description of its contents is historical and was not re-verified from this response.

DNCC’s official page/count evidence is 10 zones/regions and 54 wards; no page-specific publication/update date or stable source IDs/parent IDs were found in the retrieved page. DSCC official overview/2025 notice evidence is 10 zones and 75 wards; the Zone/Ward page identifies itself as last updated 2016-12-08, so it is stale evidence, not a current data release. No page or attachment verified all zone and ward records with machine-readable parent links. No official stable row identifiers, separate structured zone entities, version/correction history, explicit thana-to-ward relationships, or written redistribution/derivative-data license or attribution wording were found. Ward counts and map/list content are reference evidence only; no ward, zone, thana, identifier, or parent assignment is inferred from them.

The NSDI/SOB catalog response describes a 495-upazila ESRI geodatabase with preparation/revision “2023 (Work is ongoing)” and security classification “Non Restricted”; the catalog response does not provide a downloadable structured file, feature IDs or lineage for the city ward hierarchy. The FAQ states public information does not necessarily require sign-in and that data may be free to download/use while provider-specific terms may vary. That statement does not establish permission for the specific data product or derivative redistribution. DNCC/DSCC pages and attachments displayed no explicit reuse license or attribution requirements. City-page update/publication dates were otherwise not available in the retrieved content. The GIS shell had no publication date or terms. The BBS GIS site had timed out in the earlier recorded review.

**Manifest check and disposition:** the existing `load_locations` JSON contract requires top-level `source.name`, `version`, `url`, `reviewed_by`, `reviewed_at`, plus non-empty validated `records` with names, levels and ordered parent paths; `source_id` is optional. The importer requires `--reviewed` and does not activate records unless `--activate` is supplied. The contract does not itself capture retrieval date, publication/update date, license/permission, or attribution wording; those must be recorded in supporting provenance documentation before a source can be approved. No city JSON, manifest, or location rows were created. **SOURCE GAP — NO IMPORT/ACTIVATION** until DNCC/DSCC or an authorized custodian supplies a complete current machine-readable export with stable IDs or written identifier policy, explicit zone/ward parent IDs, source version/effective date, completeness confirmation, and written reuse/derivative terms and attribution.

## 11. Location-first search privacy (nearby matching not implemented)

- Ask for browser geolocation only after the user explicitly selects “Use my current location”; rely on browser permission and do not track in the background. Provide place/pin alternatives when permission is denied or unavailable.
- Donor location is separate from requester search location. The current profile picker lets the donor select a general area through Google Places/geocoding or a map pin, explicitly confirm it and grant separate, revocable `donor_area_storage` consent. It stores scalar coordinates, a generalized label, optional Place ID, source and server-set confirmation timestamp privately. It does not request GPS or enable discovery/matching. Do not collect an exact street address or assume the point is the donor's home.
- A blood requester may explicitly select and confirm a general request area using Places API (New) and an adjustable map pin. Store its label, private coordinates, optional Place ID, source and server-set confirmation timestamp on the request. Public request listings expose only the general label; never return coordinates or Place ID. This point is not used for donor matching, and facility name/address remain separate requester-entered fields. Do not request GPS or use Geocoding; disclose that the browser sends the requested place query and details directly to Google.
- Requester search latitude/longitude is sensitive transient input. The current `/app/` picker keeps it only in JavaScript memory and does not send it to the application backend. A future approved matching endpoint may receive it in a POST body over HTTPS; it must never be put in a URL, browser storage, analytics, logs, database records or error messages and must not retain it.
- Any future matching feature must validate requester and donor coordinates against a reviewed, approved Bangladesh boundary dataset. Reject outside points and fail closed if no approved boundary is active. Review dataset source, license, version, provenance and import/use approval before implementation; prefer a reviewed boundary dataset over a hand-written bounding box. No boundary dataset is approved, imported or activated for this profile-picker task.
- PostGIS `ST_DWithin` uses only donor-confirmed points for exact server-side radius eligibility at 5, 10, 20 or 50 km. Administrative representative points never qualify a donor for a radius and never receive a distance. If the interface supports a clearly separate section, show area-only candidates under exactly “Area matches — distance not verified,” without a distance or radius claim; otherwise omit them from radius results.
- Public results may show a generalized area and, only for radius-qualified results, one approximate straight-line distance band: `<2 km`, `2–5 km`, `5–10 km`, `10–20 km`, `20–50 km`, or `>50 km`. This is not road/travel distance. Never reveal donor coordinates, exact distance, exact address or inferred home location through public APIs, templates, admin exports, logs or errors.
- Withdrawal of `donor_area_storage` immediately clears the stored point, label, Place ID, source and confirmation timestamp. Map-only profiles are not discoverable under current search rules. Any later coordinate matching requires a separate consent/schema/security review.
- The profile picker sends user-entered place queries and selected pin coordinates directly from the browser to Google Maps Platform when Places/geocoding features are used; disclose this provider data flow. Do not send donor records, blood group or search results. Keep requester coordinates transient and provider data minimized.
- The optional hospital/place search is only a way to select a search center unless separately approved. It does not confirm a facility, donor/hospital affiliation, inventory, medical suitability or compatibility.
- `/location-demo/` and the `/app/` requester location picker use Google Maps Platform in the browser when the restricted development key is configured. User place-search queries and selected coordinates used for reverse geocoding are sent to Google after interaction; the map also loads Google's map resources. On `/app/`, requester coordinates remain in page memory and are not sent to BloodConnect Django endpoints. In the donor profile picker, the donor-selected query and pin coordinates go directly from the browser to Google only for the requested map/geocoding operation, as disclosed on the form. BloodConnect does not send donor profile records, blood group or search results to Google.
- The Find Donor production provider remains unselected. Before product use, review current per-SKU charges/free usage, billing requirements, terms, attribution, storage/caching limits, regional requirements, data transfers and privacy-notice language. Browser geolocation itself does not use Google. Never transmit donor profile records, blood group or search results to a map provider.
- Provide a provider-independent fallback or clear error state. A map/Places outage must not disclose coordinates or silently broaden/alter search results; define a usable alternate location-selection route before release. OSM-derived data and public tile services have separate license and operational terms that must be reviewed.
