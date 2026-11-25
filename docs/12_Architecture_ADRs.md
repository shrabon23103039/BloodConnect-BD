# 12 — Architecture Decision Records (ADRs)

Record important decisions here. New decisions should be appended, not silently substituted.

## ADR-001 — Modular monolith for MVP

**Status:** Accepted  
**Decision:** Use one Django deployment with clearly separated Django apps.  
**Reason:** Appropriate for one primary developer, faster delivery, simpler operations and sufficient scale path.  
**Consequences:** Keep module boundaries explicit; extract services only when measured operational needs justify it.

## ADR-002 — P2P-first product model

**Status:** Accepted  
**Decision:** Donor-to-recipient coordination is the core workflow; hospital participation is optional.  
**Reason:** MVP must function without external institutional partnerships.  
**Consequences:** Do not make hospital accounts or integrations a dependency for core flows.

## ADR-003 — Consent-gated donor contact

**Status:** Accepted  
**Decision:** Recipient sends contact request; donor explicitly accepts before consented contact channels are disclosed.  
**Reason:** Reduce scraping, spam and unwanted disclosure.  
**Consequences:** Implement state machine, audit trail, rate limits and object-level permissions.

## ADR-004 — Django templates + Bootstrap for web MVP

**Status:** Accepted  
**Decision:** Use server-rendered Django templates and Bootstrap; expose DRF APIs for mobile/future clients.  
**Reason:** One developer can deliver a maintainable web product without separate frontend deployment.  
**Consequences:** Keep UI components reusable and API contracts independent of templates.

## ADR-005 — PostgreSQL as system of record

**Status:** Accepted  
**Decision:** Use PostgreSQL and Django ORM.  
**Reason:** Relational constraints, transactions, indexing and mature operational tooling.  
**Consequences:** No direct client database access.

## ADR-006 — No PostgreSQL RLS in MVP

**Status:** Accepted  
**Decision:** Use server-side Django authorization; evaluate RLS later as defense in depth.  
**Reason:** RLS with pooling and transaction identity context adds complexity and must be deliberately tested.  
**Consequences:** Every query and endpoint must enforce owner/role access. RLS can be added after a dedicated design review.

## ADR-007 — Flutter as future mobile client

**Status:** Accepted  
**Decision:** Build responsive web MVP first; use DRF API for future Flutter Android/iOS client.  
**Reason:** Avoid parallel web/mobile implementation before product workflows are stable.  
**Consequences:** API contract, auth and pagination must be mobile-ready.

## ADR-008 — No medical compatibility engine

**Status:** Accepted  
**Decision:** Search by exact requested blood-group label and location only; do not implement transfusion compatibility or eligibility rules.  
**Reason:** These are clinical decisions requiring professional assessment.  
**Consequences:** Product language must consistently say "potential donor".

## ADR-009 — External integrations behind adapters

**Status:** Accepted  
**Decision:** Email, SMS, map, hospital, identity and DGHS integrations use adapters.  
**Reason:** Credentials, authorization and provider availability are uncertain.  
**Consequences:** Mock adapters in development; production integration disabled until approved.

## ADR-010 — Use a security-supported Gunicorn release

**Status:** Accepted
**Date:** 2026-11-06
**Context:** The TRD proposed Gunicorn 23.x. Upstream's security policy marks 23.0.0 unsupported, while the current supported release line is 26.x.
**Decision:** Pin the latest published and supported Gunicorn release verified for the lock (26.2.0 at review time); keep Gunicorn as the WSGI server behind Nginx.
**Reason:** A pinned release that upstream no longer security supports is not an acceptable production baseline. The version update preserves the approved deployment architecture.
**Alternatives:** Keep 23.0.0 and accept unsupported security maintenance (rejected); switch WSGI server (unnecessary architecture change).
**Consequences:** Review upstream support before future upgrades; Gunicorn is used on supported POSIX deployment platforms and omitted from Windows environments by a platform marker.
**Related documents:** `docs/04_TRD.md`, `requirements/LOCK_REPORT.md`.

## ADR-011 — Target an installable, supported Python patch line

**Status:** Accepted
**Date:** 2026-11-06
**Context:** The TRD selected Python 3.13.x. Python 3.13.18 is a source-only security release, and Python 3.13.17 was the last 3.13 release with Windows binary installers. This project is developed in a Windows environment. Django 5.2 added support for Python 3.14 in 5.2.8.
**Decision:** Use the Python 3.14 line and pin Python 3.14.10 for the current reproducible baseline.
**Reason:** Python 3.14.10 is the current official security-fixed patch with Windows installation support, and the selected Django LTS line supports Python 3.14.
**Alternatives:** Keep Python 3.13.17 and miss security fixes available in 3.13.18 (rejected); build the source-only 3.13.18 manually on Windows (unnecessarily complex); change Django to 6.x to use Python 3.15 (unnecessary architecture/version-line change).
**Consequences:** Runtime patch updates within Python 3.14 must be reviewed and reflected in `.python-version`, setup instructions, CI, and the lock report.
**Related documents:** `docs/04_TRD.md`, `docs/REFERENCES.md`, `requirements/LOCK_REPORT.md`.

## ADR-012 â€” Normalize one account login identifier

**Status:** Accepted
**Date:** 2026-11-06
**Context:** The schema permits email authentication or phone authentication and requires unique normalized identifiers, but does not define normalization rules.
**Decision:** Each account stores exactly one identifier. Trim and case-fold email addresses; store phone numbers in E.164 syntax (`+` and up to 15 digits). New accounts remain `PENDING` until a later verification flow activates them. `ACTIVE` is the only account status that Django considers authenticated/usable.
**Reason:** One normalized identifier per account avoids ambiguous account-recovery and duplicate-address behavior. Syntactic E.164 validation is deterministic without claiming that a phone number is owned or verified.
**Alternatives:** Store both email and phone on a single account without an identifier-selection policy (rejected); infer or rewrite local phone formats based on Bangladesh geography (rejected because it can mis-handle international users and is not in the schema).
**Consequences:** Registration and authentication services must select one identifier and verify ownership before activation. Phone-only authentication requires the custom backend planned in P2-01; Django's default email username alone is not sufficient for phone login.
**Related documents:** `docs/01_PRD.md`, `docs/05_Schema.md`, `docs/06_Plan.md`.

## ADR-013 - Web authentication and account abuse controls

**Status:** Accepted
**Date:** 2026-11-06
**Context:** P2-01 must provide web registration, session login/logout and password reset while the account schema permits one email or phone identifier and new accounts stay pending until verification. Exact authentication throttles were not specified.
**Decision:** Use Django session authentication with a custom backend that accepts the normalized email or E.164 phone identifier. Pending, suspended and deactivated accounts cannot authenticate. Registration requires one identifier, a validated password and explicit Terms/Privacy acknowledgement, but returns a generic confirmation to avoid account enumeration. Logout is POST/CSRF protected. Password reset uses Django's one-time token flow and is sent only to an active account's verified email. Local development uses Django's in-memory email backend so reset tokens are not printed to terminal logs; production requires SMTP host/user/password supplied through environment variables and TLS or SSL. Apply fixed-window cache throttles per remote IP: 10 login attempts/minute, 5 registration attempts/hour, and 5 password-reset attempts/hour. Derive cache keys using HMAC so raw IP addresses are not stored.
**Reason:** Reuse Django's supported session and password-reset security behavior, preserve the one-identifier account policy, and prevent authentication/contact details from being disclosed by generic errors or logs. Explicit, conservative thresholds make the plan testable until operational data justifies review.
**Alternatives:** Add a third-party authentication/throttle package (unnecessary dependency); enable accounts before verification (violates ADR-012); send reset tokens to console (risks token exposure); disclose duplicate/unknown identifiers (enables enumeration).
**Consequences:** Phone-only password recovery depends on verified phone delivery in P2-02. Registration acknowledgement history is recorded in P2-04. Until P5-05 configures a shared Redis cache, development throttling is process-local and is not a multi-worker production control. Production SMTP credentials/provider approval are required before password reset delivery can operate.
**Related documents:** `docs/01_PRD.md`, `docs/02_AppFlow.md`, `docs/07_Security.md`, `docs/09_Deployment.md`, `docs/11_Data_Governance.md`, `docs/06_Plan.md`.

## ADR-014 - One-time account verification codes

**Status:** Accepted
**Date:** 2026-11-06
**Context:** P2-02 requires email/phone verification, single-use codes, expiry, resend throttling and a mock provider without authorized production delivery services.
**Decision:** Generate six-digit codes with the standard cryptographic random source. Expire them after 10 minutes, accept at most five attempts per challenge, enforce a 60-second resend cooldown and at most three sends per account/purpose/hour, and throttle challenge sends to five per IP/hour and code submissions to ten per IP/hour. Store only an HMAC digest using Django's secret key; never store/log submitted or delivered codes in the database or application logs. Invalidate any previous outstanding challenge when issuing a new one. Development/tests use an in-memory mock delivery adapter; production fails closed until a real authorized adapter exists. Verification activates only the user's existing email or phone identifier.
**Reason:** These bounded defaults provide meaningful resistance to guessing and resend abuse while keeping the implementation small and testable. The HMAC prevents a database-only compromise from enabling trivial offline enumeration of six-digit codes.
**Alternatives:** Store plaintext or unsalted hashes (rejected); allow unlimited resend/guessing (rejected); send codes to console/logs (rejected); activate accounts before verification or claim production provider access (rejected).
**Consequences:** The mock cannot deliver to real users. P13-01 adds synchronous email delivery through Django?s configured backend when authorized SMTP settings and a verified sender are present; phone verification still requires an SMS provider. Shared IP throttles become effective across workers when P5-05 configures Redis; per-challenge attempt limits and per-account resend history are database-backed immediately. Purge challenge rows more than 24 hours past expiry with `manage.py purge_verification_challenges`, and schedule that command during deployment. Phone password recovery can use the same challenge service after successful verification.
**Related documents:** `docs/01_PRD.md`, `docs/02_AppFlow.md`, `docs/07_Security.md`, `docs/08_Testing.md`, `docs/11_Data_Governance.md`, `docs/06_Plan.md`.

## ADR-015 - Minimal account roles and object ownership

**Status:** Accepted
**Date:** 2026-11-06
**Context:** P2-03 requires server-side role and object authorization without introducing an application-specific role framework. The PRD defines authenticated users, donors, moderators, superadmins and future organization users; the schema already includes Django group and per-user permission relations.
**Decision:** Treat an authenticated account as a user with `account_status=ACTIVE`. Use Django's built-in `Group` membership to assign `MODERATOR` and future named roles, and Django permissions for fine-grained moderation actions. Donor authority will be derived from the donor profile relationship when P3-02 exists, rather than a manually assigned group. Only `is_superuser` denotes `SUPERADMIN`; `is_staff` alone grants no application role or moderation permission. Organization access remains unavailable until its scoped feature exists. Provide reusable DRF permission classes for active accounts, explicit roles and object ownership. Ownership is exact identity equality against the object's `user` or `owner`; privileged access requires a separate permission check and is not an implicit owner bypass.
**Reason:** Reuse the relations already included by `PermissionsMixin`, keep role assignment auditable through Django auth, and prevent a Django admin flag or role label from bypassing object ownership.
**Alternatives:** Add a custom role model/dependency (duplicate of built-in groups); treat all staff as moderators (overbroad); let moderators bypass ownership checks (violates least privilege); assign donor role manually (can drift from profile state).
**Consequences:** Group names and required Django permission codenames must be provisioned when their features are implemented. Each view/service must combine authentication, feature-specific role checks and ownership checks; these helpers do not replace workflow-specific authorization.
**Related documents:** `docs/01_PRD.md`, `docs/05_Schema.md`, `docs/07_Security.md`, `docs/10_API_Contract.md`, `docs/06_Plan.md`.

## ADR-016 - Append-only, versioned consent events

**Status:** Accepted
**Date:** 2026-11-06
**Context:** P2-04 needs separate, versioned and auditable consent choices. The governance schema requires policy version, grant state, capture time, optional withdrawal time and source, while the legal text and retention schedule remain draft items.
**Decision:** Add a `governance.ConsentRecord` event table. Registration requires and records separate Terms acceptance and Privacy Notice acknowledgement using configurable `TERMS_POLICY_VERSION` and `PRIVACY_POLICY_VERSION` values that default to `draft-1`. Privacy settings record purpose-specific opt-in/out events against the privacy policy version. Events are appended only; the service serializes updates by locking the account row and avoids duplicate events when the latest state/version is unchanged. Privacy choices default to false. Donor discovery, contact disclosure, notifications and generalized location settings are recorded but do not activate features until their dependent workflows enforce them. Current legal policy documents remain drafts pending qualified local review.
**Reason:** Preserve an auditable history without overwriting prior consent, separate unrelated purposes, and avoid treating consent as proof of a product capability or legal approval.
**Alternatives:** Store only current booleans (loses history); combine all purposes into one checkbox/event (not purpose-specific); assume a production policy version before legal review (unsupported).
**Consequences:** Policy owners must increment version settings when text changes and configure approved versions before release. Consent events are retained with the account under a PROTECT relation; account deletion/retention procedures must resolve this dependency. No donor or contact flow may rely on a stored choice until it checks current consent at the point of use.
**Related documents:** `docs/01_PRD.md`, `docs/02_AppFlow.md`, `docs/05_Schema.md`, `docs/07_Security.md`, `docs/11_Data_Governance.md`, `docs/06_Plan.md`.

## ADR-017 - Offline, provenance-checked administrative geography

**Status:** Accepted
**Date:** 2026-11-06
**Context:** P3-01 requires Division/District/Upazila hierarchy with source and version stored per row. The BBS Geo Code page is official but currently lists a 2016 publication; the National Portal pages are maintained government references, but their displayed Upazila totals differ across current pages. DGHS location APIs describe authenticated access and do not grant this project access.
**Decision:** Store locations in a self-referential hierarchy and load only a frozen JSON snapshot that includes source name, source version/date, source URL and human review metadata. The importer is offline, validates every parent path and the hierarchy, and refuses input without explicit review confirmation. No government endpoint is called. Do not ship/populate an official seed until the dataset's current names/counts and parent assignments have been reconciled and reviewed; synthetic fixtures are test-only.
**Reason:** Keep runtime independent of government services and prevent a stale or inconsistent list from being presented as current official data.
**Alternatives:** Call BBS/DGHS endpoints at runtime (no authorization/credentials); assume the 2016 workbook is current (not evidenced); use an unverified third-party dataset (provenance and hierarchy not assured).
**Consequences:** The schema and importer can be verified with synthetic fixtures, but a complete real administrative seed remains a data-curation/review prerequisite before discovery can use it. Reconcile with an up-to-date BBS Geo Code publication and current Bangladesh National Portal listings before approving a version.
**Related documents:** `docs/05_Schema.md`, `docs/06_Plan.md`, `docs/REFERENCES.md`, `docs/09_Deployment.md`.

## ADR-018 - Blood request expiry and lifecycle enforcement

**Status:** Accepted
**Date:** 2026-11-06
**Context:** P4-01 specifies required and expiry timestamps plus the states `DRAFT`, `OPEN`, `FULFILLED`, `CANCELLED` and `EXPIRED`, but does not specify an expiry default or how automatic expiry runs.
**Decision:** Default a newly created request's expiry to its required-at time; allow publishing only when both timestamps are in the future and expiry is not before required-at. Owners may edit drafts/open requests, publish drafts, and transition open requests to `FULFILLED` or `CANCELLED`. Expiration is an automated transition for due open requests, performed by an idempotent bounded management service/command; deployment scheduling is configured with background jobs in P5/P9. Closed states are terminal. `FULFILLED` records the requester's coordination report and is not clinical verification.
**Reason:** The required-at timestamp is the only documented event that naturally bounds the request lifetime. The rules preserve the specified state machine, avoid unbounded public requests, and keep clinical conclusions outside the platform.
**Alternatives:** Invent a fixed number-of-days time-to-live (unsupported by requirements); allow past-due requests to publish (stale listing risk); treat donor contact acceptance as fulfillment (not authorized by the state machine).
**Consequences:** The request's `expires_at` remains explicit and can be adjusted by its owner while editable. The expiration command must be scheduled in a deployment environment before stale requests can be cleaned up automatically. The service uses bounded batches so a large due queue does not become one long transaction.
**Related documents:** `docs/02_AppFlow.md`, `docs/05_Schema.md`, `docs/06_Plan.md`, `docs/07_Security.md`, `docs/09_Deployment.md`.

## ADR-019 - In-app-only requester responses

**Status:** Accepted
**Date:** 2026-11-06
**Context:** S-09 in `docs/02_AppFlow.md` requested a contact preference, but `requests_bloodrequest` has no preference field and the MVP contact workflow does not define recipient contact disclosure or consent.
**Decision:** Blood requests are answered through the in-app contact-request workflow only. Do not collect or disclose the requester's phone/email through a request form or public listing. Remove the undefined preference field from S-09 and state the in-app-only behavior explicitly.
**Reason:** This uses the supported coordination channel and prevents exposing account identifiers without a documented consent and authorization flow.
**Alternatives:** Add an undocumented schema field and guess whether a requester preference permits contact disclosure (unsafe and unsupported); add arbitrary contact options without a corresponding workflow (misleading).
**Consequences:** Request screens explain that replies are coordinated in app. A later product change that enables direct requester contact must define a schema, consent, authorization and disclosure policy through a new reviewed decision.
**Related documents:** `docs/02_AppFlow.md`, `docs/05_Schema.md`, `docs/07_Security.md`, `docs/11_Data_Governance.md`.

## ADR-020 - Public donor search rate limit

**Status:** Accepted
**Date:** 2026-11-07
**Context:** P4-04 requires abuse protection for unauthenticated donor search. The project already uses a cache-backed, fixed-window IP throttle with HMAC-derived keys for account workflows; shared Redis configuration is scheduled in P5-05.
**Decision:** Limit donor search to 30 requests per remote IP per 60-second fixed window using the existing cache throttle. Return HTTP 429 with `Retry-After: 60` after the limit. Derive the cache key with the Django secret key and HMAC-SHA256; do not store raw IP addresses. Apply this equally to guests and authenticated users.
**Reason:** Public guest search is a product requirement; a bounded request rate reduces scraping and automated load while preserving ordinary interactive use. Reusing the established mechanism avoids a new dependency.
**Alternatives:** Require login (conflicts with guest-search requirements); add a third-party package (unneeded dependency); choose an unbounded service-wide or per-account policy (does not protect unauthenticated search or lacks defined identity behavior).
**Consequences:** The current development/default cache is process-local, so this is not a cross-worker production control until P5-05 configures Redis. The threshold is an initial abuse-control default and should be reviewed against operational evidence before public scale claims.
**Related documents:** `docs/07_Security.md`, `docs/08_Testing.md`, `docs/06_Plan.md`, `docs/09_Deployment.md`.

## ADR-021 - Contact request expiry

**Status:** Accepted
**Date:** 2026-11-07
**Context:** The contact request schema requires an expiry time, but the MVP flow did not define its duration. Blood requests already have an explicit owner-controlled expiry, and pending contact requests should not remain actionable indefinitely.
**Decision:** A pending contact request expires at the earlier of 48 hours after creation or the associated blood request's expiry. A late accept/decline attempt records the request as expired. Expiry is terminal; it does not reopen or disclose contact details.
**Reason:** A bounded 48-hour window limits stale contact attempts while allowing time to respond. Capping it at the parent blood request's expiry prevents a contact request from outliving its purpose.
**Alternatives:** Let requests remain pending indefinitely (stale requests); use an arbitrary longer fixed period without regard to request expiry; allow contact requests after the parent request closes.
**Consequences:** Creation and decision services enforce the window. A later scheduled expiry job may mark untouched due rows expired; the pending unique constraint stops applying once a request is terminal.
**Related documents:** `docs/02_AppFlow.md`, `docs/05_Schema.md`, `docs/06_Plan.md`, `docs/07_Security.md`.

## ADR-022 - Contact request creation throttle

**Status:** Accepted
**Date:** 2026-11-07
**Context:** Authenticated contact request creation can generate unwanted notifications and spam even when duplicate pending requests are blocked. The existing account/search controls use the shared fixed-window cache throttle.
**Decision:** Limit contact request creation to 10 POST attempts per remote IP per 60-minute fixed window. Use the existing HMAC-derived IP cache key and return 429 with `Retry-After: 3600` after the limit. Apply after authentication; requests are also scoped to an active recipient and a single pending donor/request tuple.
**Reason:** A conservative bound reduces scripted abuse while allowing ordinary request coordination. The duplicate constraint independently prevents repeated pending requests for the same donor and request.
**Alternatives:** No endpoint limit (permits spam); key only by account (does not constrain guest-independent automation across accounts); introduce a separate dependency (unnecessary).
**Consequences:** The current cache is process-local; P5-05 Redis configuration is required for cross-worker enforcement. Revisit the threshold using operational evidence.
**Related documents:** `docs/07_Security.md`, `docs/08_Testing.md`, `docs/06_Plan.md`, `docs/09_Deployment.md`.

## ADR-023 - Redis-backed notification outbox and Celery

**Status:** Accepted
**Date:** 2026-11-07
**Context:** P5-05 requires shared throttling and background notification delivery. The TRD already selects Redis 7.x and Celery 5.7.0, and the runtime lock already pins `celery[redis]`; notifications are durable database rows created with the contact transaction.
**Decision:** Use the existing `REDIS_URL` for Django's shared cache and Celery's Redis broker, selecting separate Redis database indexes for cache and broker. Use each durable notification UUID as the Celery task identifier and as the database idempotency key. Enqueue only after the creating transaction commits; failed/unsent rows remain pending and are redriven by a bounded periodic task. Configure JSON-only tasks, late acknowledgement, worker-loss rejection, bounded transient retries, task time limits and no result backend. Tests use eager Celery and an isolated local cache.
**Reason:** Reuse the approved stack, avoid losing notifications when a request transaction rolls back, and make duplicate worker delivery harmless without storing message payloads in Redis.
**Alternatives:** Add a new broker/dependency (contradicts TRD); publish before database commit (can create notifications for rolled-back requests); rely on an untracked process-local queue (loses work on restart); store Celery results unnecessarily.
**Consequences:** Redis and a Celery worker/beat process are required for production background delivery and cross-worker throttling. Provider adapters remain disabled until P5-06 and authorized configuration exist. In-app rows stay readable from PostgreSQL even while delivery is pending.
**Related documents:** `docs/04_TRD.md`, `docs/05_Schema.md`, `docs/06_Plan.md`, `docs/09_Deployment.md`, `docs/10_API_Contract.md`.

## ADR-024 - Mock-only email and SMS notification adapters

**Status:** Accepted
**Date:** 2026-11-07
**Context:** P5-06 requires email/SMS adapter seams, but no approved production notification provider or SMS authorization is configured. Email credentials exist as environment settings, which alone do not authorize product notifications.
**Decision:** Add email/SMS adapter protocols with deterministic mock implementations only. Create external-channel outbox records only in mock mode, for verified destinations with current optional-notification consent; recheck consent at delivery. Production settings disable external channels. Do not instantiate SMTP/SMS providers from notification tasks until an authorized provider and explicit release approval are recorded.
**Reason:** Preserve the planned adapter boundary and test delivery behavior without sending real messages or treating configured credentials as authorization.
**Alternatives:** Send real SMTP/SMS on the basis of credentials alone (no consent/provider authorization); invent an SMS provider (unsupported); omit consent checks (violates privacy policy).
**Consequences:** Mock references identify simulated deliveries only. Production in-app notifications continue through PostgreSQL; email/SMS notifications are disabled pending documented authorization and provider implementation.
**Related documents:** `docs/05_Schema.md`, `docs/06_Plan.md`, `docs/07_Security.md`, `docs/09_Deployment.md`, `docs/11_Data_Governance.md`.

## ADR-025 - Private reports and bilateral blocks

**Status:** Accepted
**Date:** 2026-11-07
**Context:** P6-01 requires private user reporting and blocking; schema says blocks in either direction prevent new contact requests but does not define controlled report reasons.
**Decision:** Allow report reasons `SAFETY_CONCERN`, `HARASSMENT`, `SPAM`, `IMPERSONATION`, `INAPPROPRIATE_CONTENT`, and `OTHER`. Keep report details scoped to the reporter and authorized moderators (moderator UI/access is P6-02); never expose the reporter or report text to the reported account. Treat a block in either direction as disqualifying a new contact request. Block creation is idempotent and does not notify the other party.
**Reason:** A small controlled list supports triage without collecting broad sensitive narratives. Symmetric eligibility enforcement applies the schema's bilateral wording consistently while preserving reporter privacy.
**Alternatives:** Reveal report contents to reported users (risks retaliation); treat blocks as one-way contact eligibility (contradicts the schema); add free-form categories or anonymous third-party reports without policy (unbounded abuse surface).
**Consequences:** Report and block records use server-side ownership checks. No moderator access or report-resolution workflow is exposed until P6-02.
**Related documents:** `docs/01_PRD.md`, `docs/02_AppFlow.md`, `docs/05_Schema.md`, `docs/06_Plan.md`, `docs/07_Security.md`.

## ADR-026 - Explicit moderator authorization and report decisions

**Status:** Accepted
**Date:** 2026-11-07
**Context:** P6-02 requires private report review and resolution. Django staff/admin privileges have a separate operational purpose and must not grant product moderation rights implicitly.
**Decision:** Require an active account in the explicit `MODERATOR` group for report review and transition actions. Staff status and superuser status alone grant no access. Allow `OPEN` to move to `UNDER_REVIEW`, `RESOLVED` or `DISMISSED`; allow `UNDER_REVIEW` to move to either terminal state. Terminal decisions require a nonblank reason, and every accepted transition records the actor and minimized status/reason codes in the audit log.
**Reason:** A dedicated, explicit role and constrained state machine implement least privilege and leave an accountable decision trail without disclosing reporter information to the reported account.
**Alternatives:** Reuse `is_staff` (broader operational authority); let terminal reports reopen without a new report (weakens audit history); audit free-form narratives (unnecessary PII exposure).
**Consequences:** Moderator group membership must be provisioned deliberately. Moderator pages expose report details only to authorized active moderators; no action is available to the reported account.
**Related documents:** `docs/01_PRD.md`, `docs/02_AppFlow.md`, `docs/05_Schema.md`, `docs/06_Plan.md`, `docs/07_Security.md`.

## ADR-027 - Redacted append-only audit events

**Status:** Accepted
**Date:** 2026-11-07
**Context:** P6-03 requires evidence for sensitive state changes while preventing audit records from becoming a second store of donor contact data or user narratives.
**Decision:** Store append-only audit events in PostgreSQL with actor, action, resource type/UUID, timestamp and an allowlisted set of short status/reason codes. Record sensitive consent, report/block, blood-request and contact-request transitions, accepted contact disclosure, and report moderation actions in their domain transaction. Exclude message bodies, contact destinations, report descriptions, resolution text and other arbitrary metadata.
**Reason:** A small durable record can support review while sharply constraining the data retained in operational logs.
**Alternatives:** Free-form JSON audit payloads (risk of PII/secrets); logs only (weaker durability/transactional consistency); updating or deleting audit rows (breaks append-only history).
**Consequences:** Audit rows are append-only through the application model and require a retention/access policy before production. They record only events after this feature is deployed; they do not reconstruct earlier actions.
**Related documents:** `docs/05_Schema.md`, `docs/06_Plan.md`, `docs/07_Security.md`, `docs/11_Data_Governance.md`.

## ADR-028 - Small-cell suppression for operational metrics

**Status:** Accepted
**Date:** 2026-11-07
**Context:** P6-04 requires aggregate-only operational metrics and the data-governance policy prohibits small-cell reporting that could re-identify a person.
**Decision:** Provide a fixed moderator-only dashboard of global counts for discoverable donor profiles, open public blood requests, pending contact requests and open reports. Suppress counts below five, including zero. Do not provide location, blood group, time, user, report reason or other breakdowns, exports or individual records.
**Reason:** A coarse fixed set of operational totals can support MVP oversight while reducing the chance that a small population reveals individual activity.
**Alternatives:** Expose per-user or demographic/location breakdowns (re-identification risk); show small counts (reveals presence); add CSV exports (larger disclosure surface).
**Consequences:** Metrics are operational indicators only and do not establish service outcomes, donor eligibility or blood supplied. The threshold should be reviewed with privacy and operational evidence before expansion.
**Related documents:** `docs/01_PRD.md`, `docs/06_Plan.md`, `docs/07_Security.md`, `docs/11_Data_Governance.md`.

## ADR-029 - Opaque, rotating API bearer tokens

**Status:** Accepted
**Date:** 2026-11-07
**Context:** P7-02 needs short-lived API credentials with refresh rotation, expiry and revocation. The TRD lists JWT as a target after package review; no JWT package is currently in the approved lock.
**Decision:** Use cryptographically random opaque access and refresh tokens, store only SHA-256 digests in PostgreSQL, expire access tokens after 15 minutes and refresh tokens after 30 days, rotate refresh tokens on each use, and revoke the whole token family when a used refresh token is replayed. Check active account status and token revocation/expiry on every bearer-authenticated request. Apply the existing HMAC-keyed IP throttle to issue, refresh and revoke routes. Do not add a dependency.
**Reason:** This meets current expiry/rotation/revocation acceptance while avoiding an unreviewed auth dependency and avoids keeping credentials in cleartext at rest. Opaque tokens allow immediate server-side revocation.
**Alternatives:** Static DRF tokens (no expiry/rotation); JWT with a new dependency (requires separate package review and refresh-token blacklist semantics); self-issued JWT code (unnecessary cryptographic implementation risk).
**Consequences:** Every bearer request reads PostgreSQL, so no performance/capacity claim is made. Access tokens are invalidated on refresh; clients must atomically replace both credentials. TLS is mandatory in deployment. Token-row retention/cleanup must be included in operations.
**Related documents:** `docs/04_TRD.md`, `docs/06_Plan.md`, `docs/07_Security.md`, `docs/10_API_Contract.md`, `docs/11_Data_Governance.md`.

## ADR-030 - Render as proposed staging provider

**Status:** Accepted for staging configuration only; provisioning and deployment not authorized
**Date:** 2026-11-07
**Context:** P9-02 and the staging-dependent P8-05/P8-06 tasks need a hosted environment. The project owner proposed Render and explicitly withheld authorization to assume an account, create paid resources, or deploy. The repository already has a Docker image, PostgreSQL 17, Redis-compatible Celery configuration, liveness/readiness endpoints and production settings.
**Decision:** Prepare a Render Blueprint for a Docker web service, managed PostgreSQL 17, private Key Value, Celery worker and beat scheduler, co-located in Singapore with synthetic-only staging data. Use Render's service-provided `onrender.com` hostname, referenced dynamically through `RENDER_EXTERNAL_HOSTNAME` and `RENDER_EXTERNAL_URL`; do not define a custom domain. Disable auto-deploys, use private database/Key Value service references, require database TLS, run migrations in the paid web service pre-deploy command, and keep all credentials in Render environment variables/secret management. Do not apply or deploy the Blueprint until separately authorized.
**Reason:** This matches the existing container/Celery architecture, uses Render's managed service connections and health-check support, and avoids assuming a custom domain or pre-existing account. Paid persistent data services are necessary for credible staging load/restore work; their current pricing must be reviewed before provisioning.
**Alternatives:** Treat local Compose as staging (does not verify a hosted deployment); use free Postgres/Key Value for staging (Postgres expires after 30 days and has no managed backups; Key Value loses state on restart); configure a custom domain (unnecessary because Render provides an `onrender.com` subdomain).
**Consequences:** `render.yaml` describes paid resources but creates none until explicitly applied. P9-02 remains implemented-unverified until an authorized Render account/repository connection, approved SMTP settings and a deployment pass health/migration checks. Email account verification uses Django's SMTP email backend with the existing one-time challenge service; phone verification remains unavailable in production until an SMS adapter is authorized. P8-05/P8-06/P8-07 remain blocked until staging is operational and provider and account-verification behavior can be exercised safely.
**Related documents:** `Dockerfile`, `render.yaml`, `scripts/render_start.sh`, `docs/06_Plan.md`, `docs/07_Security.md`, `docs/09_Deployment.md`, `docs/EXECUTION_STATE.md`.

## ADR-031 — Donor-confirmed private location for distance matching

**Status:** Accepted product direction; implementation pending
**Date:** 2026-11-22
**Context:** The revised Find Donor concept requires location-radius search. Using administrative representative points as the primary donor position can produce inaccurate radius matches and distances. Donor coordinates are sensitive; requester search coordinates have a separate transient lifecycle.
**Decision:** During donor profile setup/editing, the donor explicitly confirms an optional point and grants separate, revocable `donor_location_matching` consent. Store the point privately as PostGIS `geography(Point, 4326)` on `DonorProfile`, with source (`GPS` or `MAP_PIN`), GPS accuracy when applicable, and last confirmation/update timestamp. GPS accuracy must be <=100 m for radius matching; a map pin requires explicit donor confirmation. These are donor-provided locations, not independently verified and not assumed to be the donor's home; do not collect an exact street address.

Requester search coordinates are submitted in a POST body for that search only; never persist or log them in database records, analytics, URLs or errors. Validate requester and donor points against a reviewed, approved Bangladesh boundary dataset using PostGIS `ST_Covers`; reject outside points and fail closed if no approved boundary is active. Review source, license, version, provenance and import/use approval before implementation; do not substitute a hand-written bounding box or activate an unreviewed dataset.

Use PostGIS `ST_DWithin` against donor-confirmed coordinates only for exact, server-side radius eligibility at 5, 10, 20 and 50 km. Administrative representative points never qualify a donor for a radius or receive a distance. If the interface clearly separates result types, donors with only reviewed administrative-area data may appear under exactly “Area matches — distance not verified,” with no distance or radius claim; otherwise omit them from radius results. Public radius-qualified results may show only one coarse approximate straight-line band (`<2 km`, `2–5 km`, `5–10 km`, `10–20 km`, `20–50 km`, `>50 km`), not road/travel distance. Never expose donor coordinates, exact distance or exact address through public APIs, templates, admin exports, logs or errors.

Consent withdrawal immediately clears the point, source, accuracy and confirmation timestamp; retain only the administrative area if permitted. Deactivation immediately excludes the donor from every match type. Account deletion removes the precise point from the active database. A proposed maximum 30-day purge window for deleted/revoked precise coordinates in backups is subject to final privacy/legal policy.
**Reason:** Donor confirmation is more relevant to the donor's intended discovery location than an administrative centroid, while strict separation and coarse output preserve privacy.
**Alternatives:** Use administrative representative points for radius eligibility (rejected because they can misstate donor distance); disclose donor points to requesters (rejected for privacy); treat an area point as a distance fallback (rejected because it cannot substantiate radius inclusion); send stored donor matching coordinates or donor records to map/Places providers (rejected as unnecessary disclosure).
**Consequences:** Implementation requires PostGIS support, a reviewed and approved Bangladesh boundary dataset, schema migration, owner-only profile API/UI, versioned consent and withdrawal behavior, server-side matching, separated area-only results, deletion/backup retention handling, and privacy/boundary/radius tests. The administrative-location source gap remains a separate blocker for real area results. P12-02 now adds a client-side location-first picker to `/app/`, reusing the P12-03 Google Maps/Places/Geocoding code; it does not submit requester coordinates to BloodConnect, return nearby results or select a production provider. Product provider, costs, terms and data-transfer disclosure require review. This ADR does not authorize imports, matching migrations, billing or deployment.
**Related documents:** `README.md`, `docs/01_PRD.md`, `docs/02_AppFlow.md`, `docs/03_UI_Spec.md`, `docs/04_TRD.md`, `docs/05_Schema.md`, `docs/06_Plan.md`, `docs/07_Security.md`, `docs/08_Testing.md`, `docs/09_Deployment.md`, `docs/10_API_Contract.md`, `docs/11_Data_Governance.md`.

## ADR-032 — Google sign-in through django-allauth

**Status:** Accepted (implemented; verification in progress)
**Date:** 2026-11-23
**Context:** BloodConnect BD has a custom Django `User` that accepts exactly one email or phone identifier, an `IdentifierBackend`, Django session authentication, account status enforcement, and a P2-02 verification flow. Google sign-in is an additional web authentication method. Provider email equality alone must not merge or authenticate a local account, and Google identity verification does not establish phone ownership, donor status or donor eligibility.
**Decision:** Select `django-allauth` 65.22.1's Google provider for server-side OAuth 2.0 Authorization Code Flow and OIDC ID-token processing. It supports Django's session stack, callback/state handling, Google claims and explicit account connection. The selected release is pinned in the runtime input and hash locks after compatibility review. Configure client ID and secret from protected backend environment variables only. Request only `openid`, `email` and `profile`; do not persist social tokens. Use state and PKCE, and validate subject (`sub`), issuer, audience, expiry and verified-email claim server-side. The Google provider's code-only flow does not send an OIDC nonce; Google documents nonce as optional for `response_type=code`, while requiring it for responses that include an ID token. The library validates claims for the authorization-code token exchange. Do not describe that as independent JWT signature verification where the token was fetched directly over TLS from Google's token endpoint.

Keep Django session authentication and the current email/phone `IdentifierBackend`; add the social backend alongside it rather than replacing it. Apply the existing active-account and permission checks before establishing a usable BloodConnect session. Create new Google users through the existing account-creation and verification policy, in PENDING status until all locally required verification is complete. The provider's `email_verified` claim does not itself mark a local email/phone verification field complete unless a separately reviewed policy explicitly accepts it. Never set `phone_verified_at`, account approval, donor status or medical eligibility from Google claims.

Persist the Google `sub` as a unique linked provider identity using django-allauth's supported social-account model. A verified Google email that matches an unlinked local account must not silently authenticate, merge, or auto-connect that account; disable email-based social authentication/auto-connect. Link only after the user has authenticated to an ACTIVE BloodConnect account and explicitly confirms the action through a CSRF-protected flow. Reject identities already connected to another user and handle concurrent duplicate attempts without creating duplicate accounts. Do not implement unlink unless account recovery and prevention of removing the only usable authentication method are included.

**Reason:** django-allauth is Django-native and provides a maintained provider/account-linking implementation and its own persistent social identity model, avoiding a hand-built OAuth token and callback implementation. Its supported account/session integration permits the existing local login system to remain available.
**Alternatives:** Hand-implement OAuth/OIDC and token verification (rejected because it duplicates security-sensitive protocol behavior); client-only Google sign-in (rejected because browser-submitted identity is untrusted); automatic email-based merge/link (rejected because it bypasses explicit account authentication); replace local authentication or the user model (rejected because it disrupts existing login and account policy).
**Consequences:** django-allauth adds account/social-account tables via additive migrations; inspect generated migrations and use isolated test databases only. Do not apply them to the existing customer database without explicit approval. The project configures its OAuth app from settings/environment variables. Its adapter resolves that settings-backed app without querying `SocialApp`, while callback persistence still requires django-allauth social-account tables. Secrets stay in protected backend configuration. Callback path confirmed from the resolver: `/accounts/google/login/callback/`; tested local URI: `http://127.0.0.1:8000/accounts/google/login/callback/`. Google returned `redirect_uri_mismatch`, requiring this exact URI to be added to the Google Cloud OAuth client's authorized redirect URIs. A production URL must use the verified deployment host; none is established here. Google verified email does not activate pending accounts or replace BloodConnect verification requirements. New accounts remain pending and existing matching-email accounts require sign-in followed by explicit authenticated linking. Email/phone auth remains available; no account merge or unlink is provided.
**Related documents:** `docs/01_PRD.md`, `docs/02_AppFlow.md`, `docs/03_UI_Spec.md`, `docs/04_TRD.md`, `docs/05_Schema.md`, `docs/06_Plan.md`, `docs/07_Security.md`, `docs/08_Testing.md`, `docs/09_Deployment.md`, `docs/10_API_Contract.md`, `docs/11_Data_Governance.md`, [django-allauth requirements](https://docs.allauth.org/en/latest/installation/requirements.html), [Google provider](https://docs.allauth.org/en/latest/socialaccount/providers/google.html), [social-account linking](https://docs.allauth.org/en/latest/socialaccount/introduction.html).

## ADR-033 — Store donor-selected donation areas without geospatial infrastructure

**Status:** Accepted for the profile-picker scope
**Date:** 2026-11-23
**Context:** The approved donor-profile location picker needs to persist a donor-confirmed general donation area. The existing model has required administrative division/district foreign keys, but the reviewed administrative choices are unavailable. The planned PostGIS `PointField` cannot be imported in the current runtime because GeoDjango's GDAL library is absent, and PostGIS is not configured. The user approved a profile-picker-only alternative; donor discovery and distance matching are explicitly out of scope.
**Decision:** Add nullable scalar decimal latitude/longitude fields, a general-area label, optional Google Place ID, a constrained source (`GOOGLE_PLACE`, `GOOGLE_GEOCODE`, or `MAP_PIN`), and a server-set confirmation timestamp to the private donor profile. Keep the existing administrative foreign keys and make division/district nullable so new map-only profiles can be saved; preserve existing foreign-key values during migration and on profile saves without a replacement map area, but clear them when an owner confirms and saves a replacement map area so stale administrative locations are not retained or used for discovery. Store selected coordinates only after explicit area confirmation and a separate, revocable `donor_area_storage` consent. Do not request browser GPS. Disclose that the browser sends the donor's place query and selected pin coordinates directly to Google Maps Platform for the requested map/geocoding operation; do not send donor records, blood group or search results. Keep coordinates and Place ID out of public serializers, donor search results, public templates, logs and errors. Keep map-only profiles excluded from discovery because the existing discovery queryset continues to require valid administrative references. This decision does not itself authorize coordinate matching, donor markers, a public location API, or migration application.
**Alternatives:** Add GeoDjango/GDAL and configure PostGIS (deferred pending a separate infrastructure decision); retain required administrative fields (rejected because the unavailable dataset blocks saving); use public map markers or coordinate matching (rejected as outside this profile-only scope).
**Consequences:** The schema diverges temporarily from the planned PostGIS location model and is SQLite-compatible for the current profile-only workflow. A later matching project must review a separate migration from scalar coordinates to the approved geospatial schema, boundary validation, consent purpose and retention policy before using coordinates. After separate explicit approval, the additive migration was applied only to the local Compose development database; it preserves existing donor administrative references and no production or remote database was migrated. Google Maps is used only through the existing restricted browser-key integration; this does not approve production use or billing.
**Related documents:** `docs/01_PRD.md`, `docs/02_AppFlow.md`, `docs/03_UI_Spec.md`, `docs/04_TRD.md`, `docs/05_Schema.md`, `docs/06_Plan.md`, `docs/07_Security.md`, `docs/08_Testing.md`, `docs/10_API_Contract.md`, `docs/11_Data_Governance.md`.

## ADR-034 — Store confirmed request areas separately from facility details

**Status:** Accepted for request-location selection; migration application approved for local Compose development only (2026-11-23)
**Date:** 2026-11-23
**Context:** Request creation currently requires administrative division/district choices that are unavailable in the reviewed location dataset. Facility name/address are separate optional text fields and cannot safely stand in for a selected map area. The existing shared browser picker can provide Places details and map coordinates, but `BloodRequest` has no request-area fields.
**Decision:** Add nullable scalar decimal request latitude/longitude, a general-area label, optional Google Place ID, a constrained source (`GOOGLE_PLACE` or `MAP_PIN`), and a server-set confirmation timestamp. Make the legacy division/district foreign keys nullable so a new map-only request can be saved without inventing administrative records. Preserve all existing rows and foreign-key references during migration. A requester's confirmed map area replaces legacy location references only when that owner intentionally selects and confirms a replacement; a cleared map selection is not publishable without another valid location. Keep facility name and address independent of the selected area.

Reuse `static/js/location_picker.js` in a request-specific Places-only mode: use Places API (New) autocomplete and Place Details, never Geocoding or browser GPS. A marker adjustment reads the map event coordinates directly; it keeps the selected general-area label (or an explicitly generic map-pin label) and does not claim address verification. The server validates the confirmed coordinate pair, label and source and sets the timestamp. Public request-list/detail serializers never include the user-supplied map label, coordinates or Place ID; owner-only reads may show the label and owner-only web form fields may carry the point for editing. Preserve request visibility, lifecycle, expiry and authorization rules.

**Security follow-up (2026-11-25):** The Places/map-pin label is client-controlled, so it cannot be assumed to be a general area. Public API responses now return `null` for map-selected labels until a reviewed server-side generalization source exists. This supersedes the public-label portion of the decision above. Legacy administrative labels remain public; the authenticated owner may read their own saved label.

**Alternatives:** Reuse `facility_address` (rejected because it conflates a free-text facility description with the selected map area and cannot store the point); map Google address components into official administrative records (rejected because Places data is not an authoritative Bangladesh dataset); add PostGIS (deferred because request display needs no coordinate matching and the approved MVP runtime does not configure it).
**Consequences:** The additive request migration contains nullable field additions, nullable changes to two foreign keys and consistency constraints; it has no data transformation, deletion or backfill. Existing requests retain their administrative location and continue to render through the legacy fallback. After explicit user approval, `requests.0002_add_confirmed_request_location` was applied only to the local Compose development database; no production or remote database was migrated. Request coordinates and Place IDs are private persistence, not donor-search inputs or public marker data. Google receives only the browser's user-entered place query and requested Places details. This decision does not enable donor matching, request-distance calculations, public map markers, Geocoding or billing changes.
**Related documents:** `docs/02_AppFlow.md`, `docs/03_UI_Spec.md`, `docs/05_Schema.md`, `docs/06_Plan.md`, `docs/07_Security.md`, `docs/08_Testing.md`, `docs/10_API_Contract.md`, `docs/11_Data_Governance.md`.

## ADR template

## ADR template

### ADR-NNN — Title
- Status: Proposed / Accepted / Rejected / Superseded
- Date:
- Context:
- Decision:
- Alternatives:
- Consequences:
- Related documents:

## ADR-035 — Keep UI audit tooling isolated from application dependencies

**Status:** Accepted
**Date:** 2026-11-24
**Context:** The Django application already pins Playwright in its Python development lock and has Chromium E2E tests, but no central route/viewport audit, axe accessibility scanner, baseline artifact format, screenshot organization or image-diff tooling. The existing project has no npm tooling.
**Decision:** Reuse the existing Python Playwright/pytest stack and add exact-pinned `axe-core` (`4.14.1`), `pixelmatch` (`8.0.0`) and `pngjs` (`7.0.0`) only as npm development dependencies used by tests. Keep these tools, screenshot output and the synthetic-account fixture out of application runtime and production auth. The audit runs only against pytest `live_server` and isolated test settings; it does not load human storage state or submit application forms. Keep Lighthouse optional until it is available through an approved local toolchain.
**Alternatives:** Add a second browser framework or runtime package (rejected as duplicate); load axe from a CDN during tests (rejected because it makes results depend on remote availability); store browser credentials/storage state (rejected due to unnecessary session risk); add Lighthouse by runtime network install (deferred).
**Consequences:** Developers run `npm ci` for the test-only audit assets. Screenshot comparison uses an explicit 0.5% changed-pixel tolerance and records image diffs without rewriting application code. Screenshots are opt-in, limited to representative routes, and use synthetic data.
**Related documents:** `docs/08_Testing.md`, `docs/UI_AUDIT_REPORT.md`, `tests/ui/audit_config.py`, `tests/e2e/test_ui_audit.py`.

## ADR-036 — Revoke API credentials on password reset

**Status:** Accepted
**Date:** 2026-11-25
**Context:** Web password reset updates Django's password hash, invalidating authenticated Django sessions on their next request. API access and refresh credentials are independent opaque database records and otherwise remain valid after an email-link or verified-phone password reset.
**Decision:** Commit the password update and revocation of all active API access and refresh token families in one database transaction for both password-reset flows. Record each revoked family through the existing redacted API token audit event with reason `PASSWORD_RESET`. Rotate the anonymous session before storing a valid email reset token or granting phone-code reset authority.
**Reason:** A successful credential recovery must invalidate credentials issued using the prior password and must not transfer reset authority through a pre-existing session identifier.
**Alternatives:** Leave token revocation to API clients (does not invalidate stolen credentials); add a password-version field and migrations (unneeded with existing revocable token rows); revoke only refresh credentials (leaves access credentials valid until expiry).
**Consequences:** Password resets revoke all active API token families immediately. No schema or dependency change is required. Session data unrelated to reset remains intact when the session key rotates.
**Related documents:** `docs/07_Security.md`, `docs/10_API_Contract.md`, `apps/accounts/forms.py`, `apps/accounts/views.py`, `apps/api/token_services.py`.
