# BloodConnect BD — Context Architecture Pack

**Product:** BloodConnect BD  
**Document set:** Context Architecture v1.0  
**Prepared:** 2026-11-06  
**Formal academic schedule:** 16 weeks  
**Initial MVP target:** 7 calendar days (aspirational; release only after acceptance gates pass)

## What this repository contains

This package is the source of truth for product scope, user journeys, visual design, technical decisions, data model, implementation order, security, testing, deployment, API contracts, data governance, mobile roadmap and academic SDLC documentation.

### Required six-document architecture

1. [`docs/01_PRD.md`](docs/01_PRD.md) — Product Requirements Document.
2. [`docs/02_AppFlow.md`](docs/02_AppFlow.md) — Screen-by-screen navigation and state flows.
3. [`docs/03_UI_Spec.md`](docs/03_UI_Spec.md) — Design system and UI behavior.
4. [`docs/04_TRD.md`](docs/04_TRD.md) — Technical Requirements Document.
5. [`docs/05_Schema.md`](docs/05_Schema.md) — Relational schema and authorization model.
6. [`docs/06_Plan.md`](docs/06_Plan.md) — Dependency-ordered implementation checklist.

### Additional engineering documents

- [`docs/07_Security.md`](docs/07_Security.md)
- [`docs/08_Testing.md`](docs/08_Testing.md)
- [`docs/09_Deployment.md`](docs/09_Deployment.md)
- [`docs/10_API_Contract.md`](docs/10_API_Contract.md)
- [`docs/11_Data_Governance.md`](docs/11_Data_Governance.md)
- [`docs/12_Architecture_ADRs.md`](docs/12_Architecture_ADRs.md)
- [`docs/13_Mobile_Plan.md`](docs/13_Mobile_Plan.md)
- [`docs/14_Academic_SDLC.md`](docs/14_Academic_SDLC.md)
- [`docs/15_Release_Checklist.md`](docs/15_Release_Checklist.md)
- [`docs/REFERENCES.md`](docs/REFERENCES.md)

Agent instructions:
- [`CLAUDE.md`](CLAUDE.md)
- [`AGENTS.md`](AGENTS.md)
- [`.cursorrules`](.cursorrules)
- [`.cursor/rules/project-guardrails.mdc`](.cursor/rules/project-guardrails.mdc)

## Product decision in one sentence

BloodConnect BD is a **P2P-first, institution-ready donor discovery and coordination platform**: recipients discover potential donors and send contact requests; donors control whether to accept; optional organizations may participate later. The platform does not collect, test, store, sell, transport or transfuse blood and does not determine medical eligibility.

## How to use this pack

1. Read `CLAUDE.md` / `AGENTS.md` first.
2. Read all six core documents before implementation.
3. Review the supporting security, testing, data-governance and deployment documents.
4. Resolve any open decision before coding; record changes in `12_Architecture_ADRs.md`.
5. Work through `06_Plan.md` in order.
6. After every completed task, update its status, evidence and test results in `06_Plan.md`.
7. Do not mark a task complete based only on generated code. Run the relevant checks and inspect the result.

## Status vocabulary

- `NOT_STARTED`
- `IN_PROGRESS`
- `BLOCKED`
- `IMPLEMENTED_UNVERIFIED`
- `VERIFIED`
- `DEFERRED`

`VERIFIED` requires reproducible evidence. A generated screen or a successful build alone does not verify the full feature.

## Important scope and safety constraints

- MVP is a coordination tool, not a medical service or blood bank.
- Blood-group filtering is a discovery filter, not a transfusion-compatibility decision.
- A qualified healthcare professional and authorized facility must assess donor eligibility, compatibility and transfusion safety.
- Donor phone numbers and precise locations are private by default.
- No NID, DGHS, hospital, blood-bank or government API integration is assumed to be available. Use mock adapters until written authorization and credentials exist.
- Do not claim national deployment, 100,000-user capacity, government partnership, legal compliance or clinical validation without evidence.
- The 16-week schedule is the formal planning baseline. The 7-day MVP target is an internal acceleration target, not a claim about the actual duration of work.

## Version policy

The dependency versions in `04_TRD.md` are the proposed baseline. Before installing, verify current security advisories and package compatibility, then commit a complete resolved lock file. Never silently upgrade major versions.

## Development setup

### Current repository state

The repository contains the Django project, separated settings, hash-pinned dependencies, PostgreSQL configuration, public information pages, a custom account model, and verified web registration/session authentication, email/phone verification, password-reset, role/ownership permissions, versioned consent/privacy settings, and a location hierarchy/import process. New accounts remain pending until their identifier is verified. Local verification uses an in-memory mock and sends no real email or SMS; production verification remains disabled until an authorized provider is implemented. No official location snapshot is bundled pending source reconciliation and review. Donor profiles and discovery, blood/contact requests, moderation, API workflows, Docker Compose services and release deployment remain incomplete; consult `docs/06_Plan.md` and `docs/EXECUTION_STATE.md` for verified progress. Public privacy and terms pages are drafts. Do not treat the current implementation as a completed application.

### Prerequisites

- Git.
- Python 3.14.10, per `docs/04_TRD.md` and `.python-version`.
- Docker Desktop or Docker Engine with the Compose plugin for local PostgreSQL/Redis services (Compose setup is P9-01).

### Bootstrap commands

From the repository root, create and activate a virtual environment:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

On macOS/Linux, use:

```sh
python3.14 -m venv .venv
source .venv/bin/activate
```

Copy `.env.example` to `.env` and set local values without committing `.env`:

```powershell
Copy-Item .env.example .env
```

```sh
cp .env.example .env
```

The Django settings read environment variables from the process; they do not parse `.env` directly. Compose will load `.env` for local services after P9-01. For direct local commands, load the required values from `.env` into your shell process first. Development and production require PostgreSQL; only automated tests use an in-memory SQLite database. Development password-reset email is held by Django's in-memory email backend; no message is sent externally or printed to terminal logs.

Install the reviewed, hash-pinned development set with:

```sh
python -m pip install --require-hashes -r requirements/dev.lock
```

Production images should install only the runtime set with `python -m pip install --require-hashes -r requirements/base.lock`.

After P9-01 adds the Compose file, start local PostgreSQL and Redis with:

```sh
docker compose up -d db redis
```

For current scaffold checks, run:

```sh
python manage.py check
pytest --ds=config.settings.test
```

After P1-06 creates the custom user model and initial migration, apply migrations and run the development server:

```sh
python manage.py migrate
python manage.py runserver
```

Run the test suite with `python -m pytest` after the project test dependencies are installed. Use synthetic data only. See `docs/08_Testing.md` for required coverage and evidence; see `docs/09_Deployment.md` for production configuration, which is not equivalent to the local development server.

### Environment variables

`.env.example` lists variable names only. Configure local values in the ignored `.env` file. Do not commit secrets, real provider credentials, production URLs, or personal/health data. The authoritative descriptions and production handling requirements are in `docs/09_Deployment.md`.

## Contribution workflow

Read `AUTONOMOUS_IMPLEMENTATION.md`, `CLAUDE.md`, `AGENTS.md`, and the relevant product/engineering documents before changing code. Use `docs/06_Plan.md` as the dependency-ordered task queue and `docs/EXECUTION_STATE.md` as the handoff checkpoint. Complete one task at a time, add tests for behavior and permission boundaries, run the documented checks, inspect the diff, and record actual results before marking a task verified. See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the project workflow and safety review.
