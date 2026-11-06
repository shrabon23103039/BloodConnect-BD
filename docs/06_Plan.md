# 06 — Implementation Plan and Agent Task Checklist

**Version:** 1.0  
**Ordering:** Dependency-first, sequential.  
**Rule:** Update this file after every completed task with status and evidence.

## 1. Status legend

- `[ ] NOT_STARTED`
- `[~] IN_PROGRESS`
- `[!] BLOCKED`
- `[?] IMPLEMENTED_UNVERIFIED`
- `[x] VERIFIED`
- `[>] DEFERRED`

A task is `VERIFIED` only when acceptance criteria pass and actual evidence is recorded.

## 2. Execution protocol

For every task:
1. Read relevant specifications.
2. Confirm prerequisite tasks are verified.
3. Inspect existing repository and avoid overwriting work.
4. Implement only the task scope.
5. Add tests.
6. Run tests and checks.
7. Inspect diff and security impact.
8. Update this plan with files, commands, results and remaining issues.

## Phase 0 — Repository and context baseline

- [x] P0-01 Verify all context documents are present and internally consistent. **VERIFIED 2026-11-06 (document/repository inspection only).**
  - Depends on: none.
  - Acceptance: six core docs, supporting docs and agent instructions exist.
  - Evidence: `README.md`, `CLAUDE.md`, `.cursorrules`, `AGENTS.md`, `.cursor/rules/project-guardrails.mdc`, all six core documents and all supporting documents under `docs/` were read and cross-checked. The documented P2P consent model, modular Django monolith, PostgreSQL/ORM boundary, API roadmap and safety constraints agree at the scope level.
  - Repository finding: this checkout contains documentation and Cursor guardrails only. No application source, dependency manifests, migrations, tests, container/deployment files, `.gitignore`, or usable Git repository were found. `git status --short` returned `fatal: not a git repository`.
- [x] P0-02 Initialize Git repository and `.gitignore`. **VERIFIED 2026-11-06.**
  - Depends on: P0-01.
  - Acceptance: secrets, virtualenv, caches, media and local DB files ignored.
  - Evidence: `git init` created the repository on branch `master`. `git check-ignore` checks passed for `.env`, `.env.local`, `.venv/pyvenv.cfg`, `db.sqlite3`, `media/example.jpg` and `__pycache__/module.pyc`; `.env.example` was confirmed not ignored.
  - Files: `.gitignore`, `docs/EXECUTION_STATE.md`, `docs/06_Plan.md`.
- [x] P0-03 Create README and contribution/development instructions. **VERIFIED 2026-11-06 (documentation acceptance).**
  - Depends on: P0-02.
  - Acceptance: setup commands and environment variables documented.
  - Evidence: README documents prerequisites, Windows/macOS/Linux virtualenv commands, environment setup, dependency installation, service startup, Django migration/run commands and test command, with explicit notes that commands requiring future project tasks are not yet runnable. `.env.example` lists all names from `09_Deployment.md` and contains no values. `CONTRIBUTING.md` records task, test, privacy and ADR workflow. A PowerShell assertion verified the environment names are complete and blank and the README references exist.
  - Files: `README.md`, `CONTRIBUTING.md`, `.env.example`, `docs/06_Plan.md`, `docs/EXECUTION_STATE.md`.

### P0 inspection disposition

- Completed: P0-01, limited to presence and manual consistency review of the context pack. This does not mean any product feature is implemented.
- Completed: P0-02. Git initialized and ignore patterns verified.
- Completed: P0-03. Setup, environment variable names and contribution workflow are documented; application-dependent commands are explicitly staged for later tasks.
- Runtime/scaffolding tasks P1-01 and P1-02 are verified. Public information pages (P1-04) and account web flows (P2-01) are verified; donor, request, contact, moderation, API, release and deployment workflows remain incomplete.

### Implementation readiness, risks and planning gaps

- Current task: **P4-01**, blood request model and lifecycle. P0-01 through P0-03, P1-01 through P1-06, P2-01 through P2-04 and P3-01 through P3-04 are verified.
- Continue Phase 3 in dependency order. P1-04 public landing/product, privacy and safety content is implemented; its legal notices remain draft/review items.
- Planning gap: broad MVP requirements for report/privacy settings and operational dashboard are mapped to tasks, but retention periods, request/contact expiry policy and a reconciled current Bangladesh geography snapshot remain unresolved. Authentication throttle thresholds are defined in ADR-013; consent version behavior is ADR-016. Resolve remaining choices from existing docs during each task; if they require product/architecture choices not covered there, record an ADR/document update before coding.
- Dependency/version risk: P1-01 verified compatible exact pins, universal hash locks and package advisories. Linux production installation still needs CI/deployment verification.
- Privacy/release risk: donor contact disclosure, object-level access, synthetic-only data, legal/healthcare review, backup restore, and production secret handling are release blockers. The documentation is not evidence that these controls exist.
- Development database: P1-06 was verified against the existing Docker Desktop PostgreSQL 17.11 Supabase service using a dedicated `bcbd_dev` role/database, persistent Docker volume and ignored local `.env`; no existing containers were stopped or removed. This environment is local development only.
- External-service risk: email, SMS, maps, identity, government and institutional capabilities have no authorized production access established. MVP must remain functional with mock/no-op adapters where applicable.
- Schedule risk: the seven-calendar-day target is aspirational. The formal baseline is 16 weeks, and neither schedule is evidence of completed work.

## MVP requirement traceability checklist

This checklist maps the PRD MVP scope to the existing dependency-ordered task IDs. Items remain unchecked until implemented and verified against their acceptance criteria; documentation coverage alone is not feature completion.

- [ ] Public landing/product, privacy and safety pages; responsive web shell — P1-04, then P8-01/P8-03/P8-04.
- [ ] Registration, login, logout, password reset, verification seam and account/role authorization — P1-06, P2-01–P2-04.
- [ ] Donor profile, consent, availability, visibility and pause/deactivation — P2-04, P3-01–P3-04.
- [ ] Exact blood-group plus division/district/upazila discovery; safe public fields, pagination and throttling — P3-01–P3-04, P4-03–P4-04.
- [ ] Blood request creation, edit, cancellation, closure and lifecycle/expiry — P4-01–P4-02.
- [ ] Recipient contact request and donor accept/decline/cancel/expire; atomic/idempotent transitions; contact disclosure only after acceptance and consent — P5-01–P5-03.
- [ ] Durable in-app notifications; optional email/SMS only through mock/sandbox adapters — P5-04; P5-05–P5-06 are optional delivery infrastructure and require their listed prerequisites.
- [ ] User reporting/blocking and admin moderation — P6-01–P6-02.
- [ ] Redacted audit events for sensitive actions — P6-03.
- [ ] Aggregate operational dashboard metrics with privacy controls — P6-04.
- [ ] DRF `/api/v1/` serializers, auth, donor/request/contact endpoints and OpenAPI/contract coverage for future clients — P7-01–P7-04.
- [ ] Verification of privacy, authorization, accessibility/responsiveness, failure handling, release and operations — P8-01–P8-07, P9-01–P9-05 as applicable.
- [ ] Excluded from MVP: native Flutter clients and organization/government/identity production integrations — P10-01–P10-06 remain deferred; no authorization is assumed.

Optional PRD items are not committed MVP acceptance gates: generalized map view and privacy-reviewed authorized-admin CSV export have no implementation tasks yet; organization directory is planned only as future P10-03. Revisit these only after required MVP flows and release gates are verified, then add scoped plan tasks and dependencies before implementation.

### Cross-cutting acceptance gates for every implementation task

- [ ] Preserve exact blood-group discovery only; no clinical compatibility, eligibility, inventory, donation guarantee or medical verification behavior/copy.
- [ ] Keep donor phone/email/exact address/precise coordinates out of public search, serializers, logs and notifications; disclose only donor-consented channels after explicit acceptance.
- [ ] Enforce server-side ownership/role checks, default-deny private access, CSRF for session writes, input validation and applicable throttling.
- [ ] Use synthetic data only; do not add real personal, health or identity data to fixtures, screenshots, logs or examples.
- [ ] Keep external providers behind adapters and disabled/mock until authorized; no assumed government or institutional access.
- [ ] Record changed files, exact commands, actual results and unresolved issues in the execution log. A task is VERIFIED only with acceptance evidence; otherwise use IMPLEMENTED_UNVERIFIED or BLOCKED.

## Phase 1 — Runtime, database and configuration

- [x] P1-01 Verify Python/Django/DRF compatibility and pin exact dependency versions. **VERIFIED 2026-11-06.**
  - Depends on: P0-03.
  - Acceptance: resolved lock file committed; security advisories checked.
- [x] P1-02 Create Django project and environment-specific settings. **VERIFIED 2026-11-06.**
  - Depends on: P1-01.
  - Acceptance: development/test settings separate from production.
  - Evidence: `pytest --ds=config.settings.test tests/test_settings_profiles.py` passed (2 tests); default development and explicit development `manage.py check` both pass; test profile asserts DEBUG disabled and test-only password hashing; a subprocess confirms production refuses to load without its required secret.
  - Files: `manage.py`, `config/`, `tests/`, `README.md`, `docs/06_Plan.md`, `docs/EXECUTION_STATE.md`.
- [x] P1-03 Configure PostgreSQL and psycopg. **VERIFIED 2026-11-06 (configuration only).**
  - Depends on: P1-02.
  - Acceptance: connection configuration is validated; defer the first migration smoke test until P1-06 has created the custom user model.
  - Evidence: URL parser tests cover PostgreSQL schemes, decoded credentials, supported query options, rejected unsupported input and secret redaction. `manage.py check` passes with synthetic PostgreSQL URLs under development and production settings; production requires `sslmode=require`, `verify-ca` or `verify-full`. Seven focused tests pass and Bandit reports no issues in `config/`.
  - Limitation: no local PostgreSQL service or Docker daemon is available, so no live connection or migration is claimed. Run the first migration smoke test after P1-06 against a provisioned PostgreSQL service.
  - Files: `config/database.py`, `config/settings/`, `tests/test_settings_profiles.py`, `README.md`, `docs/06_Plan.md`, `docs/EXECUTION_STATE.md`.
- [x] P1-04 Configure static files, templates and Bootstrap. **VERIFIED 2026-11-06.**
  - Depends on: P1-02.
  - Acceptance: responsive base layout and public landing/product, privacy and safety pages render with the safety copy and contact/privacy boundaries in `01_PRD.md` and `02_AppFlow.md`.
  - Evidence: Django client tests render all six public pages, verify viewport/accessibility navigation and local Bootstrap assets, test medical/emergency disclosures, donor contact privacy and draft-policy warnings. `collectstatic --settings=config.settings.production` passed and post-processed 726 assets; `manage.py check` passed and Bandit found no issues in configuration.
  - Files: `config/urls.py`, `config/settings/`, `templates/`, `static/`, `tests/test_public_pages.py`, `docs/04_TRD.md`, `docs/REFERENCES.md`, `docs/06_Plan.md`, `docs/EXECUTION_STATE.md`.
- [x] P1-05 Add health/readiness endpoints and structured logging. **VERIFIED 2026-11-06.**
  - Depends on: P1-02.
  - Acceptance: no secrets/PII in logs; health states distinguish dependencies.
  - Evidence: nine tests cover dependency-specific ready/not-ready states, dependency-free liveness, non-cacheability, query/credential redaction, generated request IDs and safe request metadata. Full suite passes (21 tests); Django check passes; Bandit reports no issues in `config/`.
  - Files: `config/health.py`, `config/logging.py`, `config/middleware.py`, `config/database.py`, `config/settings/base.py`, `config/urls.py`, `tests/test_health_logging.py`, `docs/04_TRD.md`, `docs/06_Plan.md`, `docs/EXECUTION_STATE.md`.
- [x] P1-06 Create custom User model before first production migration. **VERIFIED 2026-11-06.**
  - Depends on: P1-03.
  - Acceptance: model is configured as `AUTH_USER_MODEL` before any initial migration; email/phone identity policy and account status tests pass. Run the first migration smoke test only after this task.
  - Verified locally: custom model is configured before migration, exactly one normalized email or E.164 phone is required, account-status/authentication tests pass, migrations are up to date, and `manage.py migrate --settings=config.settings.test` passes on in-memory SQLite.
  - PostgreSQL verification: Docker Engine `29.9.2`; existing PostgreSQL `17.11` container reported healthy and had a persistent named volume. Created isolated `bcbd_dev` login and `bloodconnect_bd_dev` database on that service; local `.env` is gitignored and contains the generated development URL. Django connected as `bcbd_dev`; `manage.py migrate --noinput --settings=config.settings.development` applied all migrations including `accounts.0001_initial`; `showmigrations` reports it applied; PostgreSQL catalog confirms the exact-one-identifier check, unique identifier indexes and case-insensitive email index. `manage.py check` and migration consistency check pass; full pytest suite passes (31/31). No unrelated container was stopped or removed.
  - Files: `apps/accounts/`, `config/settings/base.py`, `tests/test_accounts_user.py`, `docs/12_Architecture_ADRs.md`, `docs/06_Plan.md`, `docs/EXECUTION_STATE.md`.

## Phase 2 — Accounts and authorization

- [x] P2-01 Implement registration, login, logout and password reset. **VERIFIED 2026-11-06.**
  - Depends on: P1-06.
  - Acceptance: auth flows, validation and rate-limit tests pass.
  - Evidence: 14 focused authentication tests pass within a 46-test suite. Tests cover email/phone registration and sign-in, pending-account rejection, validation, generic duplicate/reset responses, verified-email password reset, one-time reset links, POST-only logout, CSRF, per-IP throttles and log redaction. Development and production Django checks pass with synthetic SMTP configuration, PostgreSQL `migrate --check` reports no unapplied migrations, Bandit reports no issues, and `git diff --check` passes.
  - Files: `apps/accounts/authentication.py`, `apps/accounts/forms.py`, `apps/accounts/throttling.py`, `apps/accounts/urls.py`, `apps/accounts/views.py`, `config/settings/`, `config/urls.py`, `templates/accounts/`, `templates/base.html`, `templates/pages/home.html`, `tests/test_account_auth_flows.py`, `tests/test_public_pages.py`, `tests/test_settings_profiles.py`, `.env.example`, `docs/09_Deployment.md`, `docs/12_Architecture_ADRs.md`, `docs/06_Plan.md`, `docs/EXECUTION_STATE.md`, `README.md`.
  - Limitations/dependencies: newly registered accounts remain pending until P2-02 verification; phone reset waits for verified-phone delivery in P2-02; versioned acknowledgement history is P2-04. Local cache throttles are process-local until P5-05 configures Redis. Production SMTP delivery requires an authorized provider and environment credentials; live delivery was not tested.
- [x] P2-02 Implement verification adapter interface and mock provider. **VERIFIED 2026-11-06.**
  - Depends on: P2-01.
  - Acceptance: OTP expiry, one-time use and resend throttling tested.
  - Evidence: 13 verification tests pass within a 60-test suite. Tests cover HMAC-only persistence, email/phone account activation, expiry, one-time use, resend invalidation/cooldown and 3-per-hour account caps, five-attempt lockout, per-IP request/attempt throttles, generic enumeration-resistant web responses, OTP/log redaction, phone password recovery, 24-hour cleanup, and fail-closed production registration when no provider exists. PostgreSQL migrations `0002` and `0003` applied; catalog shows expiry/attempt constraints and indexes. Development check, PostgreSQL migration check, cleanup command, Bandit and diff checks pass.
  - Files: `apps/accounts/models.py`, `apps/accounts/migrations/0002_verificationchallenge.py`, `apps/accounts/migrations/0003_verificationchallenge_accounts_ve_expires_fb4ecf_idx.py`, `apps/accounts/verification.py`, `apps/accounts/forms.py`, `apps/accounts/views.py`, `apps/accounts/urls.py`, `apps/accounts/management/commands/purge_verification_challenges.py`, `config/settings/`, `templates/accounts/`, `tests/test_account_verification.py`, `tests/test_account_auth_flows.py`, `docs/05_Schema.md`, `docs/12_Architecture_ADRs.md`, `docs/06_Plan.md`, `docs/EXECUTION_STATE.md`, `README.md`.
  - Limitations: mock delivery is in-memory and does not send messages; production account verification remains disabled until an authorized provider is implemented. IP throttles use process-local cache until P5-05 configures shared Redis. Schedule the challenge purge command during deployment.
- [x] P2-03 Implement roles and server-side permission classes. **VERIFIED 2026-11-06.**
  - Depends on: P2-01.
  - Acceptance: unauthorized object access tests pass.
  - Evidence: six focused permission tests pass within a 66-test suite. Tests deny anonymous, pending, suspended, deactivated and cross-user object access; grant moderator role only to explicit group members; distinguish staff from superadmin; and ensure superusers do not bypass object ownership. Development check, PostgreSQL migration check, migration consistency check, Bandit and diff checks pass.
  - Files: `apps/accounts/permissions.py`, `tests/test_account_permissions.py`, `docs/12_Architecture_ADRs.md`, `docs/06_Plan.md`, `docs/EXECUTION_STATE.md`.
  - Limitations: donor role is derived from the donor-profile relation when P3-02 introduces it; organization access remains unavailable until its feature exists. Moderator groups and fine-grained Django permissions must be provisioned alongside moderation features.
- [x] P2-04 Implement consent records and privacy settings. **VERIFIED 2026-11-06.**
  - Depends on: P2-01.
  - Acceptance: consent changes are versioned and auditable.
  - Evidence: Four focused consent/privacy tests pass within a 70-test suite. Tests verify separate registration Terms/Privacy versions, authentication and inactive-session restrictions, privacy settings, append-only grant/withdrawal history, no duplicate event for unchanged state and model edit/delete refusal. PostgreSQL migration `governance.0001` applied; catalog confirms both check constraints and the user/purpose/time index. Development check, PostgreSQL migration check, migration consistency, Bandit and diff checks pass.
  - Files: `apps/governance/`, `apps/governance/migrations/0001_initial.py`, `apps/accounts/forms.py`, `apps/accounts/views.py`, `config/settings/base.py`, `config/urls.py`, `templates/accounts/register.html`, `templates/governance/privacy_settings.html`, `templates/pages/privacy.html`, `templates/base.html`, `tests/test_consent_privacy.py`, `tests/test_account_auth_flows.py`, `docs/05_Schema.md`, `docs/12_Architecture_ADRs.md`, `docs/06_Plan.md`, `docs/EXECUTION_STATE.md`, `README.md`.
  - Limitations: policy versions remain `draft-1` until qualified local legal review approves Terms and Privacy text; retention/deletion rules remain unresolved. Donor discovery/contact options are stored but have no effect until dependent workflows enforce consent. Future organization sharing is not exposed as a setting.

## Phase 3 — Locations and donor profiles

- [x] P3-01 Create location models and reviewed Bangladesh geography seed process. **VERIFIED 2026-11-06.**
  - Depends on: P1-03.
  - Acceptance: hierarchy integrity and source/version recorded.
  - Evidence: Six location tests pass within a 76-test suite. Tests cover valid hierarchy, invalid parent levels, case-insensitive uniqueness, provenance/version persistence, idempotent import, and rejection of missing review metadata or broken hierarchy. PostgreSQL `locations.0001` is applied; catalog confirms three check constraints, root/child unique indexes and lookup index. Development check, PostgreSQL migration check, migration consistency, Bandit and diff checks pass.
  - Files: `apps/locations/`, `apps/locations/migrations/0001_initial.py`, `tests/test_location_data.py`, `config/settings/base.py`, `docs/05_Schema.md`, `docs/06_Plan.md`, `docs/12_Architecture_ADRs.md`, `docs/REFERENCES.md`, `docs/EXECUTION_STATE.md`, `README.md`.
  - Limitation: No real geography rows are seeded. The BBS Geo Code catalogue found is dated 2016, and official National Portal list pages displayed inconsistent totals during review; an independently reconciled current snapshot must be approved before real profile/discovery use. The importer requires a human review confirmation and makes no API calls.
- [x] P3-02 Implement donor profile model and migrations. **VERIFIED 2026-11-06.**
  - Depends on: P2-03, P3-01.
  - Acceptance: constraints and indexes match `05_Schema.md`.
  - Evidence: Six focused model tests pass within an 82-test suite. Tests verify schema-safe defaults, field enumerations, one-profile-per-user, protected user/location references, invalid blood-group database rejection, profile-derived Donor role, exact search indexes and division/district/upazila parent integrity. PostgreSQL migration `donors.0001` applied; catalog confirms four enum checks, four search indexes and the unique user index. Development check, PostgreSQL migration check, migration consistency, Bandit and diff checks pass.
  - Files: `apps/donors/`, `apps/donors/migrations/0001_initial.py`, `config/settings/base.py`, `tests/test_donor_profile_model.py`, `docs/05_Schema.md`, `docs/06_Plan.md`, `docs/EXECUTION_STATE.md`, `README.md`.
  - Limitations: No profile editing or discovery flow yet; visibility and contact-consent enforcement belongs to P3-03/P3-04. Location selection remains testable only with synthetic rows until P3-01's reviewed real dataset is available. No medical eligibility or compatibility logic was added.
- [x] P3-03 Implement donor profile create/update/pause/deactivate. **VERIFIED 2026-11-06.**
  - Depends on: P3-02, P2-04.
  - Acceptance: owner-only changes and consent rules tested.
  - Evidence: Five focused donor workflow tests pass within the 87-test suite. Tests cover authenticated owner writes, cross-owner service denial, verified-channel-only sharing, versioned contact consent, stale profile preference suppression after withdrawal, pause/deactivation, and authentication requirements. Development check, PostgreSQL migration check, migration consistency, Bandit and diff checks pass.
  - Files: `apps/donors/forms.py`, `apps/donors/services.py`, `apps/donors/views.py`, `apps/donors/urls.py`, `apps/governance/forms.py`, `apps/governance/views.py`, `config/urls.py`, `templates/donors/profile_form.html`, `templates/base.html`, `tests/test_donor_profile_flows.py`, `tests/test_consent_privacy.py`, `docs/06_Plan.md`, `docs/EXECUTION_STATE.md`, `README.md`.
  - Limitations: Real profile submission is unavailable until the reviewed location snapshot is loaded. Visibility controls are P3-04; any actual contact disclosure must additionally wait for an accepted contact request and check current consent.
- [x] P3-04 Implement availability and visibility controls. **VERIFIED 2026-11-06.**
  - Depends on: P3-03.
  - Acceptance: unavailable/hidden donors excluded from search.
  - Evidence: Three discovery policy tests pass within the 92-test suite. The discoverable queryset requires an active account, active profile, `AVAILABLE`, visible, active selected locations and the latest granted donor-discovery consent. Tests exclude unavailable, paused, hidden, unchecked, pending-account, inactive-location and revoked-consent profiles; owner controls grant/withdraw consent and update availability/visibility, and deactivation preserves moderator suspension.
  - Files: `apps/donors/models.py`, `apps/donors/forms.py`, `apps/donors/services.py`, `apps/donors/views.py`, `apps/governance/models.py`, `tests/test_donor_discovery_policy.py`, `tests/test_donor_profile_flows.py`, `tests/test_consent_privacy.py`, `docs/06_Plan.md`, `docs/EXECUTION_STATE.md`, `README.md`.
  - Limitations: This is the server-side eligibility queryset for P4-03 to consume; a public search route and allowlisted result serializer are not implemented. No official location snapshot is loaded.

## Phase 4 — Blood requests and discovery

- [ ] P4-01 Implement blood request model and lifecycle service.
  - Depends on: P2-03, P3-01.
  - Acceptance: valid transitions, expiry and owner permissions tested.
- [ ] P4-02 Implement request create/edit/cancel/close screens.
  - Depends on: P4-01.
  - Acceptance: UI state/error cases match `02_AppFlow.md`.
- [ ] P4-03 Implement donor search filters and pagination.
  - Depends on: P3-04.
  - Acceptance: exact blood-group filter; no private fields; query count bounded.
- [ ] P4-04 Implement search rate limiting and abuse controls.
  - Depends on: P4-03.
  - Acceptance: throttle behavior tested.

## Phase 5 — Contact workflow and notifications

- [ ] P5-01 Implement contact request model and state transition service.
  - Depends on: P4-01, P3-04.
  - Acceptance: duplicate pending requests prevented; atomic transitions tested.
- [ ] P5-02 Implement accept/decline/cancel/expire actions.
  - Depends on: P5-01.
  - Acceptance: only addressed donor decides; idempotency and terminal states tested.
- [ ] P5-03 Implement consent-gated contact disclosure.
  - Depends on: P5-02, P2-04.
  - Acceptance: private fields absent before acceptance and absent if donor did not consent.
- [ ] P5-04 Implement in-app notification records.
  - Depends on: P5-01.
  - Acceptance: notification creation is durable and minimized.
- [ ] P5-05 Configure Redis and Celery for background notifications.
  - Depends on: P5-04.
  - Acceptance: retries bounded; duplicate delivery guarded; provider failures isolated.
- [ ] P5-06 Implement email/SMS adapters in sandbox or mock mode.
  - Depends on: P5-05.
  - Acceptance: credentials externalized; provider errors handled; no production send without approval.

## Phase 6 — Moderation and administration

- [ ] P6-01 Implement report and block models/services.
  - Depends on: P2-03.
  - Acceptance: block prevents new contact requests; report privacy tested.
- [ ] P6-02 Implement admin moderation workflows.
  - Depends on: P6-01.
  - Acceptance: least privilege and reasoned audit events.
- [ ] P6-03 Implement audit event service.
  - Depends on: P2-03.
  - Acceptance: sensitive actions logged without secrets/PII.
- [ ] P6-04 Implement basic aggregated analytics.
  - Depends on: P4-01, P5-01.
  - Acceptance: aggregate data only; no private donor disclosure.

## Phase 7 — API and mobile readiness

- [ ] P7-01 Implement DRF serializers and `/api/v1/` routing.
  - Depends on: P2-03, P3-03.
  - Acceptance: serializer allowlists and API tests pass.
- [ ] P7-02 Implement auth strategy for API clients.
  - Depends on: P7-01.
  - Acceptance: token expiry, rotation/revocation and permissions tested.
- [ ] P7-03 Implement donor, request and contact endpoints.
  - Depends on: P4-01, P5-02.
  - Acceptance: OpenAPI schema and contract tests pass.
- [ ] P7-04 Publish API documentation and sample requests.
  - Depends on: P7-03.
  - Acceptance: examples contain no real user data.

## Phase 8 — Security, quality and release readiness

- [ ] P8-01 Complete unit and integration test suite.
  - Depends on: all implemented core phases.
  - Acceptance: critical flows and permission boundaries covered.
- [ ] P8-02 Run dependency and static security checks.
  - Depends on: P8-01.
  - Acceptance: no unresolved critical/high issue without documented mitigation.
- [ ] P8-03 Run manual privacy/authorization review.
  - Depends on: P8-01.
  - Acceptance: donor private data protected across all endpoints and templates.
- [ ] P8-04 Run Playwright end-to-end tests.
  - Depends on: P8-01.
  - Acceptance: registration → donor search → contact request → accept flow passes.
- [ ] P8-05 Run Locust performance test and publish workload/results.
  - Depends on: staging deployment.
  - Acceptance: workload, environment, latency percentiles and error rate documented.
- [ ] P8-06 Verify backup and restore procedure.
  - Depends on: staging/production database.
  - Acceptance: restore test evidence recorded.
- [ ] P8-07 Complete release checklist.
  - Depends on: P8-01 through P8-06.
  - Acceptance: `15_Release_Checklist.md` signed off.

## Phase 9 — Deployment and documentation

- [ ] P9-01 Create Docker/Compose development environment.
  - Depends on: P1-03, P5-05.
  - Acceptance: clean setup works from documented commands.
- [ ] P9-02 Configure staging deployment.
  - Depends on: P9-01.
  - Acceptance: HTTPS, health checks, environment secrets and migrations work.
- [ ] P9-03 Configure production settings and deployment checklist.
  - Depends on: P9-02.
  - Acceptance: Django deployment checks pass; DEBUG disabled.
- [ ] P9-04 Complete user guide and technical documentation.
  - Depends on: verified implementation.
  - Acceptance: docs match shipped behavior.
- [ ] P9-05 Prepare demonstration and viva evidence.
  - Depends on: P9-04.
  - Acceptance: demo uses synthetic accounts/data and known limitations are disclosed.

## Phase 10 — Future work (deferred)

- [>] P10-01 Flutter Android client — DEFERRED; post-MVP mobile roadmap.
- [>] P10-02 Flutter iOS client — DEFERRED; post-MVP mobile roadmap.
- [>] P10-03 Organization portal and verification workflow — DEFERRED; optional/future and not a core-flow dependency.
- [>] P10-04 Authorized DGHS FHIR integration feasibility and approval — DEFERRED; requires formal authorization, documented basis and security review.
- [>] P10-05 Authorized identity verification feasibility and approval — DEFERRED; requires formal authorization and security review.
- [>] P10-06 Production SMS provider onboarding — DEFERRED; credentials, provider review and operational approval required.
- [>] P10-07 RLS defense-in-depth evaluation — DEFERRED; requires dedicated design and connection-pooling tests.
- [>] P10-08 National-scale capacity and disaster-recovery validation — DEFERRED; no capacity claim until workload and measured evidence exist.

## 3. Current execution log

| Date | Task ID | Status | Files changed | Commands run | Actual result | Remaining issues |
|---|---|---|---|---|---|---|
| 2026-11-06 | P0-01 | VERIFIED | `docs/06_Plan.md` (planning record only) | `rg --files`; initial `git status --short`; `Get-Content -Raw` on agent instructions, README, all `docs/*` and Cursor project rules | All required docs exist and were read; manual review found architecture and safety boundaries aligned. Repository initially contained documentation/guardrails only; no application tests were run. | P0-02 completed. |
| 2026-11-06 | P0-02 | VERIFIED | `.gitignore`, `docs/EXECUTION_STATE.md`, `docs/06_Plan.md` | `git init`; `git check-ignore` assertions for secret, venv, cache, media and DB examples; `.env.example` allowlist check; `git status --short --branch` | Git initialized on `master`; all ignore assertions passed and `.env.example` remains trackable. Commit: `a368617`. | P0-03 is complete. |
| 2026-11-06 | P0-03 | VERIFIED | `README.md`, `CONTRIBUTING.md`, `.env.example`, `docs/06_Plan.md`, `docs/EXECUTION_STATE.md` | PowerShell assertions for deployment environment names, blank example values and README setup references | Setup sequence and environment names documented. Commands dependent on future P1/P9 files are labelled as future; no claim of a running application. Commit: `11f4e19`. | P1-01 and P1-02 are complete. |
| 2026-11-06 | P1-01 | VERIFIED | `.python-version`, `README.md`, `docs/04_TRD.md`, `docs/06_Plan.md`, `docs/12_Architecture_ADRs.md`, `docs/REFERENCES.md`, `requirements/*`, `docs/EXECUTION_STATE.md` | `py -3.14 --version`; `winget install Python.Python.3.14`; official Python/Django/DRF/Gunicorn docs and PyPI metadata review; uv 0.13.7 universal hash compile; `uv pip sync`; `python -m pip install --dry-run --require-hashes -r requirements/dev.lock`; `python -m pip check`; `pip-audit --strict` | Python 3.14.10 verified; universal base/dev locks contain 36/101 distributions. pip hash dry-run and dependency check passed; pip-audit reported no known vulnerabilities. uv used after pip-tools timed out hashing hundreds of published artifacts; generator choice documented. | P1-01 and P1-02 are committed as `567ca14`. Linux production installation will be verified during CI/deployment. |
| 2026-11-06 | P1-02 | VERIFIED | `manage.py`, `config/`, `tests/`, `README.md`, `docs/06_Plan.md`, `docs/EXECUTION_STATE.md` | `pytest --ds=config.settings.test tests/test_settings_profiles.py`; `python manage.py check`; `DJANGO_SETTINGS_MODULE=config.settings.development python manage.py check` | Django project scaffold created with separate shared, development, test and production settings. Both checks passed; profile tests passed (2/2), including production fail-closed behavior. No migrations were created. | P1-03 PostgreSQL URL configuration is complete and validated; live database connectivity remains untested because the host has no PostgreSQL service or running Docker daemon. |
| 2026-11-06 | P1-03 | VERIFIED (CONFIGURATION) | `config/database.py`, `config/settings/`, `tests/test_settings_profiles.py`, `README.md`, `docs/06_Plan.md`, `docs/EXECUTION_STATE.md` | `pytest --ds=config.settings.test tests`; development and production `manage.py check` with synthetic PostgreSQL URLs; `python -m bandit -q -r config`; local service/port inspection | URL parser and environment settings validated; seven tests pass; both Django checks pass; Bandit reports no issues. No migrations were run. | Live PostgreSQL connection was not tested because no service is installed/listening and the Docker daemon is unavailable. Defer connection/migration smoke test until P1-06 with a database service. |
| 2026-11-06 | P1-04 | VERIFIED | `config/urls.py`, `config/settings/`, `templates/`, `static/`, `tests/test_public_pages.py`, `docs/04_TRD.md`, `docs/REFERENCES.md`, `docs/06_Plan.md`, `docs/EXECUTION_STATE.md` | `pytest --ds=config.settings.test tests`; development `manage.py check`; production `manage.py collectstatic --noinput`; `python -m bandit -q -r config` | Six public information pages render; responsive layout, reduced-motion support, local Bootstrap 5.3.8 assets and safety/privacy copy are covered by tests. 12 tests pass; production static collection post-processed 726 assets; Bandit found no issues. Legal terms/privacy are explicitly drafts requiring local review. | No browser-based viewport test yet; Playwright UI coverage remains in P8. Product pages are information-only; donor discovery and account features remain unimplemented. |
| 2026-11-06 | P1-05 | VERIFIED | `config/health.py`, `config/logging.py`, `config/middleware.py`, `config/database.py`, `config/settings/base.py`, `config/urls.py`, `tests/test_health_logging.py`, `docs/04_TRD.md`, `docs/06_Plan.md`, `docs/EXECUTION_STATE.md` | `pytest --ds=config.settings.test tests`; development `manage.py check`; `python -m bandit -q -r config`; `git diff --check` | Liveness/readiness and JSON request logs are implemented; tests verify no URL/query/contact/credential fields are emitted and dependency statuses stay distinct. Full suite 21/21, Django check passed, Bandit reports no issues. | Service behavior against live PostgreSQL/Redis remains untested; no services are available on this host. |
| 2026-11-06 | P1-06 | VERIFIED | `apps/accounts/`, `config/settings/base.py`, `tests/test_accounts_user.py`, `docs/12_Architecture_ADRs.md`, `docs/06_Plan.md`, `docs/EXECUTION_STATE.md` | Docker Engine/volume/service inspection; Django PostgreSQL connection probe; `manage.py migrate --noinput --settings=config.settings.development`; `manage.py showmigrations accounts`; development `manage.py check`; PostgreSQL catalog query; `pytest --ds=config.settings.test tests` (31 tests); migration consistency check | Dedicated `bcbd_dev` role/database on an existing PostgreSQL 17.11 service with persistent Docker storage. Django connected as that user; all migrations including `accounts.0001_initial` applied, migration marked applied and expected identifier constraint/indexes exist; 31 tests pass. Verification checkpoint commit: `3bb5092`. | Existing Supabase stack remains running and untouched except for the isolated role/database. Local `.env` is ignored by Git. |
| 2026-11-06 | P2-01 | VERIFIED | `apps/accounts/authentication.py`, `apps/accounts/forms.py`, `apps/accounts/throttling.py`, `apps/accounts/urls.py`, `apps/accounts/views.py`, `config/settings/`, `config/urls.py`, `templates/accounts/`, `templates/base.html`, `templates/pages/home.html`, `tests/test_account_auth_flows.py`, `tests/test_public_pages.py`, `tests/test_settings_profiles.py`, `.env.example`, `docs/09_Deployment.md`, `docs/12_Architecture_ADRs.md`, `docs/06_Plan.md`, `docs/EXECUTION_STATE.md`, `README.md` | `pytest --ds=config.settings.test tests` (46 tests); development and production `manage.py check`; PostgreSQL `manage.py migrate --check`; `python -m bandit -q -r apps/accounts config`; `git diff --check` | 14 authentication tests pass within 46 total tests; auth/check/migration/Bandit/diff checks pass. Registration, email/phone login, pending-state enforcement, verified-email reset, logout, CSRF, abuse throttles and redacted logging are covered. Commit: `9a74653`. | No authorized production SMTP provider; local in-memory mail backend used. P2-02 supplies account verification/phone recovery, P2-04 records acknowledgements, and P5-05 supplies shared Redis throttling. |
| 2026-11-06 | P2-02 | VERIFIED | `apps/accounts/models.py`, `apps/accounts/migrations/0002_verificationchallenge.py`, `apps/accounts/migrations/0003_verificationchallenge_accounts_ve_expires_fb4ecf_idx.py`, `apps/accounts/verification.py`, `apps/accounts/forms.py`, `apps/accounts/views.py`, `apps/accounts/urls.py`, `apps/accounts/management/commands/purge_verification_challenges.py`, `config/settings/`, `templates/accounts/`, `tests/test_account_verification.py`, `tests/test_account_auth_flows.py`, `docs/05_Schema.md`, `docs/12_Architecture_ADRs.md`, `docs/06_Plan.md`, `docs/EXECUTION_STATE.md`, `README.md` | `manage.py makemigrations accounts --settings=config.settings.test`; PostgreSQL `manage.py migrate --noinput --settings=config.settings.development`; `manage.py showmigrations accounts`; PostgreSQL constraint/index catalog query; `pytest --ds=config.settings.test tests` (60 tests); development `manage.py check`; PostgreSQL `manage.py migrate --check`; `manage.py purge_verification_challenges --settings=config.settings.development`; `python -m bandit -q -r apps/accounts config`; `git diff --check` | 13 verification tests pass within 60 total tests; PostgreSQL `0002`/`0003` migrations applied and catalog constraints/indexes present; development/migration/cleanup/Bandit/diff checks pass. Covers code HMAC, 10-minute expiry, five tries, single use, resend invalidation/cooldown and caps, generic response, OTP log redaction, phone reset, and production registration fail-closed behavior. | Mock provider is process-memory only; no real delivery. Production verification stays unavailable until provider authorization and implementation. IP throttles require P5-05 Redis for cross-process enforcement; schedule cleanup command in deployment. |
| 2026-11-06 | P2-03 | VERIFIED | `apps/accounts/permissions.py`, `tests/test_account_permissions.py`, `docs/12_Architecture_ADRs.md`, `docs/06_Plan.md`, `docs/EXECUTION_STATE.md` | `pytest --ds=config.settings.test tests/test_account_permissions.py` (6 tests); full `pytest --ds=config.settings.test tests` (66 tests); development `manage.py check`; PostgreSQL `manage.py migrate --check`; `manage.py makemigrations --check --dry-run --settings=config.settings.test`; `python -m bandit -q -r apps/accounts config`; `git diff --check` | Six permission tests and all 66 tests pass; Django check, PostgreSQL migration check, migration consistency, Bandit and diff checks pass. Active-account, explicit role and exact object-owner permission classes implemented. | Donor role binds to the donor profile in P3-02; organization role is reserved for future implementation. Moderation groups and fine-grained permissions need provisioning in moderation tasks. |
| 2026-11-06 | P2-04 | VERIFIED | `apps/governance/`, `apps/governance/migrations/0001_initial.py`, `apps/accounts/forms.py`, `apps/accounts/views.py`, `config/settings/base.py`, `config/urls.py`, `templates/accounts/register.html`, `templates/governance/privacy_settings.html`, `templates/pages/privacy.html`, `templates/base.html`, `tests/test_consent_privacy.py`, `tests/test_account_auth_flows.py`, `docs/05_Schema.md`, `docs/12_Architecture_ADRs.md`, `docs/06_Plan.md`, `docs/EXECUTION_STATE.md`, `README.md` | `pytest --ds=config.settings.test tests/test_consent_privacy.py tests/test_account_auth_flows.py` (19 tests); full `pytest --ds=config.settings.test tests` (70 tests); PostgreSQL `manage.py migrate --noinput`; `manage.py showmigrations governance`; PostgreSQL consent constraint/index catalog query; development `manage.py check`; PostgreSQL `manage.py migrate --check`; `manage.py makemigrations --check --dry-run`; Bandit; `git diff --check` | 4 focused consent/privacy tests pass within 70 total; PostgreSQL migration applied, two check constraints and consent index verified; Django/migration/Bandit/diff checks pass. | Terms and Privacy content remain draft; version defaults are `draft-1`. Choices do not enable discovery/contact sharing until dependent workflows enforce them. Retention/deletion policy remains unresolved. |
| 2026-11-06 | P3-01 | VERIFIED | `apps/locations/`, `apps/locations/migrations/0001_initial.py`, `tests/test_location_data.py`, `config/settings/base.py`, `docs/05_Schema.md`, `docs/12_Architecture_ADRs.md`, `docs/REFERENCES.md`, `docs/06_Plan.md`, `docs/EXECUTION_STATE.md`, `README.md` | `pytest --ds=config.settings.test tests/test_location_data.py` (6 tests); full `pytest --ds=config.settings.test tests` (76 tests); PostgreSQL `manage.py migrate --noinput`; `manage.py showmigrations locations`; PostgreSQL location constraint/index catalog query; development `manage.py check`; PostgreSQL `manage.py migrate --check`; `manage.py makemigrations --check --dry-run`; Bandit; `git diff --check` | Six location tests and full 76-test suite pass; PostgreSQL migration applied; three checks, root/child uniqueness and lookup indexes verified; Django/migration/Bandit/diff checks pass. Import process requires provenance and review metadata, validates hierarchy, records source/version, and is idempotent. | No official location dataset was loaded; source reconciliation/review is required before production location use. |
| 2026-11-06 | P3-02 | VERIFIED | `apps/donors/`, `apps/donors/migrations/0001_initial.py`, `config/settings/base.py`, `tests/test_donor_profile_model.py`, `docs/05_Schema.md`, `docs/06_Plan.md`, `docs/EXECUTION_STATE.md`, `README.md` | `pytest --ds=config.settings.test tests/test_donor_profile_model.py` (6 tests); full `pytest --ds=config.settings.test tests` (82 tests); PostgreSQL `manage.py migrate --noinput`; `manage.py showmigrations donors`; PostgreSQL donor constraint/index catalog query; development `manage.py check`; PostgreSQL `manage.py migrate --check`; `manage.py makemigrations --check --dry-run`; Bandit; `git diff --check` | Six model tests and all 82 tests pass; migration applied, four enum checks/four search indexes/unique user index verified; Django, migration, Bandit and diff checks pass. Profile constraints/defaults match schema; location consistency and role derivation covered. | Profile editing/consent enforcement is P3-03/P3-04; no real location seed; no clinical eligibility logic. |
| 2026-11-06 | P3-03 | VERIFIED | `apps/donors/forms.py`, `apps/donors/services.py`, `apps/donors/views.py`, `apps/donors/urls.py`, `apps/governance/forms.py`, `apps/governance/views.py`, `config/urls.py`, `templates/donors/profile_form.html`, `templates/base.html`, `tests/test_donor_profile_flows.py`, `tests/test_consent_privacy.py`, `docs/06_Plan.md`, `docs/EXECUTION_STATE.md`, `README.md` | `pytest --ds=config.settings.test tests/test_donor_profile_flows.py tests/test_consent_privacy.py` (9 tests); full `pytest --ds=config.settings.test tests` (87 tests); development `manage.py check`; PostgreSQL `manage.py migrate --check`; `manage.py makemigrations --check --dry-run`; Bandit; `git diff --check` | Five donor flow tests and four consent regression tests pass within 87 total; owner-only profile writes, versioned contact consent, channel verification, pause/deactivation and stale-consent suppression pass. Django, migration, Bandit and diff checks pass. | Reviewed geography data is not loaded, so profile form has no real location options. Actual disclosure must additionally require an accepted contact request and current consent. |
| 2026-11-06 | P3-04 | VERIFIED | `apps/donors/models.py`, `apps/donors/forms.py`, `apps/donors/services.py`, `apps/donors/views.py`, `apps/governance/models.py`, `tests/test_donor_discovery_policy.py`, `tests/test_donor_profile_flows.py`, `tests/test_consent_privacy.py`, `docs/06_Plan.md`, `docs/EXECUTION_STATE.md`, `README.md` | `pytest --ds=config.settings.test tests/test_donor_discovery_policy.py tests/test_donor_profile_flows.py tests/test_consent_privacy.py` (14 tests); full `pytest --ds=config.settings.test tests` (92 tests); synthetic PostgreSQL discoverability query in a transaction rolled back; development `manage.py check`; PostgreSQL `manage.py migrate --check`; `manage.py makemigrations --check --dry-run`; Bandit; `git diff --check` | Three discovery tests, six donor flow tests, five consent tests and all 92 tests pass. The PostgreSQL synthetic query returns the eligible profile and rolls back every fixture row. The discoverable queryset excludes profiles unless every active/available/visible/current-consent/location condition passes. Development, migration consistency, Bandit and diff checks pass. | Public search endpoint/result allowlist remains P4-03; no real location snapshot is loaded. |

## 4. Update template

Append one row per completed task:

| Date | Task ID | Status | Files changed | Commands run | Actual result | Remaining issues |
|---|---|---|---|---|---|---|

Do not fill in passing test results until commands have actually been run against the implementation repository.
