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
