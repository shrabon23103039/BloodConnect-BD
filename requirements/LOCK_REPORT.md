# Dependency lock report

## Baseline

- Review date: 2026-11-06
- Python runtime target: 3.14.10 (`.python-version`)
- Django line: 5.2 LTS
- Lock method: uv `0.13.7`, universal resolution with complete hashes
- Runtime direct inputs: `requirements/base.in`
- Development/test direct inputs: `requirements/dev.in`
- Generated locks: `requirements/base.lock`, `requirements/dev.lock`

## Compatibility and security review

- Python 3.13.18 is source-only and 3.13.17 was the last 3.13 Windows binary installer. Python 3.14.10 has a Windows installer; Django 5.2 supports Python 3.14 starting in 5.2.8. See ADR-011.
- Django 5.2.19 is the latest 5.2 patch listed during review and fixes the security issues disclosed in 5.2.18.
- DRF 3.18.3 is available and supports Django 5.2; 3.18.2 includes security fixes and 3.18.3 follows it.
- Gunicorn 23.0.0 is marked unsupported by upstream. Gunicorn 26.2.0 is the latest version available from the configured Python package index at review time and is in the upstream supported 26.x line. See ADR-010.
- Other direct package versions were checked for Python/Django compatibility and package availability on the review date. Full resolution and audit results are recorded below after generation.

## Commands and results

Lock generation commands (uv 0.13.7):

```powershell
uv pip compile --universal --generate-hashes --python-version 3.14 --output-file requirements/base.lock requirements/base.in
uv pip compile --universal --generate-hashes --python-version 3.14 --output-file requirements/dev.lock requirements/dev.in
```

Results: base lock resolved 36 packages; dev lock resolved 101 packages. The initial pip-tools attempt timed out while downloading/hashing platform wheels; uv resolved metadata for all target platforms without downloading those artifacts.

## Resolved packages

Runtime lock (`base.lock`): 36 fully pinned distributions, including platform-specific Gunicorn marker for non-Windows targets. Development lock (`dev.lock`): 101 fully pinned distributions, including test, browser, load-test and audit tools. Both locks include artifact SHA-256 hashes.

## Known limitations

- Resolver target is universal across platform markers at Python 3.14, generated on Windows. The lock uses hashes for published distributions and a platform marker for POSIX-only Gunicorn. Verify installation in CI/target containers before release.
- PostgreSQL, Redis, browser binaries, and external email/SMS providers are not part of Python package locking. Their versions and runtime checks are handled by later plan tasks.

## Verification (2026-11-06)

- `uv pip sync --python .venv/Scripts/python.exe requirements/dev.lock` — passed; installed 101 locked dev distributions (Windows omitted Gunicorn by marker).
- `python -m pip install --dry-run --require-hashes -r requirements/dev.lock` — passed; pip accepted hashes and markers.
- `python -m pip check` — passed: no broken requirements.
- `pip-audit --strict` — passed: no known vulnerabilities found.
- `uv pip compile` emitted compatibility normalization warnings for invalid trailing commas/starred comparisons in third-party package metadata; resolved constraints were normalized by uv. No project constraints were altered.

## Follow-up verification (2026-11-24)

- Added the ADR-032-selected `django-allauth[socialaccount]==65.22.1` runtime dependency to `requirements/base.in`.
- Regenerated both universal hash locks with uv `0.13.7`: `base.lock` resolves 47 packages and `dev.lock` resolves 106 packages.
- A Python 3.14.10 environment installed `requirements/dev.lock` with `pip install --require-hashes`; `pip check` passed with no broken requirements.
- The GitHub advisory database reported no known vulnerabilities for `django-allauth` 65.22.1.
- The Django system check was attempted after installation but is blocked by an existing `ImportError` for `VerificationDeliveryError` in `apps/accounts/views.py`; this is not a dependency resolution failure.
