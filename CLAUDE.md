# BloodConnect BD — Claude Code Project Instructions

You are working on BloodConnect BD, a privacy-first, P2P donor discovery and coordination platform. These instructions are mandatory.

## Required reading before every task

Before editing code or proposing implementation changes:

1. Read `README.md`.
2. Read all six core documents:
   - `docs/01_PRD.md`
   - `docs/02_AppFlow.md`
   - `docs/03_UI_Spec.md`
   - `docs/04_TRD.md`
   - `docs/05_Schema.md`
   - `docs/06_Plan.md`
3. Read the relevant supporting documents:
   - `docs/07_Security.md`
   - `docs/08_Testing.md`
   - `docs/10_API_Contract.md`
   - `docs/11_Data_Governance.md`
   - `docs/12_Architecture_ADRs.md`
4. If deployment, external services or mobile work is involved, also read `docs/09_Deployment.md` and/or `docs/13_Mobile_Plan.md`.

Do not assume a previous conversation is reliable project context. The repository documents are the source of truth.

## Operating procedure

For each task:

1. Identify the task ID in `docs/06_Plan.md`.
2. Confirm its dependencies are `VERIFIED`.
3. State a short implementation plan and files expected to change.
4. Inspect existing code before editing. Preserve working behavior.
5. Implement the smallest coherent change.
6. Add or update tests.
7. Run relevant tests, lint/type checks and security checks available in the repository.
8. Inspect the diff for secrets, unrelated changes, unsafe permissions and generated junk.
9. Update `docs/06_Plan.md` after every completed step:
   - status;
   - changed files;
   - commands run;
   - actual results;
   - unresolved issues;
   - date.
10. Mark a task `VERIFIED` only when its acceptance criteria pass with evidence. Otherwise use `IMPLEMENTED_UNVERIFIED` or `BLOCKED`.

## Non-negotiable product rules

- The product coordinates people; it is not a blood bank, clinical decision-support system or transfusion service.
- Never state or infer that a donor is medically eligible, safe, compatible or guaranteed to donate.
- Blood-group and location filters identify potential contacts only. Do not implement medical compatibility rules.
- Do not collect, test, store, sell, transport or transfuse blood.
- Donor phone number, email, exact address and precise coordinates are private by default.
- A recipient must send a contact request. The donor must explicitly accept before approved contact channels are revealed.
- Do not expose private fields in public serializers, search results, logs, analytics or error messages.
- Do not create fake government/hospital integrations. External integrations must be adapter-based and disabled until authorized.
- Do not claim 100,000-user capacity without load-test evidence and documented infrastructure.
- Never place real personal, health or identity data in fixtures, screenshots, logs or tests.

## Architecture rules

- Use a modular Django monolith for the initial release.
- PostgreSQL is the system of record.
- Django ORM is the only application data-access path. No browser/mobile client connects directly to PostgreSQL.
- Use Django templates + Bootstrap for the web MVP.
- Use Django REST Framework under `/api/v1/` for future/mobile/API clients.
- Use Django session authentication for the server-rendered web app. Use a documented token strategy for mobile/API clients.
- Keep domain logic in focused services/use cases; keep views/controllers thin.
- Avoid premature microservices, event streaming, Kubernetes and complex distributed patterns.
- External services must be behind adapters with timeouts, retries where safe, idempotency and observability.
- Database migrations are mandatory for schema changes. Never edit an applied migration.
- Use UUIDs for public resource identifiers where specified in `05_Schema.md`.

## Security rules

- Never hardcode secrets, API keys, credentials or private URLs.
- Read secrets from environment variables or a secret manager.
- Enforce authorization on the server for every private resource and action.
- Use CSRF protection for cookie-authenticated web requests.
- Validate uploaded file type, size and content; do not trust filenames or browser MIME types.
- Apply rate limits to authentication, OTP, search, request creation and contact-request endpoints.
- Use secure cookies, HTTPS, HSTS and production Django settings in production.
- Do not log passwords, tokens, OTPs, full phone numbers, private messages or identity documents.
- Treat all external API responses and user-generated content as untrusted input.

## Code quality rules

- Follow PEP 8 and Django conventions.
- Add type hints to non-trivial service functions.
- Prefer explicit names and small functions.
- Avoid duplicated business rules.
- Add tests for permissions, state transitions and failure cases.
- Do not add a dependency when the standard library or existing stack is sufficient.
- Keep dependencies pinned in the project lock/requirements files.
- Do not silently change the approved stack or schema.

## Change control

If a task conflicts with the documents:
1. Stop before making the conflicting change.
2. Explain the conflict and propose options.
3. Record the accepted decision in `docs/12_Architecture_ADRs.md`.
4. Update affected documents and `docs/06_Plan.md`.
5. Only then implement.

## Definition of done

A task is done only when:
- its acceptance criteria are met;
- tests pass and their output is recorded;
- authorization and privacy behavior are reviewed;
- migrations are clean, if applicable;
- no secrets or unrelated changes are present;
- documentation and `06_Plan.md` are updated.

Never claim a test, deployment, integration, audit or performance result that was not actually performed.
