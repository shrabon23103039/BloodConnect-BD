# BloodConnect BD — Autonomous Implementation Instructions

**Goal:** Give this file to Codex (or another coding agent). It must read the project documents, automatically choose recommended technical options, implement the MVP one task at a time, test each task, and preserve a checkpoint so another session can resume.

> Do not stop after making a plan. Start implementation and continue until the documented MVP is complete, a genuine blocker requires owner input, or the session is interrupted.

## 1. Mandatory reading

Before editing code, inspect the repository, Git status, branch, existing code, and runtime. Then read:

1. `CLAUDE.md`
2. `AGENTS.md`
3. `.cursorrules`
4. `.cursor/rules/project-guardrails.mdc` (if present)
5. `docs/01_PRD.md`
6. `docs/02_AppFlow.md`
7. `docs/03_UI_Spec.md`
8. `docs/04_TRD.md`
9. `docs/05_Schema.md`
10. `docs/06_Plan.md`
11. `docs/07_Security.md`
12. `docs/08_Testing.md`
13. `docs/09_Deployment.md`
14. `docs/10_API_Contract.md`
15. `docs/11_Data_Governance.md`
16. `docs/12_Architecture_ADRs.md`
17. `docs/13_Mobile_Plan.md`
18. `docs/14_Academic_SDLC.md`
19. `docs/15_Release_Checklist.md`
20. `docs/AGENT_BOOTSTRAP_PROMPT.md`
21. `docs/REFERENCES.md`

If a file is missing, record that fact; do not invent its contents. The actual repository is the source of truth for implementation status.

## 2. Autonomous working rules

Act as lead architect, developer, tester, and reviewer for BloodConnect BD.

- Work sequentially through `docs/06_Plan.md`, respecting dependencies.
- Implement real functionality, not placeholder screens described as complete.
- Finish and verify one coherent task before moving to the next.
- Do not repeatedly ask the owner to choose ordinary technical alternatives.
- Do not stop after analysis or scaffolding; continue implementation.
- Keep code maintainable and understandable for a CSE student who must explain it in a viva.
- Document important technical decisions briefly.
- Never claim implementation, testing, security, scalability, integration, or deployment unless actually verified.

## 3. Always choose the recommended option

Whenever alternatives exist, automatically select and implement the best option using this priority:

1. Follow approved requirements and architecture in the project documents.
2. Prefer security, privacy, correctness, and data integrity.
3. Prefer the simplest maintainable solution that satisfies the requirement.
4. Prefer stable, supported, compatible dependencies and established Django practices.
5. Prefer low operational cost and straightforward academic-MVP deployment.
6. Avoid premature complexity; preserve a sensible path for future growth.
7. Record significant decisions and reasons in an ADR or `docs/EXECUTION_STATE.md`.

**Do not present routine alternatives and wait for the owner to decide.** Recommend, briefly explain, and proceed.

Ask the owner only when safe progress genuinely requires missing information or authorization: production credentials/API keys, payments, irreversible production changes, legal or institutional approval, or an unresolvable scope decision. Never fabricate credentials, official approvals, or external integrations. Use clearly labelled mock/test adapters until real authorization exists.

## 4. Product safety and privacy rules

BloodConnect BD is a blood donor discovery and coordination platform—not a blood bank or medical service.

- Never claim medical compatibility, donor eligibility, safety, or guaranteed availability.
- Do not implement diagnosis or medical eligibility decisions.
- Do not collect, test, store, sell, transport, or transfuse blood.
- Donor availability is self-reported willingness to receive contact requests, not medical clearance.
- A recipient sends a request; the donor must explicitly accept before private contact information is disclosed.
- Phone, email, exact address, and precise coordinates are private by default.
- Share only contact channels the donor consented to share, at the permitted workflow stage.
- Implement server-side authorization, rate limits, reporting, blocking, moderation, audit records, and privacy controls.
- Blood-group and location filters are discovery filters, not medical compatibility claims.
- Government, hospital, and blood-bank integrations require official authorization, documented APIs, credentials, and a lawful data-sharing basis. Until then, use mock/test adapters only.
- Never expose secrets, passwords, tokens, or sensitive personal data in logs.
- Do not claim 100,000-user capacity without a defined workload and actual load-test evidence.
- Follow `docs/07_Security.md` and `docs/11_Data_Governance.md`; choose the safer behavior if uncertain.

## 5. Approved technical baseline

Follow the project documents as the definitive specification. The agreed baseline is:

- Python and Django backend.
- Django REST Framework API under `/api/v1/`.
- Django Templates and Bootstrap 5 responsive web UI.
- PostgreSQL database.
- Redis and Celery for required caching/background jobs.
- Nginx and Gunicorn for production serving.
- Docker Compose for local services.
- GitHub Actions for CI.
- pytest/pytest-django, DRF API tests, Playwright, and Locust where appropriate.
- Leaflet for maps.
- Flutter mobile client is future scope; do not make it a dependency for the responsive web MVP.
- Use a modular monolith; do not introduce microservices without a documented need.

Verify dependency compatibility and security before pinning versions. Keep setup reproducible and maintain a lock file or equivalent pinned dependency specification.

## 6. Persistent checkpoint — mandatory

Create and maintain `docs/EXECUTION_STATE.md`. This is the durable handoff record between sessions and accounts. Update it after every completed task, meaningful changes, and before any interruption or stop.

Use this structure:

```markdown
# BloodConnect BD — Execution State

## Current status
- Overall: Not started / In progress / Blocked / MVP complete
- Current phase:
- Current task ID:
- Last updated:
- Git branch:

## Completed tasks
- [x] Task ID — description
  - Implementation:
  - Verification:
  - Commit (if any):

## In-progress task
- [ ] Task ID — description
  - Files changed:
  - Work completed:
  - Remaining work:
  - Risks:

## Next task
- Task ID:
- Exact next action:
- Dependencies:

## Verification
- Commands run:
- Tests passed:
- Tests failed:
- Tests not run and why:

## Decisions
- Decision:
- Reason:
- Related ADR/document:

## Blockers requiring owner input
- None / exact blocker and required input

## Resume instructions
- Re-read project instructions and this checkpoint.
- Inspect Git status and actual repository state.
- Resume the first incomplete, unblocked task in docs/06_Plan.md.
```

Task status rules:

- Mark `[x]` only after implementation and acceptance criteria are verified.
- Keep incomplete work as `[ ]`; explicitly label blocked tasks `BLOCKED`.
- Do not mark generated files or plausible-looking code as verified functionality.
- Keep `docs/06_Plan.md` synchronized with actual progress.
- Preserve completed-task history.
- Use the actual task IDs in `docs/06_Plan.md`.

## 7. Required task execution loop

For every task in `docs/06_Plan.md`:

1. Read the task, dependencies, and acceptance criteria.
2. Inspect relevant existing code and tests.
3. Choose the recommended implementation approach automatically.
4. Implement the task's coherent scope.
5. Add or update tests.
6. Run relevant formatting, lint, static checks, and tests available.
7. Fix failures caused by your changes before proceeding.
8. Review the diff for security, privacy, correctness, secrets, and accidental scope changes.
9. Update `docs/06_Plan.md` and `docs/EXECUTION_STATE.md`.
10. Make a meaningful Git commit if Git is initialized and repository policy permits it. Never discard or rewrite the owner's existing work.
11. Continue to the next unblocked task without waiting for routine approval.

If a test cannot run because a dependency, service, credential, or environment is unavailable, record it as **not run**, explain why, and do not report it as passed.

## 8. Interruption / credit-limit protocol

If credits run out, context is low, the session is ending, or tools become unavailable:

1. Stop starting new tasks.
2. Save safe, coherent changes.
3. Run relevant quick checks if possible.
4. Update `docs/EXECUTION_STATE.md` with the exact current state.
5. Update `docs/06_Plan.md` without marking unfinished tasks complete.
6. Record the exact next action/command, changed files, and any failing test.
7. Leave the repository coherent; do not leave half-written files or unsafe migrations.
8. Provide a concise handoff summary.

Do not claim you can keep working in the background after a session/account stops. A new agent session must be started by the owner. If it has access to the same repository/workspace, it must use the checkpoint and resume—not restart.

## 9. Quality gates before declaring MVP complete

Verify as much as the environment permits.

**Functional:** registration, login, logout, password reset; roles and permissions; donor profiles and availability; blood-group/location discovery; request and accept/reject flow; consent-gated contact disclosure; notifications; reporting/blocking/moderation/audit; admin workflows; responsive UI; API behavior and documentation.

**Security/privacy:** object-level authorization; authentication/session/CSRF protections; input validation; rate limits; secure password handling; no contact disclosure before acceptance and consent; no secrets or sensitive data in logs; safe uploads if applicable; production secrets via environment variables.

**Engineering:** clean migrations; automated tests; browser tests for critical journeys where available; meaningful error handling; Docker setup where supported; valid CI; accurate setup/deployment docs; documentation matching actual code.

**Performance:** add indexes based on query patterns; avoid obvious N+1 queries; load-test only with a documented workload and safe test data. Report measured results honestly. Never infer production capacity from local tests.

## 10. Definition of done

The MVP is complete only when:

1. Every required MVP task in `docs/06_Plan.md` is verified complete or explicitly documented as an accepted limitation.
2. Core donor discovery and request/consent flows work end to end.
3. Automated tests for critical business rules and privacy boundaries pass.
4. Setup and deployment instructions match the code.
5. Security and release checklists have been reviewed.
6. Known critical/high-severity defects are resolved or clearly reported.
7. `docs/EXECUTION_STATE.md` and `docs/06_Plan.md` accurately show final status.
8. The final report separates verified functionality from unverified, mocked, and future-scope features.

Do not call an academic MVP production-ready just because it works locally.

## 11. Resume in a fresh session or with another account

When a new session starts:

1. Read this file.
2. Read the mandatory project documents listed in Section 1.
3. Read `docs/EXECUTION_STATE.md`.
4. Inspect Git status, branch, recent commits, and actual files.
5. Reconcile the checkpoint with the repository; correct stale status.
6. Find the first incomplete, unblocked task in `docs/06_Plan.md`.
7. Resume that task using the execution loop.
8. Do not redo completed work unless verification shows it is broken or incomplete.
9. Do not ask the owner to repeat information already present in project files.

### Owner's resume message

> Read `AUTONOMOUS_IMPLEMENTATION.md`, all required project documents, and `docs/EXECUTION_STATE.md`. Inspect the repository and Git status, then resume the first incomplete task. Automatically choose the recommended option for ordinary technical decisions. Continue implementing and testing one task at a time, updating the checkpoint after every task. Do not stop for routine approval.

## 12. First run

On the first run:

1. Complete mandatory reading and repository inspection.
2. Create `docs/EXECUTION_STATE.md` if it does not exist.
3. Reconcile the plan with the actual repository.
4. Identify the first incomplete task whose dependencies are satisfied.
5. Start implementing it immediately.
6. Continue the task loop until the MVP is complete, interrupted, or genuinely blocked.

**Do not respond with only a proposed plan. Begin implementation in the same run.**

## 13. Communication

Keep updates concise. After each meaningful task, report the task ID, implementation, tests/checks actually run and results, main files changed, and next task. Do not ask for routine technical choices. If blocked, ask one precise question and explain why the answer is necessary.

---

## Final instruction

**Finish the documented BloodConnect BD MVP—not merely generate code quickly. Read first, automatically choose the recommended path, implement one task at a time, verify it, record progress, and continue. Preserve a reliable checkpoint so another session or account can resume from the exact last incomplete task.**
