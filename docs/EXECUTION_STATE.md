# BloodConnect BD — Execution State

## Current status
- Overall: In progress
- Current phase: Phase 8 - Security, quality and release readiness (staging-dependent checks pending)
- Current task ID: P8-05 (blocked)
- Last updated: 2026-11-07
- Git branch: `master` (seven pre-push review files staged for the local cleanup commit; `.env` is ignored and untracked)
- Git remote: none configured; intended GitHub repository is unknown and no push was made.
- Checkpoint commit: `3aaf5c28ea6a9da2750b43f9ce8ce5d1755d0965` (`docs: record final review and local commit`).
- Latest verified local implementation commit: `d1a8c678d0de76b821b555d3bc99fdca7b65bd2a` (`feat: complete BloodConnect MVP workflows`); not pushed.

## Final local review and commit (2026-11-07)
- Reviewed the complete tracked diff and all new files (108 paths staged); confirmed no local `.env`, database, key or credential-shaped literal was included. The staged `git diff --check` passed after fixing whitespace in new files.
- Commit: `d1a8c678d0de76b821b555d3bc99fdca7b65bd2a` (`feat: complete BloodConnect MVP workflows`). No force-push, reset, clean, or history rewrite was used.
- Verification: full suite 167 tests and 6 subtests; Bandit no findings (existing B105 protocol-label suppression warning); pip-audit no known vulnerabilities; `pip check` clean; migrations consistent; Docker Compose config valid; Render YAML/static assertions pass; synthetic production deploy check reports no issues; `git diff --check` clean.
- Not verified: Render account-side Blueprint validation, provisioning, hosted deployment, HTTPS, hosted migrations/health, SMTP/provider delivery, staging load, restore, and release sign-off.
- Repository change has not been pushed. Render remains unauthorized and unused; no resources were created and no costs incurred. GitHub target and credentials are not configured in this checkout.

## Pre-GitHub-push secret and security audit (2026-11-07)

- **PASS: tracked inventory/history:** `git ls-files` enumerated 240 tracked files. Reviewed the current branch/history (24 commits); no database, backup, media upload or certificate/private-key artifact is tracked. No Git remote is configured; no push occurred.
- **PASS: history-aware secrets scan:** Gitleaks `git --log-opts="--all --full-history" --redact=100` scanned all 24 reachable commits (about 2.32 MB) and found no leaks. Scanner image digest: `sha256:c00b6bd0aeb3071cbcb79009cb16a60dd9e0a7c60e2be9ab65d25e6bc8abbb7f`. All scanner output was fully redacted.
- **WORKSPACE SCAN: local-only findings:** Gitleaks `dir --redact=100` scanned a temporary workspace snapshot including ignored local files, excluding `.git`, `.venv` and generated `staticfiles`. It reported two `generic-api-key` matches, both in the ignored, untracked `.env` (the local Django key and PostgreSQL password); the values were never recorded or printed. No workspace finding was in tracked files. `.env` remains excluded from Git and Docker and was left byte-for-byte unchanged. Do not copy it into tracked files or share it.
- **PASS: ignore controls:** `.gitignore` and `.dockerignore` exclude `.env`/`.env.*` while allowing `.env.example`, common private-key/certificate formats, cloud credential directories, local database/backup patterns, cloud/IDE credential directories, logs, and generated secret/credential files. `git check-ignore` assertions passed for 52 sensitive-path cases; `.env.example` remains trackable. The current local diff adds these extra exclusions; no staged files or untracked repository files were present at audit time.
- **PASS: example configuration:** `.env.example` has empty values for every assignment (placeholders only). Production Django reads the signing key, DB URL, Redis URL and SMTP credentials from environment variables; production fails closed when required values are absent. Render generates the Django key and uses service references plus protected `sync: false` SMTP values. Dockerfile has no secret-bearing build args or embedded credentials. No `.github` directory/workflows exist, so there are no GitHub Actions secrets/configuration to audit.
- **PASS: committed personal-data/artifact review:** no non-reserved-domain email-shaped value was found in tracked files. Bangladesh-phone-shaped candidates occur only in test files (synthetic fixtures) and one requirements-lock false positive; no actual phone values were copied into this checkpoint. No tracked user database, backup, uploaded document or media was found. Local `debug.log` is ignored; basic email/phone pattern checks found no matches.
- **LOCAL DATABASE PRESERVATION:** the active Compose PostgreSQL container is healthy and remains mounted to the existing `bloodconnect-bd_postgres_data` volume at `/var/lib/postgresql/data`; Compose still names this volume `postgres_data` under project `bloodconnect-bd`. The ignored `.env` `DATABASE_URL` targets the existing `bloodconnect_bd_dev` database on the Supabase container published at `127.0.0.1:55322`. A read-only TCP identity query using the exact `.env` credentials succeeded inside that target container; its `/var/lib/postgresql/data` mount is the existing `supabase_db_nirapatta-p112-fresh` volume. Compose application containers continue using their separate existing internal `db:5432` database and `bloodconnect-bd_postgres_data` volume. A direct host-side connection attempt timed out in this execution environment, so the host-to-published-port route was not independently verified. The `.env` file and both database volumes were not modified; no container was started/stopped, no migrations or writes were run, and no database was reset or recreated.
- **RESOLVED: Compose credential defaults:** tracked `compose.yaml` now requires `DJANGO_SECRET_KEY` and `POSTGRES_PASSWORD` from local environment/ignored `.env`; it retains only safe development defaults for database name/user and loopback ports. `.env.example` remains placeholder-only with blank values for every assignment. README documents local setup.
- **Verification after cleanup:** `docker compose config --quiet` passed; `.venv\Scripts\pytest.exe --ds=config.settings.test tests -q --tb=short -p no:cacheprovider` passed (167 tests, 6 subtests); `.env.example` all-empty assertion passed; `.env` is not tracked and `git check-ignore -v .env` confirms exclusion; `git diff --check` passed. Gitleaks history scan passed (24 commits, no leaks); workspace scan findings are limited to the two local `.env` values described above. A read-only PostgreSQL identity query through the `.env` target container succeeded; no migrations or writes were run.
- No Git remote was added and nothing was pushed, published or deployed. No secret values are disclosed here. At the time of this initial audit, its local changes remained uncommitted.

## Final GitHub pre-push review (2026-11-07)

- Reviewed the complete diff and staged the seven related files (`.dockerignore`, `.env.example`, `.gitignore`, `README.md`, `compose.yaml`, `docs/06_Plan.md`, `docs/EXECUTION_STATE.md`); no unstaged changes remain. Existing ignore-rule changes were preserved and included in this cleanup review.
- `.env` is untracked and ignored (`git check-ignore -v .env`); `.env.example` has 26 assignments and all values are blank. Compose requires `DJANGO_SECRET_KEY` and `POSTGRES_PASSWORD`; only database/user/loopback-port development defaults remain.
- Final checks: `docker compose config --quiet` passed; full pytest suite passed (167 tests, 6 subtests); `git diff --check` passed. Gitleaks scanned all 24 reachable commits with no leaks. Workspace scan reported two `generic-api-key` matches only in ignored `.env`; no committed secret finding.
- Docker inspection confirms the active Compose PostgreSQL container remains mounted to `bloodconnect-bd_postgres_data`, and the `.env` target container remains mounted to `supabase_db_nirapatta-p112-fresh`; both containers are running as before. No container lifecycle operation, database write, migration, volume change, reset or recreation was performed.
- The exact `.env` database credentials passed a read-only identity query against its target container. A direct host-side connection attempt timed out in this execution environment, so the published-port route remains unverified.
- Pending action at checkpoint: create the local cleanup commit from the inspected staged diff. No remote is configured and no push is authorized or planned.

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

## Completed task
- [x] P3-03 — Implement donor profile create/update/pause/deactivate
  - Implementation: Added a signed-in, owner-scoped donor profile editor and transactional service writes. Only verified contact methods appear as sharing choices; grants and withdrawals append versioned consent events. Current consent ledger state overrides a stale profile checkbox. Pause marks the donor unavailable; deactivation hides the profile, marks it unavailable and withdraws discovery consent. All mutations use POST.
  - Verification: Five focused donor flow tests and four consent regression tests pass within the full 87-test suite. Tests cover owner denial, verified-channel choices, consent grants/withdrawals, stale preference suppression, pause/deactivation and authentication. Development check, PostgreSQL `migrate --check`, migration consistency, Bandit and diff checks pass.
  - Files changed: `apps/donors/forms.py`, `apps/donors/services.py`, `apps/donors/views.py`, `apps/donors/urls.py`, `apps/governance/forms.py`, `apps/governance/views.py`, `config/urls.py`, `templates/donors/profile_form.html`, `templates/base.html`, `tests/test_donor_profile_flows.py`, `tests/test_consent_privacy.py`, `docs/06_Plan.md`, `docs/EXECUTION_STATE.md`, `README.md`.
  - Limitations: Real profile submission requires a reviewed location snapshot. Actual contact disclosure must additionally require an accepted contact request and current consent; that workflow is later in the plan.

## Completed task
- [x] P3-04 — Implement availability and visibility controls
  - Implementation: Added owner controls for availability and visibility, writing donor-discovery consent in the same transaction. Added `DonorProfile.objects.discoverable()` as the server-side eligibility queryset; it requires an active account/profile, `AVAILABLE`, visible, active location hierarchy and latest granted discovery consent. Consent timestamps are made strictly increasing per purpose so same-clock-time updates retain correct ordering.
  - Verification: Three focused discovery tests, six donor flow tests and five consent tests pass within the 92-test suite. Tests cover unavailable/paused/hidden/unchecked profiles, inactive accounts/locations, consent denial/revocation, owner grant/withdrawal, and preserving moderator suspension. A synthetic PostgreSQL query confirmed an eligible profile is returned and rolled back the fixture. Development check, PostgreSQL `migrate --check`, migration consistency, Bandit and diff checks pass.
  - Files changed: `apps/donors/models.py`, `apps/donors/forms.py`, `apps/donors/services.py`, `apps/donors/views.py`, `apps/governance/models.py`, `tests/test_donor_discovery_policy.py`, `tests/test_donor_profile_flows.py`, `tests/test_consent_privacy.py`, `docs/06_Plan.md`, `docs/EXECUTION_STATE.md`, `README.md`.
  - Limitations: Public search consumes this queryset in P4-03. No official location snapshot is loaded.

## Completed task
- [x] P4-01 - Implement blood request model and lifecycle service
  - Implementation: Added `requests_bloodrequest` schema, location hierarchy validation, constraints/indexes, active-owner creation/edit/transition services, and `expire_blood_requests` command. Status changes are transactional/owner scoped; due expiration uses bounded idempotent batches. ADR-018 records the expiry default and interpretation of fulfillment.
  - Verification: Seven focused tests and full suite (99/99) passed. PostgreSQL migration applied; catalog confirmed request table, constraints, foreign keys and indexes. Development check, PostgreSQL migration check, migration consistency, expiration command (0 due rows), Bandit and diff check passed.
  - Files changed: `apps/requests/`, `config/settings/base.py`, `tests/test_blood_requests.py`, `docs/12_Architecture_ADRs.md`, `docs/06_Plan.md`, `docs/EXECUTION_STATE.md`.
  - Limitation: Automatic expiration requires scheduling the command in deployment (P5/P9). It processes up to 500 due records per run.

## Completed task
- [x] P4-02 - Implement request create/edit/cancel/close screens
  - Implementation: Added requester-only request list, create/draft/publish, detail/edit, cancellation and requester-reported fulfillment routes/templates. Mutations use POST and P4-01 services. Replies are in-app-only per ADR-019; requester contact information is not disclosed.
  - Verification: Six focused web-flow tests and seven lifecycle tests pass; full suite passed (105/105). Development check, PostgreSQL `migrate --check`, migration consistency, Bandit and `git diff --check` passed.
  - Files changed: `apps/requests/forms.py`, `apps/requests/views.py`, `apps/requests/urls.py`, `apps/requests/services.py`, `config/urls.py`, `templates/requests/`, `templates/base.html`, `tests/test_blood_request_flows.py`, `docs/02_AppFlow.md`, `docs/12_Architecture_ADRs.md`, `docs/06_Plan.md`, `docs/EXECUTION_STATE.md`.
  - Limitations: Contact-request summaries await P5 workflows. Location tests use synthetic fixtures because the reviewed official geography snapshot is not loaded.

## Completed task
- [x] P4-03 - Implement donor search filters and pagination
  - Implementation: Added public `/app/donors/` search, exact blood-group and active hierarchical location filters, discovery-consent-gated availability, deterministic ordering and 20-item pagination. Cards use an explicit allowlist and do not include contact/account-private fields. Public guest access follows the PRD.
  - Verification: Five focused search tests and full suite passed (110/110). The pagination query-count test stays at or below 10 for 21 results. Development check, PostgreSQL `migrate --check`, migration consistency, Bandit and `git diff --check` passed.
  - Files changed: `apps/donors/search_forms.py`, `apps/donors/views.py`, `apps/donors/urls.py`, `templates/donors/search.html`, `templates/base.html`, `tests/test_donor_search.py`, `README.md`, `docs/06_Plan.md`, `docs/EXECUTION_STATE.md`.
  - Limitation: No reviewed official location snapshot is loaded; fixtures use synthetic location/profile rows. Contact action/profile detail remains dependent on P5 contact workflow tasks.

## Completed task
- [x] P4-04 - Implement search rate limiting and abuse controls
  - Implementation: Applied the existing HMAC-keyed fixed-window cache throttle to donor search for guests and authenticated users at 30 requests per remote IP per 60 seconds. Requests above the quota receive HTTP 429 with a 60-second `Retry-After` header. ADR-020 records the threshold and process-local cache limitation.
  - Verification: Seven focused donor-search tests and the full suite passed (112/112). Tests cover the quota boundary, Retry-After, raw-IP absence from the HMAC cache key and independent quotas per IP. Development Django check, PostgreSQL `migrate --check`, test-settings migration consistency, Bandit and `git diff --check` passed.
  - Files changed: `apps/donors/views.py`, `tests/test_donor_search.py`, `docs/12_Architecture_ADRs.md`, `docs/06_Plan.md`, `docs/EXECUTION_STATE.md`, `README.md`.
  - Limitation: The currently configured cache is process-local; P5-05 Redis configuration is required for cross-worker enforcement.

## Completed task
- [x] P5-01 - Implement contact request model and state transition service
  - Implementation: Added the UUID contact request model, pending-only partial unique constraint, row-locked creation/decision services, active-owner and donor-discoverability checks, blood-request ownership/state checks, and ADR-021 expiry (48 hours capped by the related request expiry).
  - Verification: Six focused service/schema tests and the full suite passed (118/118). Tests cover database duplicate prevention, active/discoverable donor requirements, request ownership/open state, donor-only accept/decline, recipient-only cancel, idempotency and late expiry. PostgreSQL migration `connections.0001` applied; development check, PostgreSQL `migrate --check`, test-settings migration consistency, Bandit and `git diff --check` passed.
  - Files changed: `apps/connections/`, `config/settings/base.py`, `tests/test_contact_requests.py`, `docs/05_Schema.md`, `docs/12_Architecture_ADRs.md`, `docs/06_Plan.md`, `docs/EXECUTION_STATE.md`, `README.md`.
  - Limitation: In-app notifications are P5-04 work. Private donor channels are returned only through the accepted-connection disclosure service.

## Completed task
- [x] P5-02 - Implement contact request actions and expiry
  - Implementation: Added authenticated recipient composer, incoming/outgoing lists and scoped detail pages; POST-only accept/decline/cancel actions; per-IP creation throttle (10 POST attempts/hour, ADR-022); and bounded `expire_contact_requests` service/command. Requester and donor pages omit private contact channels.
  - Verification: Ten focused contact workflow tests and full suite passed (122/122). Tests cover composer privacy, scoped details, POST-only actions, donor/recipient authorization, idempotency, terminal/expiry behavior and rate-limit boundary. Development check, PostgreSQL `migrate --check`, test-settings migration consistency, Bandit and `git diff --check` passed.
  - Files changed: `apps/accounts/throttling.py`, `apps/connections/forms.py`, `apps/connections/views.py`, `apps/connections/urls.py`, `apps/connections/services.py`, `apps/connections/management/commands/expire_contact_requests.py`, `config/urls.py`, `templates/connections/`, `templates/base.html`, `templates/donors/search.html`, `tests/test_contact_requests.py`, `docs/12_Architecture_ADRs.md`, `docs/06_Plan.md`, `docs/EXECUTION_STATE.md`, `README.md`.
  - Limitation: Rate limiting remains process-local until P5-05 configures shared Redis.

## Completed task
- [x] P5-03 - Implement consent-gated contact disclosure
  - Implementation: Added `Connection` records atomically on acceptance and a recipient-scoped connection page/service. Channel disclosure requires an active recipient, an active accepted connection, an active donor account, an explicitly enabled donor profile channel, a verified identifier and current purpose-specific consent.
  - Verification: Twelve focused contact tests and the full suite passed (124/124). Tests verify no connection disclosure before acceptance, no channels without current consent or after withdrawal, recipient-only access, and rendering of the allowed email. PostgreSQL migration `connections.0002` applied; development check, PostgreSQL migration check, test-settings migration consistency, Bandit and `git diff --check` passed.
  - Files changed: `apps/connections/models.py`, `apps/connections/migrations/0002_connection.py`, `apps/connections/services.py`, `apps/connections/views.py`, `config/urls.py`, `templates/connections/`, `tests/test_contact_requests.py`, `docs/05_Schema.md`, `docs/06_Plan.md`, `docs/EXECUTION_STATE.md`, `README.md`.
  - Limitation: Reporting/closing connections and notification delivery remain later tasks.

## Completed task
- [x] P5-04 - Implement in-app notification records
  - Implementation: Added the durable notification model and recipient-scoped list/read pages. Contact creation and accepted/declined/cancelled/expired transitions create fixed-copy in-app notifications in the same transaction. Notifications contain no contact channels, private request text or health details.
  - Verification: Fourteen focused contact workflow tests and full suite passed (126/126). Tests cover event creation/idempotency, notification minimization, owner-scoped list/read, and request authorization. PostgreSQL migration `notifications.0001` applied; development check, PostgreSQL migration check, test-settings migration consistency, Bandit and `git diff --check` passed.
  - Files changed: `apps/notifications/`, `apps/connections/services.py`, `config/settings/base.py`, `config/urls.py`, `templates/notifications/`, `templates/base.html`, `tests/test_contact_requests.py`, `docs/06_Plan.md`, `docs/EXECUTION_STATE.md`, `README.md`.
  - Limitation: Notifications are in-app only. External/background delivery awaits P5-05/P5-06.

## Completed task
- [x] P5-05 - Configure Redis and Celery for background notifications
  - Implementation: Configured Redis logical DB 0 for Django cache and DB 1 for Celery broker; Celery JSON-only serialization, late acknowledgements, bounded startup/publish/task retries, worker-loss rejection, time limits, no result backend, and periodic pending-notification redrive. Notification rows use the outbox pattern: enqueue after commit, stable UUID task IDs, row-locked idempotent processing, durable pending fallback and bounded redrive. ADR-023 documents the existing pinned-stack configuration.
  - Verification: Focused contact/settings tests (26) and full suite passed (130/130). Tests cover production Redis URL/config separation, malformed URL rejection without credentials in errors, bounded task retry settings, duplicate processing, stable task IDs, and queue failure isolation from the contact transaction. `notifications.0002` applied; development check, PostgreSQL migration check, test-settings migration consistency, Bandit and `git diff --check` passed.
  - Files changed: `config/__init__.py`, `config/celery.py`, `config/redis.py`, `config/settings/base.py`, `config/settings/production.py`, `config/settings/test.py`, `apps/notifications/models.py`, `apps/notifications/migrations/0002_alter_notification_delivery_status.py`, `apps/notifications/services.py`, `apps/notifications/tasks.py`, `tests/test_contact_requests.py`, `tests/test_settings_profiles.py`, `docs/09_Deployment.md`, `docs/12_Architecture_ADRs.md`, `docs/06_Plan.md`, `docs/EXECUTION_STATE.md`, `README.md`.
  - Limitation: No `REDIS_URL` is configured in this workspace, so live Redis/broker connectivity was not exercised. Local development uses process-local cache; production settings require Redis. External provider adapters are P5-06.

## Completed task
- [x] P5-06 - Implement mock email/SMS adapters
  - Implementation: Added email/SMS protocols and deterministic mock adapters. External-channel notification rows are created only in mock mode for verified channels and current optional-notification consent; workers recheck consent before delivery. Permanent delivery errors become `FAILED`, transient errors retry with bounded backoff, and production settings disable external channels (ADR-024).
  - Verification: Thirty focused contact/settings tests and full suite passed (134/134). Tests cover mock delivery and stable references, consent withdrawal, verified destinations, permanent failure isolation, production-disabled delivery, no destination/body leakage and provider-boundary settings. PostgreSQL migration `notifications.0003` applied; development check, PostgreSQL migration check, test-settings migration consistency, Bandit and `git diff --check` passed.
  - Files changed: `apps/notifications/adapters.py`, `apps/notifications/models.py`, `apps/notifications/migrations/0003_remove_notification_notify_channel_in_app_and_more.py`, `apps/notifications/services.py`, `apps/notifications/tasks.py`, `apps/notifications/views.py`, `config/settings/base.py`, `config/settings/production.py`, `config/settings/test.py`, `tests/test_contact_requests.py`, `tests/test_settings_profiles.py`, `docs/12_Architecture_ADRs.md`, `docs/06_Plan.md`, `docs/EXECUTION_STATE.md`, `README.md`.
  - Limitation: Only mock email/SMS adapters exist. No production provider was authorized or invoked.

## Completed task
- [x] P6-01 - Implement report and block models/services
  - Implementation: Added UUID reports and user blocks, controlled reasons, self-target checks, idempotent block creation, reporter-only retrieval and bilateral block eligibility checks in contact creation (ADR-025).
  - Verification: Four focused moderation tests and full suite passed (139/139). Tests cover controlled report reasons, self-report rejection, reporter privacy, self-block rejection, idempotent blocks and block prevention in either direction. PostgreSQL migration `moderation.0001` applied; development check, migration check, test-settings migration consistency, Bandit and `git diff --check` passed.
  - Files changed: `apps/moderation/`, `apps/connections/services.py`, `config/settings/base.py`, `tests/test_moderation_privacy.py`, `tests/test_contact_requests.py`, `docs/12_Architecture_ADRs.md`, `docs/06_Plan.md`, `docs/EXECUTION_STATE.md`, `README.md`.
  - Limitation: Moderator review/resolution controls are P6-02; report details are not exposed to reported users.

## Completed task
- [x] P6-02 - Implement admin moderation workflows
  - Implementation: Added a private report queue/detail workflow guarded by the explicit active `MODERATOR` group. Staff/superuser status alone grants no access. Added constrained POST-only status transitions with required terminal resolution reasons and redacted audit events (ADR-026).
  - Verification: Focused moderation tests passed (13/13); full suite passed (148/148 at task verification). PostgreSQL `audit.0001` applied; development check, migration check, migration consistency, Bandit and diff check passed.
  - Files changed: `apps/audit/`, `apps/moderation/`, `config/urls.py`, `templates/moderation/`, `tests/test_moderation_privacy.py`, `docs/12_Architecture_ADRs.md`, `docs/06_Plan.md`, `docs/EXECUTION_STATE.md`.
  - Limitation: Moderator group membership must be provisioned deliberately.

## Completed task
- [x] P6-03 - Implement redacted audit event service
  - Implementation: Added append-only PostgreSQL audit events with strict status/reason metadata allowlist. Transactional records cover consent, reports/blocks, blood-request and contact-request lifecycle, accepted contact disclosure, and moderation actions (ADR-027).
  - Verification: Focused audit/moderation/contact/consent tests passed (43/43); full suite passed (151/151). Development check, PostgreSQL migration check, migration consistency, Bandit and diff check passed.
  - Files changed: `apps/audit/`, `apps/governance/models.py`, `apps/connections/services.py`, `apps/requests/services.py`, `apps/moderation/services.py`, `tests/test_audit_events.py`, `tests/test_moderation_privacy.py`, `docs/12_Architecture_ADRs.md`, `docs/06_Plan.md`, `docs/EXECUTION_STATE.md`.
  - Limitation: Retention/access policy is a preproduction requirement; events do not reconstruct prior activity.

## Completed task
- [x] P6-04 - Implement basic aggregated analytics
  - Implementation: Added moderator-only fixed global counts for discoverable donor profiles, open public blood requests, pending contact requests and open reports. Counts below five, including zero, are suppressed; no dimensions, filters, exports or source records are returned (ADR-028).
  - Verification: Analytics tests passed (2/2); full suite passed (153/153). Development check, PostgreSQL migration check, test-settings migration consistency, Bandit and diff check passed. No migration was needed.
  - Files changed: `apps/analytics/`, `config/settings/base.py`, `config/urls.py`, `templates/analytics/`, `tests/test_analytics.py`, `docs/12_Architecture_ADRs.md`, `docs/06_Plan.md`, `docs/EXECUTION_STATE.md`.
  - Limitation: Coarse counts do not establish service outcomes or blood supplied; no additional metrics dimensions are approved.

## Completed task
- [x] P7-01 - Implement DRF serializers and `/api/v1/` routing
  - Implementation: Added API version root and OpenAPI schema route, session authentication baseline, page-number pagination (20) and explicit donor, blood-request and contact-request read serializers.
  - Verification: API baseline and allowlist tests passed (2/2); full suite passed (155/155). Development check, test-settings migration consistency, Bandit and diff check passed. No migration was needed.
  - Files changed: `apps/api/`, `config/settings/base.py`, `config/urls.py`, `tests/test_api_contract.py`, `docs/06_Plan.md`, `docs/EXECUTION_STATE.md`.
  - Limitation: Resource endpoints are P7-03; token auth is P7-02. Donor location output matches existing public search granularity.

## Completed task
- [x] P7-02 - Implement API-client authentication
  - Implementation: Added opaque bearer access/refresh token issue, rotation and family revocation. Only SHA-256 digests persist; access expires in 15 minutes, refresh in 30 days. Refresh replay revokes its family. Active account and expiry/revocation state are checked on bearer requests; IP throttles cover token operations. Issue/rotation/revocation events use the redacted audit log (ADR-029).
  - Verification: API token lifecycle tests passed (5/5 API tests total); full suite passed (158/158). PostgreSQL `api.0001` applied; development check, migration check, test-settings migration consistency, Bandit and diff check passed.
  - Files changed: `apps/api/`, `apps/api/migrations/0001_initial.py`, `config/settings/base.py`, `tests/test_api_contract.py`, `docs/05_Schema.md`, `docs/10_API_Contract.md`, `docs/12_Architecture_ADRs.md`, `docs/06_Plan.md`, `docs/EXECUTION_STATE.md`.
  - Limitation: PostgreSQL lookup is required for each bearer request; no performance evidence exists. Expired token-row retention cleanup remains operational work.

## Completed task
- [x] P7-03 - Implement donor, request and contact API endpoints
  - Implementation: Added paginated consent-gated donor search/detail; public and owner-scoped blood-request CRUD/lifecycle; participant-scoped contact-request create/list/detail/accept/decline/cancel; and connection list/detail/close. Existing domain services enforce authorization, notifications, audit and disclosure rules.
  - Verification: API contract/resource tests passed (11/11); full suite passed (164/164). OpenAPI schema validates with zero errors/warnings; development check, PostgreSQL migration check, test-settings migration consistency, Bandit and diff check passed. No new migration was needed.
  - Files changed: `apps/api/`, `apps/accounts/throttling.py`, `apps/connections/services.py`, `config/settings/base.py`, `config/urls.py`, `tests/test_api_contract.py`, `tests/test_api_resources.py`, `docs/06_Plan.md`, `docs/EXECUTION_STATE.md`.
  - Limitation: Location/reference and moderation API endpoints are outside P7-03; API performance remains unmeasured.

## Completed task
- [x] P7-04 - Publish API documentation and sample requests
  - Implementation: Added the API usage guide with synthetic request/auth examples, clarified mounted versus target routes, and documented privacy-aware responses and error correlation.
  - Verification: Manually checked the guide and contract for synthetic-only values; OpenAPI generation/validation passes with zero errors/warnings. No code or schema change was needed for the documentation task.
  - Files changed: `docs/10_API_Contract.md`, `docs/16_API_Usage_Guide.md`, `README.md`, `docs/06_Plan.md`, `docs/EXECUTION_STATE.md`.

## Completed task
- [x] P8-01 - Complete unit and integration test suite
  - Verification: Full suite passed (164/164), including web/API critical flows and permission boundaries. Pytest emitted one non-failing Windows cache warning (`WinError 183`); no tests failed.
  - Files changed: `tests/` (verification only), `docs/06_Plan.md`, `docs/EXECUTION_STATE.md`.

## Completed task
- [x] P8-03 - Manual privacy and authorization review
  - Verification: Reviewed donor search/detail, request public/owner views, contact/connection participant scope and accepted disclosure, moderation, analytics, audit metadata, templates and request logging. Focused API resource tests passed (6/6); full suite passed (164/164).
  - Limitation: Independent security review, staging DAST and performance evidence remain outstanding.

## Completed task
- [x] P8-04 - Playwright end-to-end tests
  - Verification: Chromium browser flow passed (1/1) for recipient registration/mock verification, consented donor search, contact request, donor acceptance and post-acceptance recipient email disclosure. Full suite passed (165 tests, 6 subtests).
  - Files changed: `tests/e2e/test_browser_flows.py`, `docs/06_Plan.md`, `docs/EXECUTION_STATE.md`.
  - Additional local viewport evidence (2026-11-07): Chromium returned HTTP 200 with no horizontal overflow at 320, 375, 768 and 1280 pixels for the home, privacy, safety and guest-search pages. This is a layout smoke check, not a complete accessibility audit or cross-browser test.
  - Limitation: No full accessibility audit, cross-browser test or live verification provider.

## Completed task
- [x] P9-01 - Create Docker/Compose development environment
  - Implementation: Added a Python 3.14.10 image using the hash-pinned runtime lock and Compose services for PostgreSQL, Redis, Django, Celery worker and beat. PostgreSQL data uses a project-specific named volume; published ports bind to localhost. Local mock verification/email behavior is explicit.
  - Verification: `docker compose config --quiet`, `docker compose build`, `docker compose up -d`, container Django check, migration check, pip check and host liveness endpoint passed. All five services started; PostgreSQL/Redis and web health checks passed. Existing Supabase containers were not stopped or modified.
  - Files changed: `Dockerfile`, `.dockerignore`, `compose.yaml`, `README.md`, `docs/06_Plan.md`, `docs/EXECUTION_STATE.md`.
  - Limitation: Default Compose credentials are local-only. This is not staging or production evidence.

## Current checkpoint (2026-11-07)
- P4-03 was not committed at resume. HEAD remains `b2eb593` (`style: clean request flow test spacing`); all preexisting working-tree changes were preserved. P4-03 and P4-04 are already marked verified in the plan; no implementation was replayed.
- Confirmed the guest search route is not login-gated. It queries only discoverable and available profiles and its template/test allowlist excludes direct account/contact details. Focused donor-search and production-settings tests passed (18); full suite passed (167 tests, 6 subtests).
- Prepared a proposed Render Blueprint, startup script, production environment role/TLS handling, deployment instructions and ADR-030. Blueprint YAML/static structure and local Compose configuration checks passed. No Render account/CLI/API token is configured; the Blueprint was not synced or deployed, and no cloud resource or production infrastructure was changed.
- Final staging preparation review (2026-11-07): Render's current Blueprint docs confirm the service fields/references. Clarified that the initial Blueprint create/sync provisions and starts first deploys even though future auto-deploy is off. Added an account setup checklist, every web/worker environment variable and secret source, a five-resource USD estimate, and operational risks in `docs/09_Deployment.md`. No secret values were read, entered or disclosed.
- Cost estimate checked against Render's pricing page: approximately $41.20/month for continuously running proposed service plans plus 15 GB Postgres storage, before usage extras; charges vary and require account-side confirmation. Initial resource sync and first deploy are not authorized. The reviewed work is committed locally but has not been pushed to an authorized connected repository, so Render has no source copy to build.
- Final review risks: public generated web subdomain; use synthetic data only. No reviewed official Bangladesh location snapshot is bundled, so a synthetic location/profile/request fixture set is needed for meaningful search/load smoke paths. Production web requires valid SMTP credentials at startup, but account verification still has no production adapter. Internal Key Value auth is not enabled by the Blueprint (external allowlist is empty; connectivity relies on Render private networking). Small web/worker and 256 MB Postgres plans are a measurement starting point, not capacity evidence. No Render account-side Blueprint validation has run. Final source/config scan found no credential-shaped literals; review included all tracked diff paths and all new application, test, script and deployment files.
- P9-03 is now verified for its local scope: production deployment checks pass with synthetic environment values and `DEBUG=False` is asserted. The Render deployment itself remains unverified under P9-02.
- P9-04 and P9-05 are complete with the new user and synthetic demo/viva guides. P8-06 now has a Render restore rehearsal procedure documented, but no restore was run. The next incomplete plan task remains P8-05, blocked because a verified staging target is unavailable. P8-06 and P8-07 still require hosted evidence.

## Next task
- Task ID: P8-05 (BLOCKED)
- Next required actions before P8-05: project owner supplies/authorizes a Render account/workspace and Git repository connection; authorizes pushing the reviewed local commit; approves the five paid resources and initial Blueprint sync/first deployment (current estimate about $41.20/month plus usage extras); and supplies approved SMTP credentials through Render's protected environment input. Then perform the documented initial health/migration/smoke verification before using Locust.
- Exact next task after staging is operational: run the documented Locust workload against the verified Render staging URL and record workload, environment, latency percentiles and errors.
- Dependencies/blockers: P9-02 is implemented but unverified. No Render account/workspace, connected repository, approved SMTP credentials or explicit paid resource/deployment authorization is available. A Render-provided subdomain is planned, so no custom DNS name is required. P8-06 backup/restore and P8-07 release sign-off remain pending. P9-03's local configuration/checklist scope is verified; its staging claims remain unverified. Production user verification also needs an authorized delivery adapter.

## Resume finding (2026-11-07)
- P4-03 was not committed at resume. HEAD was `b2eb593` (`style: clean request flow test spacing`); P4-03 implementation and subsequent work were present in the working tree. No changes were discarded or reset.
- P4-03 guest search route passed focused donor-search/discovery tests (8 passed at original verification); a later focused rerun passed in the 18-test donor-search/settings run. Search remains consent-gated. Latest full suite passes (167 tests plus 6 subtests), including the Playwright flow.
- The audit app/migration existed after the prior interruption, but P6-02 screens/actions were incomplete. P6-02 and P6-03 are now implemented and verified.

## Verification
- Commands run: Initial repository inventory; `git init`; `git check-ignore` assertions; `winget install/show Python.Python.3.14`; `py -3.14 --version`; package compatibility queries; uv universal lock generation; `uv pip sync`; pip hash dry-run; `pip check`; `pip-audit --strict`.
- Latest final review checks (2026-11-07): full `.venv\Scripts\pytest.exe --ds=config.settings.test tests -q --tb=short -p no:cacheprovider` (167 passed, 6 subtests); `.venv\Scripts\python.exe -m bandit -q -r apps config` (no findings; expected B105 suppression warning for `Bearer`); `.venv\Scripts\pip-audit.exe --strict` (no known vulnerabilities); `.venv\Scripts\python.exe -m pip check` (no broken requirements); `.venv\Scripts\python.exe manage.py makemigrations --check --dry-run --settings=config.settings.test` (no changes); synthetic production `manage.py check --deploy --settings=config.settings.production` (no issues, using a generated long random synthetic secret); Render YAML/static structure/security assertions; `docker compose config --quiet`; credential-pattern scan (no matches); `git diff --check`. Earlier local Compose checks/build/start, container migration/dependency checks and liveness passed; the existing local Compose stack remains active. No Render connection, resource creation or deployment was performed.
- Tests passed: P0-02 ignore assertions; P0-03 environment documentation assertions; P1-01 hash lock dry-run, dependency consistency and vulnerability audit; P1-02 settings tests (2/2) and development Django checks; P1-03 configuration tests (7/7), dev/prod Django checks and Bandit configuration scan; P1-04 full suite (12/12), development Django check, production static collection and Bandit configuration scan; P1-05 full suite (21/21), development Django check and Bandit configuration scan; P1-06 full suite (31/31), test/production Django checks, SQLite and PostgreSQL migrations, PostgreSQL migration inspection, migration consistency check and Bandit scan; P2-01 full suite (46/46), dev/prod Django checks, PostgreSQL migration check, Bandit and diff checks; P2-02 full suite (60/60), PostgreSQL verification migrations/catalog, development check, migration consistency, cleanup command, Bandit and diff checks; P2-03 focused permission tests (6/6), full suite (66/66), development check, PostgreSQL migration check, migration consistency, Bandit and diff checks; P2-04 focused consent/auth tests (19/19), full suite (70/70), PostgreSQL governance migration/catalog checks, development check, migration consistency, Bandit and diff checks; P3-01 location tests (6/6), full suite (76/76), PostgreSQL location migration/catalog checks, development check, migration consistency, Bandit and diff checks; P3-02 donor model tests (6/6), full suite (82/82), PostgreSQL donor migration/catalog checks, development check, migration consistency, Bandit and diff checks; P3-03 donor flow/consent tests (9/9), full suite (87/87), development check, migration consistency, Bandit and diff checks; P3-04 discovery/consent/profile tests (14/14), full suite (92/92), synthetic PostgreSQL eligibility query, development check, PostgreSQL migration check, migration consistency, Bandit and diff checks; P4-03 search/discovery tests (8/8), full suite (110/110); P4-04 donor-search throttle tests (7/7), full suite (112/112), development Django check, PostgreSQL migration check, test-settings migration consistency, Bandit and diff checks.
- Tests failed: None. The first production deployment check used a deliberately short synthetic secret and emitted Django warning W009; it was rerun with a long random synthetic secret and reported no issues. No application defect was found.
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
- Intended GitHub repository URL/access and explicit authorization before pushing. No remote is configured.
- Render account/workspace and repository connection, plus explicit authorization before paid staging resources are created or a deployment is triggered. No domain is required for the planned Render-generated subdomain.
- Approved SMTP provider credentials for the staging web service. Account verification needs a separately implemented and authorized delivery adapter; SMTP configuration alone does not provide it.
- Staging access for Locust/performance, database restore verification, staging security checks and production release sign-off.

## Resume instructions
- Re-read project instructions and this checkpoint.
- Inspect Git status and actual repository state.
- Resume the first incomplete, unblocked task in `docs/06_Plan.md`.
