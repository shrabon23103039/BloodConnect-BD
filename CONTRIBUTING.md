# Contributing to BloodConnect BD

Thanks for helping improve the project. BloodConnect BD handles sensitive donor and request workflows, so contributions must preserve privacy, consent, and the project's medical-safety boundaries.

## Before you start

1. Read `AGENTS.md`, `CLAUDE.md`, `README.md`, and the relevant specifications under `docs/`.
2. Check `docs/06_Plan.md` and `docs/EXECUTION_STATE.md`; work on a planned task or add a scoped task before implementation.
3. Check the current branch and complete Git status. Do not discard or rewrite existing work.
4. Keep unrelated changes out of your pull request.

## Development setup

Use Python 3.14.10 and install the hash-pinned development dependencies:

```sh
python -m venv .venv
# Activate the environment using your platform's command.
python -m pip install --require-hashes -r requirements/dev.lock
```

Copy `.env.example` to `.env` for local Compose settings. Set a unique development `DJANGO_SECRET_KEY` and `POSTGRES_PASSWORD`; never add `.env`, database files, credentials, real donor data, or provider tokens to a change.

Run the isolated application suite and useful checks:

```sh
python -m pytest --ds=config.settings.test tests -q --tb=short -p no:cacheprovider
python manage.py check --settings=config.settings.test
python -m pip check
python -m bandit -q -r apps config
docker compose config --quiet
```

The test profile uses synthetic records and an isolated SQLite database. Do not use the local Compose database for tests or screenshots.

## Change requirements

- Follow the modular Django monolith and existing dependencies; document architecture changes in an ADR before implementation.
- Enforce permissions in views/services/API layers, not only in templates.
- Keep donor phone/email and precise location private until donor acceptance and channel-specific consent.
- Do not implement or imply clinical eligibility, compatibility, blood inventory, or donation guarantees.
- Keep government, hospital, SMS, email, identity, and map integrations disabled/mock until authorization is documented.
- Use synthetic-only fixtures, screenshots, logs, and examples.
- Add or update focused tests when behavior changes. Record exact checks and actual results.
- Update `docs/06_Plan.md` and `docs/EXECUTION_STATE.md` for completed project tasks.
- Keep setup, limitations, and security claims aligned with what was actually verified.

## Pull requests

Open an issue first for substantial scope changes. Pull requests should explain the behavior change, link a task or issue, list tests/checks run, and call out privacy/security implications. Include screenshots only when they come from implemented screens with synthetic data. Do not claim CI, deployment, performance, or production readiness until the evidence exists.

The default development branch is `master`. Use normal commits and fast-forward updates; never force-push or rewrite shared history.
