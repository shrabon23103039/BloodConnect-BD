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
**Consequences:** The mock cannot deliver to real users, so production registration/verification remains unavailable until a provider is authorized and implemented. Shared IP throttles become effective across workers when P5-05 configures Redis; per-challenge attempt limits and per-account resend history are database-backed immediately. Purge challenge rows more than 24 hours past expiry with `manage.py purge_verification_challenges`, and schedule that command during deployment. Phone password recovery can use the same challenge service after successful verification.
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
