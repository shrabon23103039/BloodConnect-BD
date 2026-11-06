# Contributing to BloodConnect BD

## Before starting

1. Read `AUTONOMOUS_IMPLEMENTATION.md` and the applicable instructions/specifications.
2. Find the first incomplete task in `docs/06_Plan.md` whose dependencies are verified.
3. Reconcile that task with `docs/EXECUTION_STATE.md` and the actual Git/worktree state.
4. Keep changes within the selected task unless a documented dependency or safety issue requires a plan update.

## Implementation and verification

- Follow the modular Django monolith, PostgreSQL, Django ORM, Django templates/Bootstrap, and versioned DRF API architecture in `docs/04_TRD.md`.
- Add or update tests for acceptance criteria, permissions, state transitions, failure cases, and privacy boundaries. Run the relevant tests and checks available for the task.
- Do not claim a check passed unless it was run; record unavailable tools/services as not run and explain why.
- Review the diff for secrets, personal/health data, accidental files, and private donor-field leakage.
- Update `docs/06_Plan.md` and `docs/EXECUTION_STATE.md` with task status, changed files, commands, actual results, unresolved issues, and the next task.
- Use synthetic data only. Never add real donor/requester data, credentials, OTPs, or tokens to fixtures, screenshots, logs, or examples.

## Product and privacy boundaries

- Blood-group/location filters find potential contacts; they do not determine clinical compatibility or donor eligibility.
- Donor phone/email and precise location remain private until an authorized, explicit donor acceptance permits disclosure of the channels the donor selected.
- Enforce authorization server-side; hiding a control in the UI is not an access check.
- Keep government, hospital, identity, SMS, email, and map integrations behind adapters. Do not enable production integrations without documented authorization and credentials.
- Record an ADR before changing an accepted architecture decision or adding a dependency outside the approved stack.

## Local environment

Follow the staged setup in `README.md`. `.env.example` contains variable names only; put local values in `.env`, which Git ignores. Do not use production secrets or real personal/health data in development.
