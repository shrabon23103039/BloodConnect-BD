# Agent Instructions — BloodConnect BD

This file is a portable instruction entry point for coding agents that support `AGENTS.md`.

1. Read `CLAUDE.md` and `README.md`.
2. Read `docs/01_PRD.md` through `docs/06_Plan.md` before implementation.
3. Read the relevant security, test, API and data-governance documents.
4. Treat the repository documentation as the source of truth.
5. Work only on a task listed in `docs/06_Plan.md`, unless asked to create a documented task first.
6. Respect task dependencies. Do not skip acceptance criteria.
7. After every completed task, update `docs/06_Plan.md` with status, changed files, commands, actual test results and unresolved issues.
8. Do not expose donor contact details before donor acceptance.
9. Do not make medical eligibility, compatibility or transfusion decisions.
10. Do not invent government or institutional API access.
11. Do not claim scale or security properties without evidence.
12. Do not add dependencies or change architecture without documenting an ADR.
13. Never commit secrets or real personal/health data.
14. Run tests and inspect the diff before reporting completion.

For detailed constraints, follow `CLAUDE.md`.
