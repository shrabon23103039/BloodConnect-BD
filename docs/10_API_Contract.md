# 10 — API Contract (MVP Baseline)

**Base path:** `/api/v1/`  
**Format:** JSON  
**Time:** ISO 8601 UTC  
**IDs:** UUID public IDs  
**Authentication:** DRF configured auth; session for web and token strategy for mobile/API clients.

**Implementation status (2026-11-07):** See [`16_API_Usage_Guide.md`](16_API_Usage_Guide.md) for routes currently mounted and tested. Routes below marked as an endpoint inventory describe the target contract; routes not in the guide are not implemented and may return 404.

## 1. Conventions

- Use explicit serializers with allowlisted fields.
- Paginate list responses.
- Use consistent status codes.
- Validate all input server-side.
- Enforce object-level permissions.
- Never expose private donor fields in search endpoints.
- State-changing operations must be idempotent where retries are possible.
- Include request/correlation ID in error responses.

## 2. Error envelope

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Please review the submitted information.",
    "fields": {
      "blood_group": ["Select a valid blood group."]
    },
    "request_id": "uuid"
  }
}
```

Do not include stack traces, SQL, tokens, OTPs or private record details.
The current API returns this envelope for DRF exceptions and includes the same request ID in the `X-Request-ID` response header. Rate-limit responses use `RATE_LIMITED` and include `Retry-After`.

## 3. Endpoint inventory

### Authentication
- `POST /auth/register/`
- `POST /auth/login/` (web session flow may remain Django-native)
- `POST /auth/logout/`
- `POST /auth/verify/`
- `POST /auth/verify/resend/`
- `POST /auth/password-reset/`
- `POST /auth/token/` (API/mobile token issuance)
- `POST /auth/token/refresh/`
- `POST /auth/token/revoke/`

API-client token routes are available under `/api/v1/`. `POST /auth/token/` accepts `{ "identifier": "...", "password": "..." }`; successful authentication returns opaque `access_token` and `refresh_token` values, `token_type: "Bearer"` and `expires_in: 900`. Send access tokens in `Authorization: Bearer <access_token>`. `POST /auth/token/refresh/` accepts the current refresh token and rotates both values; clients must discard the old pair. Reuse of a rotated refresh token revokes that token family. `POST /auth/token/revoke/` revokes the family and is idempotent. Access expires after 15 minutes; refresh expires after 30 days. Token storage/retention and TLS requirements are detailed in ADR-029.

### Current user
- `GET /me/`
- `PATCH /me/`
- `POST /me/deactivation/`
- `GET /me/consents/`
- `POST /me/consents/`

### Donors
- `GET /donors/` — public allowlisted filters only.
- `GET /donors/{public_id}/`
- `POST /donor-profile/`
- `GET /donor-profile/me/`
- `PATCH /donor-profile/me/`
- `POST /donor-profile/me/availability/`
- `POST /donor-profile/me/visibility/`

#### Future donor-location API and matching contract (not implemented)

The current profile-only Google Maps picker stores scalar location fields on the Django model through the server-rendered owner form. These fields are not accepted or returned by the current donor-profile API (no private profile API is implemented), are not included in public serializers, and are not used for matching. Any API support requires a separately reviewed contract and authorization tests.

The following is a future matching/API proposal, not a contract for the current picker. If approved, the donor's authenticated `POST /donor-profile/` or `PATCH /donor-profile/me/` may accept a donor-selected point only after explicit confirmation and active `donor_location_matching` consent:

```json
{
  "confirmed_location": {
    "latitude": 23.0000,
    "longitude": 90.0000
  },
  "location_source": "GPS",
  "location_accuracy_m": 42.0
}
```

These are synthetic values. `location_source` is `GPS` or `MAP_PIN`; GPS accuracy must be <=100 m, while a map pin requires an explicit donor confirmation. The server sets the confirmation/update timestamp; do not accept it from the client. Check the point against the approved Bangladesh boundary and reject it if outside. `GET /donor-profile/me/` may return the saved point, source, accuracy and timestamp only to its owner so they can review/edit it. The public `GET /donors/{public_id}/`, donor search response, other users' endpoints, admin exports, logs and notifications must never return the coordinates or exact address.

`POST /me/consents/` records an explicit `donor_location_matching` grant or withdrawal. A generic map-display preference is not permission to store donor coordinates. Profile create/update must reject a coordinate pair unless the donor has confirmed it and the matching-consent grant is active.

On consent withdrawal, clear the point and its source/accuracy/timestamp and immediately exclude it from matching. Donor deactivation excludes the profile from all match types. Account deletion clears the precise point from the active database.

### Blood requests
- `GET /blood-requests/`
- `POST /blood-requests/`
- `GET /blood-requests/{public_id}/`
- `PATCH /blood-requests/{public_id}/`
- `POST /blood-requests/{public_id}/cancel/`
- `POST /blood-requests/{public_id}/close/`

Public request read responses include nullable `request_location_label`. When a confirmed map area is saved, the public response uses that label and returns `division`, `district` and `upazila` as null; legacy requests continue to return their administrative labels. Neither public nor owner read serializers return request coordinates, Place ID, source or confirmation timestamp. Public responses continue to omit requester identity and facility/address/description fields. The server-rendered request form currently accepts the Places-selected location; API writes retain the existing administrative location contract.

### Contact requests
- `GET /contact-requests/incoming/`
- `GET /contact-requests/outgoing/`
- `POST /contact-requests/`
- `GET /contact-requests/{public_id}/`
- `POST /contact-requests/{public_id}/accept/`
- `POST /contact-requests/{public_id}/decline/`
- `POST /contact-requests/{public_id}/cancel/`

### Connections
- `GET /connections/`
- `GET /connections/{public_id}/`
- `POST /connections/{public_id}/close/`

### Notifications
- `GET /notifications/`
- `POST /notifications/{public_id}/read/`
- `PATCH /notification-preferences/`

### Moderation
- `POST /reports/`
- `GET /me/reports/`
- `POST /users/{public_id}/block/`
- `DELETE /users/{public_id}/block/`

### Locations

The current browser selector uses `GET /app/location-options/options/{level}/?parent={uuid}` (outside `/api/v1/`) to return active child locations as `{"results":[{"id":"uuid","name_en":"..."}]}`. Supported child levels are district, upazila, union, city corporation, zone and ward, subject to valid parent levels. It supplies administrative choices only; it does not resolve text places, browser coordinates or map pins. The `/api/v1/locations/...` entries in the original target inventory are not the current browser selector endpoint.

### Proposed coordinate-based donor search (not implemented)

`POST /api/v1/donors/search/` is proposed for the revised location-first flow. The existing `GET /api/v1/donors/` query remains the current administrative-filter baseline until a separately reviewed implementation replaces or deprecates it.

Request body (synthetic coordinate values):
```json
{
  "location": {
    "latitude": 23.0000,
    "longitude": 90.0000
  },
  "blood_group": "O+",
  "radius_km": 10,
  "administrative_filters": {}
}
```

`location.latitude` and `location.longitude` are the requester's required confirmed search point; validate numeric type and check with PostGIS `ST_Covers` against the approved Bangladesh boundary. Reject points outside that boundary; fail closed if no approved boundary is active. This point is transient input and must never be persisted in database records, analytics, URLs, logs or error messages. `blood_group` may be omitted for “Any blood group” pending product decision. `radius_km` is optional and, when present, must be one of 5, 10, 20 or 50. `include_area_matches` is optional and defaults to false; set it only when the client can clearly render the separate “Area matches — distance not verified” section. The optional hospital/place lookup is a client-side way to select the confirmed center; do not require or persist a provider place ID/name for donor matching unless separately approved. The omitted-radius behavior remains undecided.

The backend uses PostGIS `ST_DWithin` against donor-confirmed geography points for radius eligibility; exact server-side distance determines inclusion (boundary inclusive). Administrative representative points never qualify a donor for the radius or receive a distance. If `include_area_matches=true`, return eligible area-only candidates separately and without distance; they must not be described as within the selected radius. If the client cannot separate them, omit them.

Response shape (illustrative; not an implemented contract):
```json
{
  "results": [
    {
      "id": "public-uuid",
      "blood_group": "O+",
      "area_label": "Generalized administrative area",
      "approximate_distance_band": "2–5 km",
      "availability": "AVAILABLE"
    }
  ],
  "area_matches": [
    {
      "id": "public-uuid",
      "blood_group": "O+",
      "area_label": "Generalized administrative area",
      "availability": "AVAILABLE"
    }
  ],
  "next": null
}
```

Only radius-qualified `results` may include an `approximate_distance_band`, selected from `<2 km`, `2–5 km`, `5–10 km`, `10–20 km`, `20–50 km`, `>50 km`. Use the exact PostGIS distance for radius filtering; bands are presentation only. The bands mean `<2, [2,5), [5,10), [10,20), [20,50], >50` km respectively. State in the UI that this is approximate straight-line distance, not road/travel distance. `area_matches` never contain a distance or radius-qualified flag and are shown only under the exact separate heading “Area matches — distance not verified.” Never return donor latitude/longitude, exact address or private contact channels. Availability is restricted to public discoverable states and defaults to available profiles only.

## 4. Existing donor search query

Example:
`GET /api/v1/donors/?blood_group=O%2B&district={uuid}&page=1`

Existing `GET` filters:
- exact `blood_group`;
- `division`;
- `district`;
- `upazila`;
- `union`;
- `city_corporation`;
- `city_zone`;
- `ward`.

The API always returns available, discoverable donors; availability is not a user-selectable API filter. This is the currently implemented administrative-filter baseline and does not provide coordinate or radius search. Do not accept arbitrary ordering fields or unbounded page sizes. The proposed POST search must apply equivalent privacy, authorization, pagination and rate-limit controls.

## 5. Contact request payload

```json
{
  "donor_id": "public-uuid",
  "blood_request_id": "public-uuid",
  "message": "Please contact me if you are available."
}
```

Response:
```json
{
  "id": "public-uuid",
  "status": "PENDING",
  "created_at": "2026-11-06T12:00:00Z",
  "expires_at": "2026-11-07T12:00:00Z"
}
```

No donor phone/email is returned.

## 6. Accept response

Before donor acceptance:
```json
{
  "id": "public-uuid",
  "status": "PENDING",
  "contact": null
}
```

After acceptance, only explicitly consented fields may be returned to the authorized participants:
```json
{
  "id": "public-uuid",
  "status": "ACCEPTED",
  "contact": {
    "method": "PHONE",
    "value": "+8801XXXXXXXXX"
  }
}
```

The example is illustrative only. Never use a real phone number in fixtures or documentation.

## 7. HTTP status guidance

- `200`: successful read/action.
- `201`: created.
- `202`: accepted for asynchronous processing.
- `204`: successful no-content action.
- `400`: validation error.
- `401`: authentication required.
- `403`: authenticated but forbidden.
- `404`: missing or intentionally undisclosed private resource.
- `409`: conflicting state or duplicate operation.
- `429`: rate limit.
- `500`: generic server failure with request ID.

## 8. API versioning and change policy

- Breaking contract changes require a new version or documented migration.
- Additive optional fields may be backward-compatible.
- Keep OpenAPI schema committed/generated in CI.
- Add contract tests for all critical state transitions.
