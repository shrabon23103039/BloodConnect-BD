# BloodConnect BD — Execution State

## Current status
- Overall: In progress
- Current phase: Phase 3 — Locations and donor profiles
- Current task ID: P3-03
- Last updated: 2026-11-06
- Git branch: master

## Completed tasks
- [x] P0-01 — Verify context documents and inspect repository baseline
  - Implementation: Read the required project instructions and documentation; confirmed the repository initially contained documentation/guardrails only.
  - Verification: Required files present and manually reviewed. No application tests existed or were run.
  - Commit: None; repository was not initialized.
- [x] P0-02 — Initialize Git repository and `.gitignore`
  - Implementation: Initialized Git and added ignore patterns for secrets, Python environments/caches, local databases, local media, logs and generated build/test output. `.env.example` remains trackable.
  - Verification: `git check-ignore` assertions passed for representative secret, environment, database, media and cache paths; `.env.example` was not ignored.
  - Commit: `a368617` (`chore: initialize repository baseline`).
- [x] P0-03 — Create README and contribution/development instructions
  - Implementation: Added staged setup commands, environment variable template, and contribution workflow. Commands requiring Django, lock, or Compose files are labelled by the task that will create them.
  - Verification: PowerShell assertions confirmed every variable documented in `docs/09_Deployment.md` is present in `.env.example` with a blank value and the README contains the setup references.
  - Commit: `11f4e19` (`docs: add development setup and contribution guide`), which also records the original context pack in Git.

- [x] P1-01 — Verify Python/Django/DRF compatibility and pin exact dependency versions
  - Implementation: Installed Python 3.14.10; reviewed official compatibility/security information; selected compatible direct pins and recorded ADR-010/011; added universal hash locks. uv 0.13.7 was selected after pip-tools timed out while hashing platform wheels; regeneration commands are documented in the TRD.
  - Verification: uv resolved 36 runtime and 101 development distributions; `uv pip sync` installed the dev lock; pip `--require-hashes` dry-run passed; `pip check` found no broken requirements; `pip-audit --strict` found no known vulnerabilities.
  - Files changed: `.python-version`, `README.md`, `docs/04_TRD.md`, `docs/06_Plan.md`, `docs/12_Architecture_ADRs.md`, `docs/REFERENCES.md`, `requirements/base.in`, `requirements/dev.in`, `requirements/base.lock`, `requirements/dev.lock`, `requirements/LOCK_REPORT.md`.
  - Commit: `567ca14` (`feat: bootstrap Django runtime and settings`; includes P1-01 and P1-02).

- [x] P1-02 — Create Django project and environment-specific settings
  - Implementation: Added the `config` project package, split shared/development/test/production settings, and set development defaults in `manage.py` with production defaults for ASGI/WSGI. Production settings require a secret, explicit hosts and HTTPS CSRF origins, disable DEBUG, and set secure cookie/HTTPS controls. No migration or domain model was created.
  - Verification: `pytest --ds=config.settings.test tests/test_settings_profiles.py` passed (2 tests); `python manage.py check` passed under default development settings and under explicitly selected development settings. Tests verify isolated test settings and production fail-closed behavior.
  - Files changed: `manage.py`, `config/`, `tests/`, `README.md`, `docs/06_Plan.md`.
  - Commit: `567ca14` (`feat: bootstrap Django runtime and settings`). No migrations were created.

- [x] P1-03 — Configure PostgreSQL and psycopg
  - Implementation: Added a standard-library PostgreSQL URL parser with an explicit query-option allowlist and credential-safe errors. Development and production require PostgreSQL URLs; production additionally requires database TLS. The test profile alone uses in-memory SQLite. README now explains shell environment values and the `.env` behavior.
  - Verification: `pytest --ds=config.settings.test tests` passed (7 tests); development and production `manage.py check` passed using synthetic PostgreSQL URLs; `python -m bandit -q -r config` reported no issues.
  - Files changed: `config/database.py`, `config/settings/`, `tests/test_settings_profiles.py`, `README.md`, `docs/06_Plan.md`.
  - Limitation: no PostgreSQL service is installed/listening and Docker daemon is unavailable, so no live connection was attempted. No migrations were run; first migration remains deferred to P1-06.
  - Commit: `eafb787` (`feat: configure PostgreSQL database URLs`).

- [x] P1-04 — Configure static files, templates and Bootstrap
  - Implementation: Added responsive Django templates and public home, how-it-works, privacy, safety, draft terms and contact information pages. Vendored Bootstrap 5.3.8 with its MIT license and source maps, configured WhiteNoise production storage and local static paths, and included reduced-motion/accessibility support. Public pages clearly disclose planned features and draft legal status.
  - Verification: `pytest --ds=config.settings.test tests` passed (12 tests); development `manage.py check` passed; production `collectstatic --noinput` post-processed 726 assets; `python -m bandit -q -r config` reported no issues.
  - Files changed: `config/urls.py`, `config/settings/`, `templates/`, `static/`, `tests/test_public_pages.py`, `docs/04_TRD.md`, `docs/REFERENCES.md`, `docs/06_Plan.md`.
  - Limitation: Playwright viewport checks are planned for P8; legal/privacy notices are drafts pending qualified local review. Donor discovery and account creation are not available.
  - Commit: `a4a4ecd` (`feat: add public product and safety pages`).

## Completed task
- [x] P1-05 — Add health/readiness endpoints and structured logging
  - Implementation: Added dependency-free liveness and DB/Redis readiness endpoints with separate status values and non-cacheable responses. Request middleware emits server-generated correlation IDs. JSON formatter logs only allowlisted metadata and omits URL paths, query strings, message bodies and exception text.
  - Verification: `pytest --ds=config.settings.test tests` passed (21 tests); development `manage.py check` passed; `python -m bandit -q -r config` reported no issues. Tests verify liveness independent of dependencies, status separation, safe timeouts, correlation IDs and redaction.
  - Files changed: `config/health.py`, `config/logging.py`, `config/middleware.py`, `config/database.py`, `config/settings/base.py`, `config/urls.py`, `tests/test_health_logging.py`, `docs/04_TRD.md`, `docs/06_Plan.md`.
  - Limitation: live DB/Redis behavior cannot be exercised on this host; readiness correctly reports not ready when dependencies are missing.
  - Commit: `5e3467d` (`feat: add health checks and privacy-safe logs`).

## Completed task
- [x] P1-06 — Create custom User model before the first production migration
  - Implementation: Added `apps.accounts.User` with UUID key, exactly one normalized email or E.164 phone identifier, case-insensitive email uniqueness, identifier/status constraints, hashed-password manager, verification timestamps, and `PENDING`/`ACTIVE`/`SUSPENDED`/`DEACTIVATED` status behavior. Set `AUTH_USER_MODEL` before generating `accounts.0001_initial`; ADR-012 records the selected identity policy.
  - Verification: `pytest --ds=config.settings.test tests` passed (31 tests, including 10 account tests); test/production Django checks, migration consistency, SQLite migration and Bandit passed. Docker Engine 29.9.2 reported an existing healthy PostgreSQL 17.11 service with persistent storage. Created an isolated `bcbd_dev` role and `bloodconnect_bd_dev` database; Django connected as that role and `manage.py migrate --noinput --settings=config.settings.development` applied `accounts.0001_initial` and all remaining migrations. `showmigrations` confirmed it applied; PostgreSQL catalog confirmed the identifier check and indexes.
  - Files changed: `apps/accounts/`, `config/settings/base.py`, `tests/test_accounts_user.py`, `docs/12_Architecture_ADRs.md`, `docs/06_Plan.md`.
  - Remaining: None for P1-06. The local `.env` is ignored by Git and stores the generated development URL; no credential was printed. No unrelated container was stopped or removed.
  - Commit: `500b3f3` (`feat: add custom account identity model`); verification recorded in this checkpoint.

## Completed task
- [x] P2-01 — Implement registration, login, logout and password reset
  - Implementation: Added public registration and account pages; accepts exactly one normalized email or E.164 phone; active accounts can sign in through Django sessions using either identifier. Generic registration/login/reset messages reduce account enumeration. Logout is POST/CSRF protected. Verified-email password reset uses Django's one-time token flow. IP throttles use HMAC-derived keys. Local email uses Django's in-memory backend; production SMTP configuration is environment-driven and fails closed without credentials.
  - Verification: `pytest --ds=config.settings.test tests` passed (46 tests, including 14 auth tests); development and production `manage.py check` passed with synthetic PostgreSQL/SMTP configuration; PostgreSQL `manage.py migrate --check` passed; Bandit reported no issues in `apps/accounts/` and `config/`; `git diff --check` passed. Tests verify CSRF, generic responses, phone/email login, pending status, verified-email password reset and token use, throttling, and auth-log redaction.
  - Files changed: `apps/accounts/authentication.py`, `apps/accounts/forms.py`, `apps/accounts/throttling.py`, `apps/accounts/urls.py`, `apps/accounts/views.py`, `config/settings/`, `config/urls.py`, `templates/accounts/`, `templates/base.html`, `templates/pages/home.html`, `tests/test_account_auth_flows.py`, `tests/test_public_pages.py`, `tests/test_settings_profiles.py`, `.env.example`, `docs/09_Deployment.md`, `docs/12_Architecture_ADRs.md`, `docs/06_Plan.md`, `docs/EXECUTION_STATE.md`, `README.md`.
  - Limitations: new accounts remain pending until P2-02; phone recovery waits for verified-phone delivery in P2-02; versioned acknowledgement history is P2-04. Local-cache throttles are per process until P5-05 configures shared Redis. SMTP delivery was not tested and requires an authorized provider.
  - Commit: `9a74653` (`feat: implement web account authentication`).

## In-progress task
- [x] P2-02 — Implement verification adapter interface and mock provider
  - Implementation: Added database-backed verification challenges with UUIDs, keyed HMAC code digests, 10-minute expiry, five-attempt cap and one-time consumption. A provider protocol separates delivery from verification; the development/test mock stores messages only in bounded process memory and never logs OTPs. Account codes activate the existing email/phone identifier. Phone reset uses the same challenge service and a five-minute session grant. A purge command removes records over 24 hours expired.
  - Verification: Full suite passed (60 tests, including 13 verification tests); PostgreSQL migrations `accounts.0002` and `0003` applied; catalog confirms constraints/indexes; development `manage.py check`, PostgreSQL `migrate --check`, purge command, Bandit and `git diff --check` passed. Tests cover expiry, replay, attempts, cooldown/send caps, IP throttling, generic responses, log redaction, phone reset, retention cleanup and fail-closed registration without a delivery provider.
  - Files changed: `apps/accounts/models.py`, `apps/accounts/migrations/0002_verificationchallenge.py`, `apps/accounts/migrations/0003_verificationchallenge_accounts_ve_expires_fb4ecf_idx.py`, `apps/accounts/verification.py`, `apps/accounts/forms.py`, `apps/accounts/views.py`, `apps/accounts/urls.py`, `apps/accounts/management/commands/purge_verification_challenges.py`, `config/settings/`, `templates/accounts/`, `tests/test_account_verification.py`, `tests/test_account_auth_flows.py`, `docs/05_Schema.md`, `docs/12_Architecture_ADRs.md`, `docs/06_Plan.md`, `docs/EXECUTION_STATE.md`, `README.md`.
  - Limitations: mock delivery does not send real messages; production signup/verification remains unavailable until an authorized provider is implemented. IP throttles remain process-local until P5-05 configures Redis. P9 deployment must schedule the purge command.

## In-progress task
- [x] P2-03 — Implement roles and server-side permission classes
  - Implementation: Added DRF permissions for active accounts, explicit roles and exact object ownership. Uses built-in Django groups; staff does not imply moderator, superuser maps only to superadmin, donor role will follow profile existence, and ownership has no implicit staff/superuser bypass. ADR-015 records the policy.
  - Verification: Six focused permission tests and full suite (66 tests) pass. Tests deny anonymous/inactive/cross-user access and distinguish explicit moderator group membership from staff status. Development check, PostgreSQL `migrate --check`, `makemigrations --check --dry-run`, Bandit and diff checks pass.
  - Files changed: `apps/accounts/permissions.py`, `tests/test_account_permissions.py`, `docs/12_Architecture_ADRs.md`, `docs/06_Plan.md`, `docs/EXECUTION_STATE.md`.
  - Limitations: Donor profile and organization roles are not yet available; moderator permission provisioning belongs to moderation workflows.

## Completed task
- [x] P2-04 — Implement consent records and privacy settings
  - Implementation: Added append-only, purpose-specific consent records, versioned Terms/Privacy acknowledgements at registration, and an authenticated deny-by-default privacy settings page. Updates lock the account, append grant/refusal/withdrawal events and avoid duplicate events when state/version has not changed. ADR-016 records that settings remain inactive until dependent workflows enforce consent.
  - Verification: Four focused tests pass within the 70-test suite. PostgreSQL `governance.0001` applied; `showmigrations` marks it applied; catalog confirms two check constraints and the compound index. Development check, PostgreSQL `migrate --check`, migration consistency, Bandit and diff checks pass.
  - Files changed: `apps/governance/`, `apps/accounts/forms.py`, `apps/accounts/views.py`, `config/settings/base.py`, `config/urls.py`, `templates/accounts/register.html`, `templates/governance/privacy_settings.html`, `templates/pages/privacy.html`, `templates/base.html`, `tests/test_consent_privacy.py`, `tests/test_account_auth_flows.py`, `docs/05_Schema.md`, `docs/12_Architecture_ADRs.md`, `docs/06_Plan.md`, `docs/EXECUTION_STATE.md`, `README.md`.
  - Limitations: Terms/Privacy text and policy versions remain drafts pending legal review; retention/deletion policy is unresolved. Choices do not expose data until future donor/contact flows enforce them.

## Completed task
- [x] P3-01 — Create location models and reviewed Bangladesh geography seed process
  - Implementation: Added UUID location hierarchy (Division > District > Upazila), parent-level validation, case-insensitive uniqueness, source/version fields and a transactional offline JSON import command. Import requires explicit review confirmation plus source URL/version/reviewer/date metadata, validates all paths before writes and prints the snapshot SHA-256. ADR-017 records why no API or unreviewed snapshot is used.
  - Verification: Six focused tests pass within the 76-test suite. PostgreSQL `locations.0001` applied; catalog confirms three checks, root and child uniqueness indexes and lookup index. Development check, PostgreSQL `migrate --check`, migration consistency, Bandit and diff checks pass.
  - Files changed: `apps/locations/`, `config/settings/base.py`, `tests/test_location_data.py`, `docs/05_Schema.md`, `docs/12_Architecture_ADRs.md`, `docs/REFERENCES.md`, `docs/06_Plan.md`, `docs/EXECUTION_STATE.md`, `README.md`.
  - Limitation: No real geography snapshot has been loaded. The BBS catalogue reviewed was dated 2016, and official National Portal pages had inconsistent displayed totals; reconcile and approve a current snapshot before profile/discovery use.

## Completed task
- [x] P3-02 — Implement donor profile model and migrations
  - Implementation: Added the schema-matched profile model, enum/database constraints, search indexes, owner relation and Division/District/Upazila hierarchy validation. Defaults are unavailable, draft, hidden, in-app only and no contact sharing. Donor role now follows active-account profile existence.
  - Verification: Six focused donor model tests pass within the full 82-test suite. PostgreSQL `donors.0001` applied; catalog confirms four enum checks, four search indexes and unique user index. Development check, PostgreSQL `migrate --check`, migration consistency, Bandit and diff checks pass.
  - Files changed: `apps/donors/`, `config/settings/base.py`, `tests/test_donor_profile_model.py`, `docs/05_Schema.md`, `docs/06_Plan.md`, `docs/EXECUTION_STATE.md`, `README.md`.
  - Limitations: Profile editing and consent enforcement remain P3-03/P3-04; no real location rows are loaded; no medical eligibility or compatibility logic exists.

## Next task
- Task ID: P3-03
- Exact next action: Implement owner-only donor profile create/update/pause/deactivate, reusing active-account/object permissions and enforcing versioned discoverability/contact consent at write time.
- Dependencies: P3-02, P2-04 and P3-01 verified; no production geography seed is available, so tests must use synthetic location rows.

## Verification
- Commands run: Initial repository inventory; `git init`; `git check-ignore` assertions; `winget install/show Python.Python.3.14`; `py -3.14 --version`; package compatibility queries; uv universal lock generation; `uv pip sync`; pip hash dry-run; `pip check`; `pip-audit --strict`.
- Tests passed: P0-02 ignore assertions; P0-03 environment documentation assertions; P1-01 hash lock dry-run, dependency consistency and vulnerability audit; P1-02 settings tests (2/2) and development Django checks; P1-03 configuration tests (7/7), dev/prod Django checks and Bandit configuration scan; P1-04 full suite (12/12), development Django check, production static collection and Bandit configuration scan; P1-05 full suite (21/21), development Django check and Bandit configuration scan; P1-06 full suite (31/31), test/production Django checks, SQLite and PostgreSQL migrations, PostgreSQL migration inspection, migration consistency check and Bandit scan; P2-01 full suite (46/46), dev/prod Django checks, PostgreSQL migration check, Bandit and diff checks; P2-02 full suite (60/60), PostgreSQL verification migrations/catalog, development check, migration consistency, cleanup command, Bandit and diff checks; P2-03 focused permission tests (6/6), full suite (66/66), development check, PostgreSQL migration check, migration consistency, Bandit and diff checks; P2-04 focused consent/auth tests (19/19), full suite (70/70), PostgreSQL governance migration/catalog checks, development check, migration consistency, Bandit and diff checks; P3-01 location tests (6/6), full suite (76/76), PostgreSQL location migration/catalog checks, development check, migration consistency, Bandit and diff checks; P3-02 donor model tests (6/6), full suite (82/82), PostgreSQL donor migration/catalog checks, development check, migration consistency, Bandit and diff checks.
- Tests failed: None.
- Tests not run and why: Live SMTP/SMS verification delivery is not authorized or configured; P2-02 uses an in-memory mock. Cross-process throttle behavior awaits the shared Redis configuration in P5-05.

## Decisions
- Decision: Ignore `.env` and `.env.*` while explicitly allowing `.env.example`; exclude local DB files, media, virtual environments, caches and build/test artifacts.
- Reason: Match P0-02 acceptance and avoid committing secrets or local user data.
- Related ADR/document: `docs/06_Plan.md`, `docs/07_Security.md`, `docs/09_Deployment.md`.
- Decision: Use Python 3.14.10 with Django 5.2.19, DRF 3.18.3, direct packages pinned in `requirements/*.in`, and universal uv-generated hash locks; move Gunicorn to the current supported release line.
- Reason: Python 3.13.18 is source-only; Django 5.2 supports Python 3.14. Upstream marks Gunicorn 23.0.0 unsupported. pip-tools artifact hashing timed out, while uv completed universal lock resolution in seconds.
- Related ADR/document: ADR-010 and ADR-011 in `docs/12_Architecture_ADRs.md`; official release/security sources in `docs/REFERENCES.md`.
- Decision: Use Django session auth, a custom email/phone identifier backend, verified-email password reset, HMAC-keyed IP throttles (login 10/minute, registration and reset 5/hour), local in-memory development email, and environment-configured production SMTP.
- Reason: Preserve pending-until-verified account policy, avoid new dependencies, prevent account enumeration and keep reset tokens out of terminal logs. Record consent acknowledgement in the versioned consent task.
- Related ADR/document: ADR-012 and ADR-013 in `docs/12_Architecture_ADRs.md`; P2-02 phone verification and P2-04 consent history remain dependencies.
- Decision: Use six-digit OTP codes with keyed HMAC digests, ten-minute expiry, five attempts, 60-second resend cooldown, three sends/account/purpose/hour, five send requests/IP/hour, ten verification attempts/IP/hour, and 24-hour post-expiry metadata cleanup. Use only an in-memory mock provider until a real integration is authorized.
- Reason: Bound guessing and resend abuse, avoid storing/logging OTPs, and keep account activation tied to proof of control over its existing identifier.
- Related ADR/document: ADR-014 in `docs/12_Architecture_ADRs.md`; scheduled cleanup and shared Redis throttles are P9/P5 follow-up work.

## Blockers requiring owner input
- None.

## Resume instructions
- Re-read project instructions and this checkpoint.
- Inspect Git status and actual repository state.
- Resume the first incomplete, unblocked task in `docs/06_Plan.md`.
