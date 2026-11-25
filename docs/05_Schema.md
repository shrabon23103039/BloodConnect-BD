# 05 — Relational Database Schema

**Version:** 1.0  
**Database:** PostgreSQL 16+  
**Primary key policy:** UUID for externally addressable entities; integer/bigint acceptable for internal lookup tables if never exposed.

## Google social identity tables

P13-01 uses django-allauth's additive social tables: `socialaccount_socialaccount` maps the unique Google provider subject (`uid`, corresponding to `sub`) to `accounts_user`; `socialaccount_socialapp` stores optional database-backed provider configuration (this project uses environment/settings configuration); and `socialaccount_socialtoken` stores provider tokens (disabled by project settings). Sites integration is disabled, so no SocialApp/Site join table is created. The project custom signup uses `accounts_user.email` and its local verification fields directly, avoiding django-allauth's separate `account_emailaddress` table. The existing `accounts_user` schema is not changed by the `socialaccount` migration chain. The six socialaccount migrations depend on the already-applied custom user migration and already-applied core migrations and have been applied to the approved development database. They create the three socialaccount tables without changing `accounts_user`. The separate django-allauth `account` migrations remain unapplied; do not apply them as part of P13-01.

## 1. Conventions

- Table names use Django app/model naming unless a custom `db_table` is explicitly documented.
- `created_at` and `updated_at` use timezone-aware timestamps.
- Store timestamps in UTC.
- Use `PROTECT` for reference data that must not disappear while referenced.
- Use `CASCADE` only where dependent data is intended to be deleted together and retention policy permits it.
- Use `SET_NULL` only when historical records remain meaningful without the related object.
- Use database constraints for invariants where possible.
- Avoid storing unnecessary identity/health data.
- Never store plaintext passwords, OTPs, access tokens or refresh tokens.

## 2. Entity overview

```text
User 1---0..1 DonorProfile
Location 1---* Location (division/district with rural and city branches)
User 1---* BloodRequest
User 1---* ContactRequest (recipient)
DonorProfile 1---* ContactRequest (donor)
BloodRequest 1---* ContactRequest
ContactRequest 1---0..1 Connection
User 1---* Notification
User 1---* UserReport (reporter)
User 1---* UserBlock (blocker)
Organization 1---* OrganizationMembership
Location 1---* DonorProfile / BloodRequest / Organization
User 1---* ConsentRecord
User 1---* AuditEvent (actor, nullable for system events)
```

## 3. Tables

### 3.1 `accounts_user`

Custom Django user model. Create before first migration.

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `email` | varchar(254) | nullable only if phone auth selected; normalized unique when present |
| `phone_e164` | varchar(16) | nullable only if email auth selected; normalized unique when present |
| `password` | varchar(128) | Django encoded password |
| `display_name` | varchar(120) | required |
| `account_status` | varchar(20) | `PENDING`, `ACTIVE`, `SUSPENDED`, `DEACTIVATED` |
| `is_staff` | boolean | default false |
| `is_superuser` | boolean | default false |
| `email_verified_at` | timestamptz | nullable |
| `phone_verified_at` | timestamptz | nullable |
| `last_login` | timestamptz | nullable |
| `created_at` | timestamptz | required |
| `updated_at` | timestamptz | required |

Indexes/constraints:
- Unique normalized email when not null.
- Unique normalized phone when not null.
- Check: at least one login identifier exists.
- Index on `account_status`.

### 3.2 `locations_location`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `name_en` | varchar(120) | required |
| `name_bn` | varchar(120) | nullable |
| `level` | varchar(20) | `DIVISION`, `DISTRICT`, `UPAZILA`, `UNION`, `CITY_CORPORATION`, `ZONE`, `WARD` |
| `parent_id` | UUID | FK self; null for division; parent level validated by model/importer |
| `corporation_scope_id` | UUID | FK self, required for wards; makes ward names unique within a corporation across zones |
| `source_name` | varchar(120) | required |
| `source_version` | varchar(60) | required |
| `source_id` | varchar(32) | nullable; source-provided identifier, unique within source when present |
| `representative_latitude` | decimal(9,6) | nullable; reviewed area-only fallback point, never radius input |
| `representative_longitude` | decimal(9,6) | nullable; paired with `representative_latitude` |
| `representative_point_status` | varchar(16) | `UNVERIFIED` or `REVIEWED`; defaults to `UNVERIFIED` |
| `is_active` | boolean | default true |

Indexes:
- `(level, parent_id, is_active)`
- unique case-insensitive English name within parent and level, including division roots; ward names are additionally unique within their city corporation (not globally).
- Rural hierarchy: division -> district -> upazila -> union.
- City hierarchy: division -> district -> city corporation -> zone -> ward. A ward may be a direct city-corporation child where the reviewed source does not define zones.
- Check: divisions have no parent and all other supported levels have a parent. Model and importer validate permitted parent levels and the city-corporation scope.
- Representative coordinates are optional, source-attributed points for an administrative area (for example a reviewed centroid/interior point), not a donor point. They may support only the separate “Area matches — distance not verified” result section for donors without a confirmed point. They are never used by PostGIS radius eligibility and never receive a distance band. If the UI cannot clearly separate area matches, omit them from radius results. Latitude/longitude must be both null or both present and in range; `representative_point_status=REVIEWED` is required before display.
- Before a point is marked `REVIEWED`, retain its source/version, derivation method, reviewer and review date in the source record or a supporting provenance manifest. If the point source differs from the administrative-name source, record both. The current location importer does not establish this point-data contract; extend and test it explicitly before importing any points.

Import only an offline JSON snapshot with source name/version/URL and reviewer/date metadata. Optional `source_id` values are retained and unique per source; the importer does not assert that an ID is a government code. When an incoming record has a source ID, it matches only the same `(source_name, source_id)`; a name/path match to a different source or different/missing ID is rejected with instructions to reconcile the identity. Ambiguous name/path matches are also rejected. Name-based reuse without a source ID is allowed only when exactly one existing row has the same source name and no source ID. These rules prevent imports from silently adopting, relabeling or replacing a row's source identity. For a matched same-source identity, an import may update `name_bn` and `source_version`; it preserves the database primary key, English name, parent and source ID. Reactivation requires explicit `--activate`. `manage.py load_locations --file <snapshot.json> --reviewed` validates the complete hierarchy before writing and prints the input SHA-256 for provenance. Any representative-point data requires separate source/method/quality review and must not be trusted merely because it appears in a location snapshot. The bundled Open Admin Data candidate is CC BY 4.0 but is currently inactive pending reconciliation with 2026 administrative changes; it is not an official government dataset. Test fixtures are synthetic.

### 3.2.1 `locations_countryboundary` (proposed; required before coordinate search)

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `country_code` | char(2) | unique; `BD` for Bangladesh |
| `boundary` | geometry(MultiPolygon, 4326) | required; reviewed national boundary used for point-in-country validation |
| `source_name` | varchar(120) | required |
| `source_version` | varchar(60) | required |
| `source_url` | varchar(500) | required |
| `license_reference` | varchar(500) | required; reviewed terms/attribution record |
| `source_sha256` | char(64) | required; hash of the reviewed source artifact |
| `reviewed_by` | varchar(120) | required |
| `reviewed_at` | timestamptz | required |
| `approved_by` | varchar(120) | required before activation |
| `approved_at` | timestamptz | required before activation |
| `is_active` | boolean | default false; only an approved Bangladesh boundary may be active |

Indexes/constraints:
- GiST index on `boundary`.
- At most one active boundary per `country_code`.
- Validate requester and donor points with PostGIS `ST_Covers(boundary, point)`; do not use a hand-written bounding box.
- Do not create, download, import or activate a boundary as part of this documentation task. Review its source, license, version, hash and import/use approval first.

### 3.3 `donors_donorprofile`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `user_id` | UUID | FK User, unique |
| `blood_group` | varchar(3) | enum A+, A-, B+, B-, AB+, AB-, O+, O- |
| `division_id` | UUID | FK Location, PROTECT, nullable for map-only profile |
| `district_id` | UUID | FK Location, PROTECT, nullable for map-only profile |
| `upazila_id` | UUID | FK Location, PROTECT, nullable |
| `union_id` | UUID | FK Location, PROTECT, nullable; rural leaf below upazila |
| `city_corporation_id` | UUID | FK Location, PROTECT, nullable; mutually exclusive with rural upazila/union |
| `city_zone_id` | UUID | FK Location, PROTECT, nullable; child of selected city corporation |
| `ward_id` | UUID | FK Location, PROTECT, nullable; scoped to selected city corporation |
| `thana_name` | varchar(120) | optional self-reported address attribute; not verified, public, or searchable |
| `donation_area_label` | varchar(180) | blank until selected; donor-confirmed general-area label, private |
| `donation_area_latitude` | decimal(11,8) | nullable; donor-selected point, private |
| `donation_area_longitude` | decimal(11,8) | nullable; donor-selected point, private |
| `google_place_id` | varchar(256) | optional Google Place ID, private |
| `location_source` | varchar(20) | `GOOGLE_PLACE`, `GOOGLE_GEOCODE` or `MAP_PIN`; required with a saved point |
| `location_confirmed_at` | timestamptz | nullable; server-set time when the donor saved the confirmed area |
| `availability_status` | varchar(20) | `UNAVAILABLE`, `AVAILABLE`, `PAUSED`; default `UNAVAILABLE` |
| `public_alias` | varchar(80) | nullable |
| `visibility_enabled` | boolean | default false until consent |
| `preferred_contact_method` | varchar(20) | `IN_APP`, `PHONE_AFTER_ACCEPT`, `EMAIL_AFTER_ACCEPT`; default `IN_APP` |
| `share_phone_after_accept` | boolean | default false |
| `share_email_after_accept` | boolean | default false |
| `last_donation_date` | date | nullable, self-reported |
| `profile_status` | varchar(20) | `DRAFT`, `ACTIVE`, `HIDDEN`, `SUSPENDED`; default `DRAFT` |
| `availability_updated_at` | timestamptz | nullable |
| `created_at` | timestamptz | required |
| `updated_at` | timestamptz | required |

Indexes:
- `(blood_group, availability_status, profile_status)`
- `(district_id, blood_group, availability_status)`
- `(upazila_id, blood_group, availability_status)`
- `(city_corporation_id, ward_id, blood_group)`
- `(visibility_enabled, profile_status)`

Constraints and access:
- Latitude/longitude must both be null or both be present and within WGS84 coordinate ranges. A saved point requires a non-empty general-area label, allowed source and confirmation timestamp; an unsaved point requires related fields to be blank.
- The profile picker stores a point only after explicit confirmation and current, revocable `donor_area_storage` consent. The timestamp is set by the server, not accepted from the browser. The picker does not request GPS and does not implement distance matching.
- Only the owner's private profile form may read or update the point, Place ID, label, source and timestamp. Public donor/search serializers, templates, admin exports, logs and errors never include the point or Place ID. Clearing the area removes all point metadata and records consent withdrawal.
- The additive schema change makes division/district nullable without rewriting existing references. Existing administrative references are preserved when the owner saves without a map area; they are cleared only when the owner confirms and saves a replacement map area. Map-only profiles remain undiscoverable because current discovery requires valid administrative references.
- This profile-only scalar-coordinate schema is a temporary, SQLite-compatible implementation decision (ADR-033), not the planned PostGIS matching schema. Any conversion to PostGIS and use for search requires a separately approved migration and matching design.

Rules:
- Donor must explicitly opt in before appearing in search.
- `AVAILABLE` means willing to receive contact requests, not medically eligible.
- Do not store an exact street address. Donor-selected coordinates are private profile fields, not public fields and not presumed to be the donor's home. Confirmation is donor-provided, not independent location verification.
- Requester location-search coordinates are transient input and are never stored on a donor, request or connection.
- Server-side radius eligibility uses PostGIS `ST_DWithin` on donor-confirmed coordinates only. Administrative representative points are not a radius or distance fallback: when confirmed coordinates are absent, a reviewed area point may only support a separate “Area matches — distance not verified” section with no distance band or radius claim; omit it if the UI cannot separate the result type.
- A profile uses either a rural upazila/union or a city-corporation area; selecting a city corporation does not require a rural upazila. Thana text is self-reported only and is never included in donor discovery output.
- Last donation date is optional self-reported information and must not be used to declare eligibility.

### 3.4 `requests_bloodrequest`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `requester_id` | UUID | FK User, PROTECT |
| `blood_group` | varchar(3) | required enum |
| `units_requested` | smallint | positive; informational only |
| `required_at` | timestamptz | required |
| `division_id` | UUID | FK Location, PROTECT, nullable for map-selected request |
| `district_id` | UUID | FK Location, PROTECT, nullable for map-selected request |
| `upazila_id` | UUID | FK Location, PROTECT, nullable |
| `request_location_label` | varchar(180) | blank/default empty; requester-confirmed general-area label |
| `request_location_latitude` | decimal(11,8) | nullable; confirmed request point, private |
| `request_location_longitude` | decimal(11,8) | nullable; confirmed request point, private |
| `request_location_place_id` | varchar(256) | optional Google Place ID, private |
| `request_location_source` | varchar(20) | `GOOGLE_PLACE` or `MAP_PIN`; blank without a point |
| `request_location_confirmed_at` | timestamptz | nullable; server-set time of confirmation |
| `facility_name` | varchar(180) | nullable, user-entered |
| `facility_address` | varchar(300) | nullable, user-entered |
| `urgency` | varchar(20) | `NORMAL`, `URGENT` |
| `description` | varchar(1000) | nullable |
| `status` | varchar(20) | `DRAFT`, `OPEN`, `FULFILLED`, `CANCELLED`, `EXPIRED` |
| `public_listing_enabled` | boolean | default true, subject to moderation |
| `expires_at` | timestamptz | required |
| `created_at` | timestamptz | required |
| `updated_at` | timestamptz | required |

Indexes:
- `(status, blood_group, district_id, required_at)`
- `(requester_id, status, created_at DESC)`
- `(expires_at, status)`

Constraints:
- `units_requested > 0`
- `expires_at > created_at`
- Request coordinates must both be null or both present and within WGS84 ranges. A stored point requires a general-area label, allowed source and server-set confirmation time; a map-pin source cannot retain a Place ID.
- Division/district are both null or both present. A newly confirmed map location replaces the request's legacy administrative references; existing rows retain their current references during the additive migration.
- Coordinates and Place ID are private request fields. Public request read serializers expose only `request_location_label` and omit exact coordinates, Place ID and facility address/description. Legacy public area fields remain available when no map area is saved.
- State transitions enforced in service layer and tested.

### 3.5 `connections_contactrequest`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `recipient_id` | UUID | FK User, PROTECT |
| `donor_profile_id` | UUID | FK DonorProfile, PROTECT |
| `blood_request_id` | UUID | FK BloodRequest, PROTECT |
| `message` | varchar(500) | nullable |
| `status` | varchar(20) | `PENDING`, `ACCEPTED`, `DECLINED`, `CANCELLED`, `EXPIRED` |
| `expires_at` | timestamptz | required |
| `decided_at` | timestamptz | nullable |
| `created_at` | timestamptz | required |
| `updated_at` | timestamptz | required |

Indexes/constraints:
- `(donor_profile_id, status, created_at DESC)`
- `(recipient_id, status, created_at DESC)`
- `(blood_request_id, status)`
- Prevent duplicate pending request for same recipient/donor/request combination using a partial unique constraint on `(recipient_id, donor_profile_id, blood_request_id)` while status is `PENDING`.
- Validate that donor and requester are not the same user.
- Validate that referenced request is open and owned by recipient.
- A pending contact request expires at the earlier of 48 hours after creation or the associated blood request's expiry (ADR-021).
- Accept/decline/cancel transitions are atomic and repeated same-state commands are idempotent.

### 3.6 `connections_connection`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `contact_request_id` | UUID | FK ContactRequest, unique |
| `status` | varchar(20) | `ACTIVE`, `CLOSED`, `REPORTED` |
| `created_at` | timestamptz | required |
| `closed_at` | timestamptz | nullable |

Create atomically after contact request acceptance. Do not duplicate donor phone/email into this table; retrieve only verified, currently consented fields through the recipient-scoped disclosure service at read time. Contact consent withdrawal takes effect immediately.

### 3.7 `notifications_notification`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `recipient_id` | UUID | FK User, CASCADE subject to retention policy |
| `notification_type` | varchar(40) | controlled enum |
| `title` | varchar(120) | required |
| `body` | varchar(300) | minimized; no sensitive data |
| `resource_type` | varchar(40) | nullable |
| `resource_id` | UUID | nullable |
| `channel` | varchar(20) | `IN_APP`, `EMAIL`, `SMS`, `PUSH` |
| `delivery_status` | varchar(20) | `PENDING`, `SENT`, `FAILED`, `SKIPPED` |
| `read_at` | timestamptz | nullable |
| `provider_reference` | varchar(120) | nullable |
| `created_at` | timestamptz | required |

Indexes:
- `(recipient_id, read_at, created_at DESC)`
- `(delivery_status, created_at)`

### 3.8 `moderation_userreport`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `reporter_id` | UUID | FK User, PROTECT |
| `reported_user_id` | UUID | FK User, PROTECT |
| `reason` | varchar(40) | controlled enum |
| `description` | varchar(1000) | required |
| `status` | varchar(20) | `OPEN`, `UNDER_REVIEW`, `RESOLVED`, `DISMISSED` |
| `assigned_admin_id` | UUID | FK User, nullable |
| `resolution_note` | varchar(1000) | nullable |
| `created_at` | timestamptz | required |
| `resolved_at` | timestamptz | nullable |

### 3.9 `moderation_userblock`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `blocker_id` | UUID | FK User |
| `blocked_id` | UUID | FK User |
| `created_at` | timestamptz | required |

Constraints:
- unique `(blocker_id, blocked_id)`
- blocker != blocked.
- Apply block in both directions for new contact-request eligibility according to product policy.

### 3.10 `governance_consentrecord`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `user_id` | UUID | FK User |
| `consent_type` | varchar(50) | controlled purpose: terms/privacy acknowledgement, donor_discovery, donor_location_matching, optional_location_map_display, phone/email sharing, notifications, organization sharing |
| `policy_version` | varchar(30) | required |
| `granted` | boolean | required |
| `captured_at` | timestamptz | required |
| `withdrawn_at` | timestamptz | nullable; set on an explicit withdrawal event |
| `source` | varchar(30) | `WEB`, `MOBILE`, `ADMIN` |

Do not overwrite historical consent. Create a new record for each grant, refusal or withdrawal. Registration records separate Terms and Privacy acknowledgement versions. Development policy versions default to `draft-1` until reviewed policy revisions are approved. Privacy-setting choices default to denied and are not effective donor-discovery/contact permissions until those dependent features enforce them.

### 3.11 `audit_auditevent`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `actor_id` | UUID | FK User, nullable for system |
| `action` | varchar(80) | required |
| `resource_type` | varchar(60) | required |
| `resource_id` | UUID | nullable |
| `correlation_id` | UUID | nullable |
| `metadata_redacted` | JSONB | minimized, no secrets/PII |
| `created_at` | timestamptz | required |

Append-only from application perspective. Restrict access. Do not log private message bodies, tokens, OTPs or full contact details.

### 3.12 `organizations_organization` (future/optional)

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `name` | varchar(180) | required |
| `organization_type` | varchar(30) | `HOSPITAL`, `BLOOD_BANK`, `OTHER` |
| `public_address` | varchar(300) | required |
| `district_id` | UUID | FK Location |
| `public_phone` | varchar(16) | nullable, organization consent |
| `verification_status` | varchar(20) | `UNVERIFIED`, `PENDING`, `VERIFIED`, `REJECTED`, `SUSPENDED` |
| `verification_scope` | varchar(300) | nullable |
| `created_at` | timestamptz | required |

Verification is limited to organization identity/authorization scope. It does not verify live blood inventory or medical quality.

### 3.13 `organizations_membership` (future/optional)

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `organization_id` | UUID | FK Organization |
| `user_id` | UUID | FK User |
| `role` | varchar(30) | `OWNER`, `MANAGER`, `STAFF`, `VIEWER` |
| `status` | varchar(20) | `INVITED`, `ACTIVE`, `REVOKED` |
| `created_at` | timestamptz | required |

Unique `(organization_id, user_id)`.

### 3.14 `accounts_verificationchallenge`

Short-lived challenge metadata for verifying an account identifier or confirming a phone password-reset request. The destination is resolved from the related account and is not copied into this table.

### 3.15 `api_apiaccesstoken` and `api_apirefreshtoken`

API credentials are opaque random bearer values. Store only a SHA-256 digest; the raw secret is returned once and never persisted or logged.

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `user_id` | UUID | FK User, cascade on account deletion |
| `token_digest` | char(64) | unique, required |
| `family_id` | UUID | required; indexes token-family revocation |
| `created_at` | timestamptz | required |
| `expires_at` | timestamptz | required |
| `revoked_at` | timestamptz | nullable |
| `used_at` | timestamptz | refresh table only; set once on rotation |

Access token lifetime is 15 minutes; refresh lifetime is 30 days. Refresh reuse revokes the whole family. Cleanup/retention of expired rows must be operationally configured. See ADR-029.

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `user_id` | UUID | FK User, CASCADE |
| `purpose` | varchar(20) | `ACCOUNT`, `PASSWORD_RESET` |
| `channel` | varchar(10) | `EMAIL`, `PHONE` |
| `code_digest` | varchar(64) | keyed HMAC digest; never plaintext |
| `failed_attempts` | smallint | 0 through 5 |
| `created_at` | timestamptz | required |
| `expires_at` | timestamptz | greater than `created_at`; 10-minute lifetime |
| `consumed_at` | timestamptz | nullable; terminal after use/invalidation |

Indexes: `(user_id, purpose, created_at)`, `(created_at)` and `(expires_at)`. A resend invalidates the previous outstanding challenge. Challenge delivery destination and code are not persisted in the database. Run `manage.py purge_verification_challenges` at least daily to remove challenge metadata more than 24 hours past expiry.

## 4. Authentication and authorization flow

### Web
1. User submits credentials over HTTPS.
2. Django authenticates and creates a session.
3. Session cookie is Secure, HttpOnly and SameSite.
4. CSRF token is required for unsafe methods.
5. Every view/service checks authentication, role and object ownership.

### Mobile/API
1. User authenticates through `/api/v1/auth/token/`.
2. API returns short-lived access token and refresh token.
3. Refresh token rotation/revocation is enabled.
4. Mobile stores tokens in platform secure storage.
5. API validates token and checks permissions on every request.

## 5. RLS / row-level security decision

- No direct database access from browser/mobile.
- Django ORM and server-side authorization are mandatory.
- PostgreSQL RLS is not part of MVP.
- RLS may be added later as defense in depth after connection-pool and transaction-context design is tested.
- Never assume RLS is active merely because the database supports it.

## 6. Data lifecycle

- Define retention periods before production.
- User deactivation hides profile immediately.
- Deletion requests are evaluated against legal, safety, fraud and audit retention duties.
- Minimize retained personal data.
- Avoid irreversible deletion where a lawful retention obligation exists; document the basis.
- Backups have a defined expiry and access policy.
