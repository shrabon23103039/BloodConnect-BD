# 04 — Technical Requirements Document (TRD)

**Version:** 1.0  
**Architecture:** Modular monolith with versioned REST API.

## Google OAuth authentication

P13-01 uses django-allauth 65.22.1's Google provider for server-side Authorization Code Flow with state and PKCE, integrated with Django sessions while retaining `IdentifierBackend`. Scopes are `openid email profile`; social token persistence is disabled. Client ID and secret are backend-only environment settings. Confirmed callback route: `/accounts/google/login/callback/`; the actual local browser URL `http://127.0.0.1:8000/` produces `http://127.0.0.1:8000/accounts/google/login/callback/`. Accessing via `localhost` produces a different host and requires its own authorized redirect URI. The production URL depends on the verified deployment origin. Explicit linking requires a CSRF-protected POST by an authenticated ACTIVE account; matching email alone never links.

After a consented Google signup creates a pending user and its `SocialAccount`, the existing inactive-account/session policy redirects to the email verification form. The Google-verified email is placed in the session, and the existing challenge service sends the code; Google claims do not set BloodConnect `email_verified_at` or activate the account. The verification service can reuse a live unexpired challenge while holding its existing per-user row lock, preventing repeat callback sends. The verify-page GET only renders the form. Active linked accounts continue through normal login without another verification challenge.

Successful allauth login uses `LOGIN_REDIRECT_URL = "home"`, resolving to the existing `/` route. Do not rely on Django's default `/accounts/profile/`, which is not mounted, and do not use `/accounts/google/link/` as a login destination; that route is reserved for explicit authenticated account linking.

## 1. Locked architecture decisions

| Area | Decision |
|---|---|
| Backend language | Python 3.14.10 (selected runtime patch; update within the 3.14 series after security review) |
| Web framework | Django 5.2 LTS line; proposed pin `5.2.19` |
| API | Django REST Framework proposed pin `3.18.3` |
| Web UI | Django Templates + locally served Bootstrap 5.3.8 (MIT) |
| Database | PostgreSQL 16+ with PostGIS extension required by the accepted location-search design; not currently configured |
| Database driver | psycopg 3.3.8 (binary extra for the local academic environment; production packaging review remains required) |
| Cache/broker | Redis 7.x |
| Background jobs | Celery 5.7.0 |
| API filtering | django-filter 26.2 |
| API schema | drf-spectacular 0.30.0 |
| Web server | Nginx |
| WSGI server | Gunicorn 26.2.0 (see ADR-010; 23.x is no longer security-supported upstream) |
| Static files | Project-local assets collected and served with WhiteNoise 6.12.0 |
| Maps/location search | Find Donor provider remains unselected: proposed options are Google Maps JavaScript API and Places API (New), or Leaflet with an approved OSM-derived tile provider. P12-02 and P12-03 use a development-only browser picker on `/app/` and `/location-demo/`; it is UI only, not donor matching or a production provider decision. Browser geolocation is native and provider-independent. |
| Tests | pytest, pytest-django, Django TestCase, Playwright |
| Load tests | Locust |
| Containers | Docker Compose for local development |
| CI | GitHub Actions |
| Mobile future client | Flutter stable channel; version pinned when mobile phase begins |

### Version pin policy

The Django 5.2 series is selected as an LTS line. The selected baseline pins are Django `5.2.19` and DRF `3.18.3`; official release notes and package metadata were checked on 2026-11-06. Django 5.2 supports Python 3.14 (added in 5.2.8), and DRF 3.18.3 supports Django 5.2. Django 5.2.19 contains fixes for the security issues disclosed in 5.2.18, and DRF 3.18.3 includes the 3.18.2 security fixes. Keep the supported Django line aligned with DRF.

Other dependency versions above are compatibility targets, not a substitute for a resolved lock file. At bootstrap:
1. Verify current stable patch releases and security status.
2. Install compatible direct dependencies recorded in `requirements/base.in` and `requirements/dev.in`.
3. Use the pinned uv lock compiler to generate universal `requirements/base.lock` and `requirements/dev.lock` files (including transitive dependencies and hashes for supported target platforms).
4. Commit the lock file.
5. Record the exact resolved versions and verification evidence in `requirements/LOCK_REPORT.md`.
6. Do not float production dependencies.

Lock generation uses uv `0.13.7` with `uv pip compile --universal --generate-hashes --python-version 3.14`; pip-tools is not used because its hash resolver downloaded every platform artifact serially and timed out while resolving psycopg-binary.

Do not use Django development server in production.

## 2. Runtime and package layout

```text
bloodconnect-bd/
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── development.py
│   │   ├── test.py
│   │   └── production.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
├── apps/
│   ├── accounts/
│   ├── donors/
│   ├── requests/
│   ├── matching/
│   ├── connections/
│   ├── notifications/
│   ├── organizations/
│   ├── locations/
│   ├── moderation/
│   ├── analytics/
│   ├── audit/
│   └── integrations/
├── templates/
├── static/
├── media/                 # local development only; production private storage
├── tests/
├── docs/
├── requirements/
├── scripts/
├── Dockerfile
├── compose.yaml
├── manage.py
├── pyproject.toml
└── .env.example
```

Each Django app should own its models, migrations, selectors/query helpers, services, forms/serializers, views and tests as appropriate. Avoid circular imports and cross-app model logic.

## 3. Application boundaries

- `accounts`: custom user, authentication, account status, role membership.
- `donors`: donor profile, visibility and availability.
- `requests`: blood request lifecycle.
- `matching`: discovery filters only; no medical compatibility logic.
- `connections`: contact request state machine and accepted connection.
- `notifications`: in-app and external delivery.
- `locations`: administrative geography.
- `moderation`: reports, blocks and moderation cases.
- `organizations`: optional verified organization records.
- `audit`: security-relevant event records.
- `integrations`: adapters for OTP, SMS, email, map and future authorized APIs.
- `analytics`: aggregated metrics with privacy controls.

## 4. Authentication

### Web
- Django session authentication.
- Secure, HttpOnly, SameSite cookies.
- CSRF middleware enabled.
- Session rotation on login and privilege changes.
- Password reset through a verified channel.

### API/mobile
- DRF authentication with short-lived access token and rotating refresh token, using a maintained JWT package after compatibility review.
- Refresh token rotation and blacklist/revocation.
- Never store long-lived secrets in browser local storage.
- Mobile secure storage (Keychain/Android Keystore) in future Flutter app.
- API rate limits on login, OTP, refresh and sensitive endpoints.

Do not mix session and JWT policies accidentally. Document which endpoints accept which authentication method.

## 5. Authorization

- Role-based permissions plus object-level ownership checks.
- Default deny for private endpoints.
- A user may read/update only their own private profile and requests unless an explicit permission allows otherwise.
- A donor can act only on contact requests addressed to that donor.
- A recipient can cancel only their own pending contact request.
- Admin/moderator access is least-privilege and audited.
- Never trust a role or owner ID sent by the client.

## 6. Data access and RLS

MVP uses Django ORM and server-side authorization as the primary access boundary. Browser and mobile clients never connect directly to PostgreSQL.

PostgreSQL Row-Level Security (RLS) is **not enabled in MVP** because connection pooling, transaction-local identity context and migration behavior must be designed and tested carefully. If RLS is introduced later:
- Use a non-owner application database role.
- Set user context transaction-locally, not as persistent session state.
- Ensure context is reset safely under connection pooling.
- Test every policy, background job and admin workflow.
- Keep Django authorization even with RLS; RLS is defense in depth, not a replacement.

## 7. API conventions

- Prefix: `/api/v1/`.
- JSON request/response.
- ISO 8601 timestamps in UTC; render in Asia/Dhaka for users.
- UUID public identifiers.
- Pagination on list endpoints.
- Consistent error envelope.
- Explicit serializer allowlists; never serialize models wholesale.
- Idempotency for state-changing operations that may be retried.
- OpenAPI schema generated and reviewed.
- No private fields in public search endpoints.

## 8. Background processing

Celery tasks:
- Send notification after database transaction commits.
- Retry transient provider failures with bounded exponential backoff.
- Use idempotency keys to avoid duplicate sends.
- Store delivery state and provider reference without storing secrets.
- Expire pending contact requests and stale requests via scheduled jobs.
- Reconcile failed notifications.

A task failure must not roll back a successful contact-request database transaction. Use an outbox or durable notification record to avoid lost notifications.

## 9. External APIs and adapters

Potential adapters:
- Email provider.
- SMS/OTP provider.
- Map tile provider.
- Future authorized hospital/blood-bank directory.
- Future authorized DGHS FHIR endpoint.
- Future authorized identity verification.

All adapters require:
- Environment-based credentials.
- Connect/read timeouts.
- Retry policy only for safe/idempotent calls.
- Circuit-breaker or failure isolation where appropriate.
- Structured logs with sensitive fields redacted.
- Provider sandbox/mock for development.
- Documentation of authorization and data-sharing basis.

### Find Donor location flow (picker UI implemented; matching not implemented)

- Browser geolocation uses the browser Geolocation API after an explicit user gesture and permission; it does not require a Google API. Require a secure context in deployed environments and provide manual place/pin selection if permission is denied or unavailable.
- Google Maps JavaScript API may render the interactive map. Places API (New) may provide location and optional hospital autocomplete; the JavaScript Place Autocomplete Widget/Data API or the Places web service are alternatives. Place Details is needed only if selection requires additional place fields. Google Places Legacy must not be selected for a new project.
- Geocoding API is optional, only for converting a text address to coordinates or reverse-geocoding a pin for a human-readable label. It is not required when the selected place, browser or map already supplies coordinates.
- Current donor-profile picker scope (ADR-033): explicitly confirm a general area and grant separate `donor_area_storage` consent before storing private decimal coordinates, general-area label, optional Google Place ID, source (`GOOGLE_PLACE`, `GOOGLE_GEOCODE`, or `MAP_PIN`) and server-set timestamp. Do not request GPS or use these fields for matching. Only the authenticated owner's profile form may read/update the fields; public serializers and donor search do not include them. Map-only profiles remain excluded by the current administrative discovery requirements.
- A later, separately approved matching implementation may use PostGIS geography, a reviewed Bangladesh boundary, `ST_DWithin`, donor-location consent and coarse public distance bands as specified below. The profile-only scalar fields do not authorize matching, boundary imports, or migration/application of PostGIS changes.
- A future approved matching endpoint may accept requester-selected coordinates in a POST body, check them against the approved Bangladesh boundary, use them for that request only and never persist them in database records, logs, analytics, URLs or errors. The current donor-profile picker sends only the donor-entered place query and selected pin coordinates directly from the browser to Google Maps Platform for the requested map/geocoding operation; disclose this provider data flow. Do not send donor records, blood group or search results to map providers.
- Use PostGIS `geography(Point, 4326)` and server-side `ST_DWithin` for radius eligibility against donor-confirmed points; use `ST_Distance` only to select the public display band. Radius options are 5, 10, 20 and 50 km. Donor-confirmed coordinates are the only points that qualify a result for a selected radius.
- An administrative representative point may be used only for a donor with no confirmed point, and only for a separate, non-radius section labelled “Area matches — distance not verified.” Do not assign those donors a distance or imply that they are inside the selected radius. If the UI cannot clearly separate the section, omit them from radius results.
- Public results expose a generalized area and, for radius-qualified results only, one coarse approximate straight-line band: `<2 km`, `2–5 km`, `5–10 km`, `10–20 km`, `20–50 km`, or `>50 km`. This is not road/travel distance. Never return donor coordinates or exact address.
- Validate both requester and donor points against a reviewed Bangladesh `MultiPolygon` using PostGIS `ST_Covers`; reject outside points and fail closed if no approved boundary is active. Prefer a versioned, licensed boundary dataset; do not substitute a hand-written bounding box.
- `ST_DWithin` must define radius inclusion on exact server-side geography distance (boundary inclusive). Public bands are presentation only and must never affect eligibility.
- The client-side `/app/` picker and `/location-demo/` reuse the Google Maps/Places browser integration when `GOOGLE_MAPS_BROWSER_API_KEY` is configured in development. This does not implement a matching adapter or approve Google as a production provider. Provider failure leaves browser GPS and the existing administrative search available. PostGIS is not configured; no coordinate matching, production key or production provider is approved.
- An optional hospital lookup is a location-selection aid, not hospital verification, affiliation, inventory or a clinical filter. Do not send donor records or donor locations to a Places provider.
- Google billing is required for a Maps Platform project setup. Pricing is pay-as-you-go with per-SKU monthly free usage; verify current price, quotas, terms, attribution, caching/storage restrictions, regional terms and privacy disclosures before selection. Restrict browser keys by referrer and API; keep any server-side key in protected environment configuration, limit APIs/quotas and set budget alerts. Do not enable billing or APIs without owner approval.
- Lower-cost alternative: Leaflet with an approved OSM-derived tile provider or a separately operated tile service. OSM data licensing and tile-service terms are distinct; the public OSM tile servers are capacity-limited, best-effort, and impose attribution, caching and usage requirements. The provider must be switchable and must not be assumed to provide unlimited production capacity.
- Before implementation, confirm that the selected PostgreSQL deployment supports the required PostGIS extension and that a reviewed, licensed, versioned Bangladesh boundary dataset has explicit import/use approval. Do not substitute a hand-written bounding box or activate an unreviewed boundary.

## 10. Security constraints

See `07_Security.md`. At minimum:
- HTTPS in production.
- `DEBUG=False`.
- Strong `SECRET_KEY`.
- Allowed hosts and trusted origins configured.
- CSRF protection.
- Secure cookies and HSTS.
- ORM/parameterized queries.
- Template escaping.
- File upload allowlist, size limits and private storage.
- Rate limiting.
- Dependency scanning.
- Backup encryption and access control.
- No secrets in Git.

## 11. Scalability strategy

Initial architecture:
- Stateless Django web/API instances.
- PostgreSQL primary database.
- Redis cache and Celery broker.
- Object storage for uploaded documents.
- Nginx/load balancer.
- Horizontal application scaling when measured load requires it.

Optimization order:
1. Correct indexes and query plans.
2. Pagination and bounded result sets.
3. Eliminate N+1 queries.
4. Cache safe public/reference data.
5. Move slow work to Celery.
6. Add application replicas.
7. Tune database connections and connection pooling.
8. Add read replicas only when justified by measurements.

"100,000 registered users" is not a capacity benchmark. Define concurrent users, request mix, throughput, latency, error rate and test duration before making performance claims.

## 12. Observability

- JSON structured request logs with an allowlist that omits URL paths, query strings, message text and exception tracebacks.
- Server-generated request correlation ID returned as `X-Request-ID`.
- Error monitoring with PII scrubbing.
- Metrics: request count, latency, status codes, queue depth, task failures, DB pool saturation.
- Health endpoints: dependency-free `/health/live/` and dependency-aware `/health/ready/` (database and Redis reported separately; response is non-cacheable).
- Audit events for privileged and sensitive operations.
- Alerts for error spikes, queue backlog, failed backups and resource saturation.

## 13. Non-functional technical constraints

- Maintainable modular code.
- Deterministic migrations.
- Repeatable local environment.
- Test suite runs in CI.
- No production secrets in environment files committed to Git.
- Graceful failure when external providers are unavailable.
- Data export/deletion workflows subject to legal retention obligations.
