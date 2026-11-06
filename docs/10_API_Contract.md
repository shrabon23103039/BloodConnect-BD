# 10 — API Contract (MVP Baseline)

**Base path:** `/api/v1/`  
**Format:** JSON  
**Time:** ISO 8601 UTC  
**IDs:** UUID public IDs  
**Authentication:** DRF configured auth; session for web and token strategy for mobile/API clients.

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

### Blood requests
- `GET /blood-requests/`
- `POST /blood-requests/`
- `GET /blood-requests/{public_id}/`
- `PATCH /blood-requests/{public_id}/`
- `POST /blood-requests/{public_id}/cancel/`
- `POST /blood-requests/{public_id}/close/`

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
- `GET /locations/divisions/`
- `GET /locations/districts/?division={id}`
- `GET /locations/upazilas/?district={id}`

## 4. Donor search query

Example:
`GET /api/v1/donors/?blood_group=O%2B&district={uuid}&availability=AVAILABLE&page=1`

Allowed filters:
- exact `blood_group`;
- `division`;
- `district`;
- `upazila`;
- `availability` (only public discoverable states).

Do not accept arbitrary ordering fields or unbounded page sizes.

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
