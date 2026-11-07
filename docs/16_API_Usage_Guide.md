# BloodConnect BD API Usage Guide

**Version:** `/api/v1/`
**Status:** Routes implemented through P7-03; the OpenAPI schema is generated from the running application.
**Data:** Use synthetic accounts and values in development. Never put bearer tokens in logs, screenshots or source control.

## Base URL and schema

Local development uses `http://localhost:8000`. Deployments must use HTTPS. The version root is `GET /api/v1/`; the generated OpenAPI document is at `GET /api/v1/schema/?format=json`.

List endpoints use page-number pagination with a default page size of 20. Use `?page=2` for the next page. Donor search accepts exact `blood_group`, `division`, `district`, `upazila` and `availability` filters; only current discoverable/available profiles are returned.

## Obtain and use an API token

Use an active, verified development account. The sample identifier and password below are placeholders.

```sh
curl -X POST http://localhost:8000/api/v1/auth/token/ \
  -H 'Content-Type: application/json' \
  -d '{"identifier":"developer@example.test","password":"<local-password>"}'
```

The response contains `access_token`, `refresh_token`, `token_type` (`Bearer`) and `expires_in` (900 seconds). Send the access token in the `Authorization: Bearer <access_token>` header. Access tokens expire after 15 minutes; refresh tokens expire after 30 days.

```sh
curl -X POST http://localhost:8000/api/v1/auth/token/refresh/ \
  -H 'Content-Type: application/json' \
  -d '{"refresh_token":"<current-refresh-token>"}'
```

Refresh rotates the pair. Replace both client-side values and discard the old pair. Reuse of an already rotated refresh token revokes the token family. Revoke a family when signing out:

```sh
curl -X POST http://localhost:8000/api/v1/auth/token/revoke/ \
  -H 'Content-Type: application/json' \
  -d '{"refresh_token":"<current-refresh-token>"}'
```

## Donor discovery

Donor search is available to guests and authenticated callers. It returns only the public alias, exact blood group, availability and the same administrative location names shown by the web search. It never returns email, phone, account name or donor contact preferences. Current discovery consent is checked on every query.

```sh
curl 'http://localhost:8000/api/v1/donors/?blood_group=O%2B&district=<district-uuid>&page=1'
```

## Blood requests

Public listing and detail routes include only open, public requests. A caller may create, edit, view or close their own requests with a bearer token. Owner responses may include the owner's facility and description fields; public responses omit them.

```sh
curl -X POST http://localhost:8000/api/v1/blood-requests/ \
  -H 'Authorization: Bearer <access-token>' \
  -H 'Content-Type: application/json' \
  -d '{
    "blood_group":"O+",
    "units_requested":1,
    "required_at":"2026-11-20T10:00:00Z",
    "division":"<division-uuid>",
    "district":"<district-uuid>",
    "upazila":"<upazila-uuid>",
    "facility_name":"Synthetic clinic",
    "facility_address":"Synthetic facility address",
    "urgency":"NORMAL",
    "description":"Synthetic coordination request",
    "public_listing_enabled":true,
    "expires_at":"2026-11-22T10:00:00Z"
  }'
```

Replace the example UUIDs with IDs from the application's location data and use future times. The response ID is the `blood_request_id` for contact requests.

## Contact requests and disclosure

Only active recipients may create a contact request. A donor accepts, declines or the recipient cancels using a POST action. Before acceptance, contact is `null`. After acceptance, recipient detail/connection responses recheck the donor's current verified channel and consent; only those channels may appear. The request message is visible only to the two participants.

```sh
curl -X POST http://localhost:8000/api/v1/contact-requests/ \
  -H 'Authorization: Bearer <recipient-access-token>' \
  -H 'Content-Type: application/json' \
  -d '{
    "donor_id":"<donor-profile-uuid>",
    "blood_request_id":"<blood-request-uuid>",
    "message":"Synthetic request message"
  }'
```

The donor uses their own token to accept:

```sh
curl -X POST 'http://localhost:8000/api/v1/contact-requests/<contact-request-uuid>/accept/' \
  -H 'Authorization: Bearer <donor-access-token>'
```

The recipient can then retrieve the participant-scoped detail:

```sh
curl 'http://localhost:8000/api/v1/contact-requests/<contact-request-uuid>/' \
  -H 'Authorization: Bearer <recipient-access-token>'
```

The response's `contact` value is `null` before acceptance and otherwise contains only currently consented channels. Consent withdrawal immediately removes the relevant value. Contact and connection actions are also available at the OpenAPI routes.

## Errors and limits

DRF errors use the documented `error` envelope with a generic message, optional field errors and a request ID. The `X-Request-ID` header carries the same ID. Rate limits return HTTP 429 with `error.code: RATE_LIMITED` and a `Retry-After` header. Development uses process-local throttling; production requires the configured shared Redis cache.

## Routes not yet implemented

The broader endpoint inventory in [`10_API_Contract.md`](10_API_Contract.md) includes future targets such as API registration/verification, `/me/`, donor-profile mutation, notifications, moderation, and location lookup. They are not part of the current mounted API; use the server-rendered web flows for those capabilities until their plan tasks are verified.
