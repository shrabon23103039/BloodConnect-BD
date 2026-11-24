# 08 — Test Strategy and Quality Assurance

## 1. Testing objectives

Verification email tests use Django?s locmem backend and synthetic sender/recipient values; they cover single-send behavior, verification success, SMTP failure handling and ensure automated tests never send real mail. Google OAuth tests use synthetic client values and mocked provider responses. Cover CSRF-protected initiation, state and PKCE, provider cancellation/errors, malformed issuer/audience/expiry/subject/email claims, pending signup, explicit link and collision policies, account status, token/secret redaction, and local email/phone regressions. Browser-check registration, login and account access at mobile, tablet and desktop widths, including focus, loading, cancellation/error and reduced-motion behavior. Label mocked results separately from live Google verification.

Verify functional behavior, privacy, authorization, state transitions, accessibility, resilience and measured performance.

## 2. Test levels

### Unit tests
- Blood-group enum validation.
- Location hierarchy validation.
- Donor availability state.
- Blood-request state transitions.
- Contact-request state transitions.
- Permission helper functions.
- Notification idempotency.

### Integration tests
- Registration and verification.
- Donor profile creation and search.
- Donor area-picker save/update/clear with private storage consent; map-only profiles remain excluded from existing donor discovery.
- PostGIS location acceptance tests run only against an isolated test database with the required PostGIS extension; never point them at the shared Compose database or named volume.
- Request creation and donor search.
- Contact request and notification.
- Donor acceptance and contact disclosure.
- Report/block workflow.
- Celery retry and provider failure.

### End-to-end tests
- Visitor registers.
- User creates donor profile.
- Recipient creates a blood request.
- Recipient searches donor and sends contact request.
- Donor signs in and accepts.
- Recipient sees only donor-consented contact channel.
- Recipient closes request.
- Admin reviews a report.

### Security tests
- Unauthenticated access to private endpoints.
- Cross-user object access.
- Serializer field leakage.
- Donor location coordinate ownership and privacy.
- Requester search-coordinate non-persistence and log redaction.
- CSRF behavior.
- Rate limits.
- Upload restrictions.
- Admin privilege boundaries.
- Token expiry/revocation.

### Non-functional tests
- Responsive layout at defined widths.
- Keyboard navigation and accessible labels.
- Load test for search and request creation.
- Backup restore.
- Provider outage behavior.

### UI audit and responsive baseline

The route inventory and viewport configuration live in `tests/ui/audit_config.py`; the non-destructive Chromium runner is `tests/e2e/test_ui_audit.py`. It uses Playwright from the pinned Python development requirements, an isolated `config.settings.test` database, and a synthetic user. Never point this runner at production or reuse a human browser storage state. Routes are loaded once and resized to avoid triggering authentication throttles; it does not submit application forms or mutate account preferences.

Install the pinned test-only axe-core asset with `npm ci`, then run:

```powershell
.venv\Scripts\python.exe -m pytest --ds=config.settings.test --no-migrations tests/e2e/test_ui_audit.py -q --tb=short -p no:cacheprovider
$env:BLOODCONNECT_CAPTURE_UI_AUDIT = "1"
.venv\Scripts\python.exe -m pytest --ds=config.settings.test --no-migrations tests/e2e/test_ui_audit.py -q --tb=short -p no:cacheprovider
$env:BLOODCONNECT_COMPARE_UI_AUDIT = "1"
.venv\Scripts\python.exe -m pytest --ds=config.settings.test --no-migrations tests/e2e/test_ui_audit.py -q --tb=short -p no:cacheprovider
```

The runner checks the 11 widths in `VIEWPORT_WIDTHS`, records document overflow, active navigation, title, H1 count and body typography, executes axe-core WCAG 2.1 A/AA checks at 390px and 1366px, and records browser console/page/request failures. Set `BLOODCONNECT_CAPTURE_UI_AUDIT=1` only to intentionally refresh reference screenshots. Set `BLOODCONNECT_COMPARE_UI_AUDIT=1` to compare actual screenshots to the saved PNG baseline with pinned `pixelmatch`/`pngjs`; the default tolerance is 0.5% changed pixels, and failures write diagnostic images to the ignored `tests/ui/diffs/`. Findings are data, not automatically suppressed or rewritten. The machine-readable run is written to `tests/ui/baseline-results.json`. Opt-in screenshots are limited to representative pages and saved under `tests/ui/screenshots/<page>/{mobile,desktop}/baseline.png`; those baseline images use synthetic test data. Pages requiring domain records or a moderator role are explicitly listed as outside the baseline rather than reported as passing.

The checklist in `tests/ui/QUALITY_CHECKLIST.md` supplements automated checks; axe and geometry checks are not a complete manual accessibility or visual review. Lighthouse remains optional and is not installed in the current project.

## 3. Critical acceptance tests

| ID | Scenario | Expected result |
|---|---|---|
| T-001 | Guest requests donor private profile | Private data not returned |
| T-002 | Recipient searches donor | Only consented public fields returned |
| T-003 | Recipient sends contact request | Pending request created once |
| T-004 | Duplicate request submitted | Duplicate blocked/idempotently handled |
| T-005 | Wrong user accepts request | 403 or non-disclosing 404 |
| T-006 | Donor declines | Contact data remains hidden |
| T-007 | Donor accepts without phone-share consent | Phone remains hidden |
| T-008 | Donor accepts with phone-share consent | Only allowed phone field is returned to parties |
| T-009 | Donor becomes unavailable | Excluded from new discovery results |
| T-010 | Request cancelled | New contact requests blocked |
| T-011 | User blocks another user | New contact request blocked according to policy |
| T-012 | Admin suspends account | Account cannot use restricted features |
| T-013 | OTP replay | Rejected |
| T-014 | OTP brute force | Rate limited |
| T-015 | Notification provider down | Core transaction remains committed; retry recorded |
| T-016 | Another user requests donor profile/search results | Donor-confirmed coordinates and exact address are absent |
| T-017 | Donor reads/updates private location | Only the authenticated profile owner can access it; confirmation and active purpose-specific consent are required |
| T-018 | Requester searches with a confirmed point | Search coordinates are absent from persistent records, URLs, analytics and logs |
| T-019 | Donor withdraws location-matching consent | Stored donor coordinates and confirmation timestamp are cleared |
| T-020 | Donor has no confirmed coordinates and has a reviewed administrative point | If requested and the client supports separation, show only under “Area matches — distance not verified,” with no distance or radius claim; otherwise omit |
| T-021 | Donor has confirmed coordinates and an administrative point | PostGIS radius eligibility uses donor-confirmed coordinates only; administrative points never influence radius qualification or distance |
| T-022 | Donor lies exactly on a selected radius boundary | `ST_DWithin` includes the exact boundary using the private point; a point just outside is excluded for 5, 10, 20 and 50 km |
| T-023 | Client requests area matches | `area_matches` are separate from radius-qualified results, use the exact required heading, and contain no distance or radius-qualified indicator; default/unsupported clients receive none |
| T-024 | Requester or donor point is outside Bangladesh, or no approved boundary is active | Outside points are rejected without echoing coordinates; missing approved boundary fails closed; no hand-written bounding-box substitute is used |
| T-025 | Donor submits GPS accuracy <=100 m, >100 m, or a map pin | Accept an eligible GPS fix; reject a less accurate fix for radius matching and request retry/pin; require explicit donor confirmation for a pin; persist source and timestamp |
| T-026 | Donor withdraws location-matching consent | Point, source, accuracy and confirmation timestamp are cleared immediately; the donor is excluded from coordinate matching |
| T-027 | Donor deactivates profile | Donor is immediately excluded from all matching, including administrative area results |
| T-028 | Account deletion processes a donor profile | Precise point is removed from the active database; backup purge deadline is documented and operationally enforced at no more than 30 days, subject to policy approval |
| T-029 | Public API, template, admin export, log or error path handles donor location | No donor coordinates or exact address are emitted; admin access does not create an export exception |
| T-030 | Requester performs a location search | Coordinates are sent only in the POST body and absent from database records, URLs, analytics, logs, result payloads and errors |
| T-031 | Public distance bands are generated | Only `<2 km`, `2–5 km`, `5–10 km`, `10–20 km`, `20–50 km`, or `>50 km` is shown; bands are approximate straight-line distance, never exact or road distance |
| T-032 | Exact distances cross a public band boundary | The band changes only at 2, 5, 10, 20 and 50 km using documented inclusive/exclusive boundaries; no exact distance is serialized |
| T-033 | User tries nearby search from the current `/app/` UI | Nearby-unavailable status is shown; requester coordinates, address, hospital selection and radius are absent from the administrative GET URL/request; existing blood-group and administrative filters still return the established results |
| T-034 | `/app/` location picker has no browser key | A normal editable address field and “Search address” control remain visible; trying address lookup explains that Google is unavailable; administrative search remains usable and no typed address/coordinates are submitted |
| T-035 | `/app/` location picker has a restricted browser key | In an explicitly configured browser test, verify Maps script load, map/pin initialization, Places API (New) suggestions and selection, typed-address geocoding, GPS reverse-geocoding, pin click/drag reverse-geocoding and reset. Do not print or store the key; do not mark live Google behavior passed when only mocked APIs were used |
| T-036 | Donor selects a general area in the profile picker | Place/pin selection is explicitly confirmed; no browser GPS is requested; only general label, coordinates, optional Place ID, source and server-set timestamp are saved after `donor_area_storage` consent |
| T-037 | Donor updates or clears the saved area | Owner can replace the selected point; clearing removes all area metadata and records consent withdrawal |
| T-038 | Map-only donor uses existing HTML/API search | The profile remains excluded by current administrative discovery requirements; no coordinates, Place ID or private label appear in public results |
| T-039 | Donor profile loads or saves location data | Only the owner profile form receives the private values; unauthenticated and other-user requests cannot read or change them |
| T-040 | Requester selects a Places result and adjusts the request pin | Places details supply coordinates without Geocoding; pin movement uses event coordinates; no GPS is requested; request fields remain unset until explicit confirmation |
| T-041 | Requester saves, edits, clears or publishes a map-selected request | The server sets confirmation time; drafts can clear the area; publishing requires a confirmed map area or a valid legacy area; detail/list show the coarse label only |
| T-042 | Public request API serializes a map-selected or legacy request | Map-selected responses include only the general-area label and omit coordinates, Place ID, source, facility details and requester identity; legacy administrative labels continue to render |

## 4. Tooling

- pytest and pytest-django for unit/integration tests.
- Django TestCase for framework-specific tests.
- DRF APIClient for API tests.
- Playwright for browser flows.
- Locust for load tests.
- Coverage.py for coverage reporting.
- Bandit or equivalent static security scanning.
- Dependency vulnerability scanner.
- OWASP ZAP for controlled staging DAST where configured.

## 5. Performance test protocol

Before running a load test, document:
- Environment and hardware/hosting plan.
- Database size and synthetic data distribution.
- Number of virtual users.
- Ramp-up period.
- Test duration.
- Request mix (search, dashboard, request read/write).
- Cache warm/cold state.
- p50, p95 and p99 latency.
- Throughput.
- Error rate.
- CPU, memory, database connections and queue depth.

Do not equate registered users with concurrent users. Do not publish a capacity claim without a repeatable test report.

## 6. Defect severity

- Critical: data exposure, account takeover, unauthorized state change, core service unavailable.
- High: major workflow broken, significant privacy/security weakness.
- Medium: feature degraded with workaround.
- Low: cosmetic or minor usability issue.

Critical and high defects block release unless a formally documented exception is approved by the project owner and appropriate reviewer.

## 7. Evidence requirements

For each test run, record:
- commit hash;
- environment;
- command;
- date;
- pass/fail count;
- failing test IDs;
- artifact/report location;
- known limitations.

Never fabricate test output or mark a test passed based on code inspection alone.
