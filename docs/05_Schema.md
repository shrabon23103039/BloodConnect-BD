# 05 — Relational Database Schema

**Version:** 1.0  
**Database:** PostgreSQL 16+  
**Primary key policy:** UUID for externally addressable entities; integer/bigint acceptable for internal lookup tables if never exposed.

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
| `level` | varchar(20) | `DIVISION`, `DISTRICT`, `UPAZILA` |
| `parent_id` | UUID | FK self, nullable for division |
| `source_name` | varchar(120) | required |
| `source_version` | varchar(60) | required |
| `is_active` | boolean | default true |

Indexes:
- `(level, parent_id, is_active)`
- unique normalized name within parent and level.

### 3.3 `donors_donorprofile`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `user_id` | UUID | FK User, unique |
| `blood_group` | varchar(3) | enum A+, A-, B+, B-, AB+, AB-, O+, O- |
| `division_id` | UUID | FK Location, PROTECT |
| `district_id` | UUID | FK Location, PROTECT |
| `upazila_id` | UUID | FK Location, PROTECT, nullable |
| `availability_status` | varchar(20) | `UNAVAILABLE`, `AVAILABLE`, `PAUSED` |
| `public_alias` | varchar(80) | nullable |
| `visibility_enabled` | boolean | default false until consent |
| `preferred_contact_method` | varchar(20) | `IN_APP`, `PHONE_AFTER_ACCEPT`, `EMAIL_AFTER_ACCEPT` |
| `share_phone_after_accept` | boolean | default false |
| `share_email_after_accept` | boolean | default false |
| `last_donation_date` | date | nullable, self-reported |
| `profile_status` | varchar(20) | `DRAFT`, `ACTIVE`, `HIDDEN`, `SUSPENDED` |
| `availability_updated_at` | timestamptz | nullable |
| `created_at` | timestamptz | required |
| `updated_at` | timestamptz | required |

Indexes:
- `(blood_group, availability_status, profile_status)`
- `(district_id, blood_group, availability_status)`
- `(upazila_id, blood_group, availability_status)`
- `(visibility_enabled, profile_status)`

Rules:
- Donor must explicitly opt in before appearing in search.
- `AVAILABLE` means willing to receive contact requests, not medically eligible.
- Exact address and coordinates are not stored in MVP.
- Last donation date is optional self-reported information and must not be used to declare eligibility.

### 3.4 `requests_bloodrequest`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `requester_id` | UUID | FK User, PROTECT |
| `blood_group` | varchar(3) | required enum |
| `units_requested` | smallint | positive; informational only |
| `required_at` | timestamptz | required |
| `division_id` | UUID | FK Location, PROTECT |
| `district_id` | UUID | FK Location, PROTECT |
| `upazila_id` | UUID | FK Location, PROTECT, nullable |
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
- Prevent duplicate pending request for same recipient/donor/request combination using a conditional unique constraint where supported.
- Validate that donor and requester are not the same user.
- Validate that referenced request is open and owned by recipient.
- Accept/decline is atomic and idempotent.

### 3.6 `connections_connection`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `contact_request_id` | UUID | FK ContactRequest, unique |
| `status` | varchar(20) | `ACTIVE`, `CLOSED`, `REPORTED` |
| `created_at` | timestamptz | required |
| `closed_at` | timestamptz | nullable |

Create only after accepted contact request. Do not duplicate donor phone/email into this table; retrieve allowed fields through a permission-checked service at read time.

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
| `consent_type` | varchar(50) | e.g. donor_discovery, phone_share_after_accept |
| `policy_version` | varchar(30) | required |
| `granted` | boolean | required |
| `captured_at` | timestamptz | required |
| `withdrawn_at` | timestamptz | nullable |
| `source` | varchar(30) | `WEB`, `MOBILE`, `ADMIN` |

Do not overwrite historical consent. Create a new record for changes.

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
