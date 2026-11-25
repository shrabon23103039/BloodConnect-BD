# 07 — Security Requirements and Threat Model

## 1. Security objectives

### Google OAuth

Use server-side Authorization Code Flow, state and PKCE; validate Google's issuer, configured audience, expiry, subject and verified-email claim through django-allauth. Google documents `nonce` as optional when `response_type=code`; this allauth code-only flow uses state and PKCE and does not send a nonce. Keep credentials backend-only and provider tokens out of persistent storage. Disable automatic email authentication/connection. Require explicit authenticated linking and reject identity/email collisions and inactive accounts. Google email does not set local verification fields, phone verification, account status, donor status or donor eligibility. A newly created pending Google account uses its provider email to request a local verification challenge, which must still be consumed before activation. Reuse a live challenge under the per-user lock on callback retry; do not send on verification-page GET. OAuth initiation/callback are IP-throttled, and initiation is a CSRF-protected POST.

Protect account access, donor privacy, request integrity, consent and service availability. Apply least privilege and defense in depth.

## 2. Assets

- Authentication credentials and session/token material.
- Donor identity and contact details.
- Donor blood-group and self-reported profile data.
- Donor-confirmed location coordinates stored privately for server-side matching.
- Recipient requests and free-text descriptions.
- Contact-request decisions.
- Moderation reports.
- Consent history.
- Admin actions and audit events.
- External provider credentials.

## 3. Threat actors

- Unauthenticated scraper.
- Malicious registered user.
- Fake donor or requester.
- Abusive user attempting harassment.
- Compromised administrator account.
- External provider compromise.
- Accidental internal disclosure.

## 4. Main threats and controls

| Threat | Control |
|---|---|
| Donor data scraping | Authentication where appropriate, pagination, throttling, minimal public fields |
| Donor-coordinate disclosure or triangulation | Owner-only profile access, server-side matching, strict public serializer allowlists, coarse distance output, rate limits, and coordinate/body redaction in logs |
| Invalid or misleading location matches | PostGIS validation against an approved Bangladesh boundary; exact radius eligibility uses donor-confirmed points only; area-only results are explicitly separated |
| Contact harvesting | Contact request gate; no public phone/email |
| Account takeover | Strong password hashing, verification, throttling, secure sessions, optional MFA for admins |
| IDOR/BOLA | Object-level authorization on every endpoint |
| Fake emergency requests | Reporting, moderation, rate limits, duplicate detection |
| OTP abuse | Per-account/IP/device throttling, expiry, one-time use |
| CSRF | Django CSRF middleware and secure cookie policy |
| XSS | Template escaping, safe rendering, content sanitization |
| SQL injection | ORM and parameterized SQL only |
| File upload abuse | Allowlist, size limits, content inspection, private storage |
| Admin misuse | Least privilege, MFA where available, immutable audit events |
| Provider compromise | Adapter isolation, secret rotation, minimum scopes |
| Data loss | Encrypted backups and restore tests |
| Denial of service | Rate limits, request size limits, reverse-proxy protections, monitoring |

## 5. Privacy boundaries

Public donor search must never return:
- phone number;
- email;
- exact home address;
- precise GPS coordinates;
- identity documents;
- private notes;
- verification evidence.

For the profile-only picker, donor-selected coordinates, general-area label, optional Place ID and source may be stored privately only after explicit confirmation and separate, revocable `donor_area_storage` consent. Do not request browser GPS or use these fields for matching. The browser sends the donor's place query and selected pin coordinates directly to Google Maps Platform only for the requested map/geocoding operation; disclose this provider data flow and do not send donor records, blood group or search results. Only the donor's own profile flow may read or update the saved fields. Public APIs, donor search results, public templates, admin exports, logs and errors never expose donor coordinates, Place IDs or exact addresses. The later PostGIS matching design remains a separate, unimplemented decision. Before donor acceptance, recipient sees only the donor's consented public profile. After acceptance, reveal only the contact method explicitly selected by the donor.

For blood requests, store the requester's selected point and optional Place ID privately only after explicit area confirmation. Treat the map label as user-controlled: public API serializers must not expose it because it may contain a precise address. Only legacy reviewed administrative labels may be public until an approved server-side generalization source exists. Never include coordinates or Place ID in public serializers, templates, logs, analytics or errors. The owner may see their own map label. The request location is separate from optional facility name/address text. The browser sends only the user's place query and selected Places details directly to Google; do not request GPS or Geocoding.

Coordinate storage does not authorize coordinate-based donor matching. Matching remains disabled until an authoritative Bangladesh boundary dataset is reviewed and approved and server-side boundary-inclusive validation is implemented. Global latitude/longitude range checks are not a Bangladesh boundary check; client-side map limits are not security validation.

## 6. Sensitive action requirements

- Contact-request accept/decline must be authenticated and authorized.
- State transition and audit record must be atomic.
- Sensitive profile changes require re-authentication where appropriate.
- A successful password reset rotates the anonymous reset session before granting reset authority, preserves unrelated session state, and revokes all API access/refresh token families atomically with the password update.
- Donor area updates require explicit confirmation and active storage consent; clearing the area immediately clears the point, label, Place ID, source and confirmation timestamp.
- Deactivation immediately excludes the donor from every match type. Account deletion removes precise coordinates from the active database.
- Admin exports must be permission-gated and audited.
- Logs must redact phone, email, tokens, OTP, message content, donor coordinates and Place IDs; do not emit coordinates in validation errors or analytics.
- Reject requester and donor points outside the approved, reviewed Bangladesh boundary and fail closed if no approved boundary is active. Review the boundary source, license, version and import/use approval before implementation; do not use a hand-written bounding box.
- Apply a proposed maximum 30-day purge window to backups containing deleted/revoked precise coordinates, subject to final privacy/legal policy. Backups and restore workflows must not retain those coordinates beyond that deadline.

## 7. Operational controls

- Separate development, staging and production secrets.
- Secret manager or protected environment variables.
- Dependency scanning in CI.
- Regular patch review.
- Backup encryption and access control.
- Restore drills.
- Incident response owner and escalation process.
- Security contact and vulnerability-reporting process before public launch.

## 8. Release blockers

Do not launch publicly if:
- private donor fields are exposed by any route/API;
- object-level authorization is missing;
- production DEBUG is enabled;
- secrets are committed;
- critical/high vulnerabilities remain without accepted mitigation;
- backups cannot be restored;
- privacy notice/consent is absent;
- the platform presents itself as a medical authority.
