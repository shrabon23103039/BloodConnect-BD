# 04 — Technical Requirements Document (TRD)

**Version:** 1.0  
**Architecture:** Modular monolith with versioned REST API.

## 1. Locked architecture decisions

| Area | Decision |
|---|---|
| Backend language | Python 3.14.10 (selected runtime patch; update within the 3.14 series after security review) |
| Web framework | Django 5.2 LTS line; proposed pin `5.2.19` |
| API | Django REST Framework proposed pin `3.18.3` |
| Web UI | Django Templates + locally served Bootstrap 5.3.8 (MIT) |
| Database | PostgreSQL 16+ |
| Database driver | psycopg 3.3.8 (binary extra for the local academic environment; production packaging review remains required) |
| Cache/broker | Redis 7.x |
| Background jobs | Celery 5.7.0 |
| API filtering | django-filter 26.2 |
| API schema | drf-spectacular 0.30.0 |
| Web server | Nginx |
| WSGI server | Gunicorn 26.2.0 (see ADR-010; 23.x is no longer security-supported upstream) |
| Static files | Project-local assets collected and served with WhiteNoise 6.12.0 |
| Maps | Leaflet 1.9.4 + OpenStreetMap tiles under provider terms |
| Tests | pytest, pytest-django, Django TestCase, Playwright |
| Load tests | Locust |
| Containers | Docker Compose for local development |
| CI | GitHub Actions |
| Mobile future client | Flutter stable channel; version pinned when mobile phase begins |

### Version pin policy

The Django 5.2 series is selected as an LTS line. The selected baseline pins are Django `5.2.19` and DRF `3.18.3`; official release notes and package metadata were checked on 2026-11-06. Django 5.2 supports Python 3.14 (added in 5.2.8), and DRF 3.18.3 supports Django 5.2. Django 5.2.19 contains fixes for the security issues disclosed in 5.2.18, and DRF 3.18.3 includes the 3.18.2 security fixes. Keep the supported Django line aligned with DRF.

Other dependency versions above are compatibility targets, not a substitute for a resolved lock file. At bootstrap:
1. Verify current stable patch releases and security status.
2. Install compatible direct dependencies recorded in `requirements/base.in` and `requirements/dev.in`.
3. Use the pinned uv lock compiler to generate universal `requirements/base.lock` and `requirements/dev.lock` files (including transitive dependencies and hashes for supported target platforms).
4. Commit the lock file.
5. Record the exact resolved versions and verification evidence in `requirements/LOCK_REPORT.md`.
6. Do not float production dependencies.

Lock generation uses uv `0.13.7` with `uv pip compile --universal --generate-hashes --python-version 3.14`; pip-tools is not used because its hash resolver downloaded every platform artifact serially and timed out while resolving psycopg-binary.

Do not use Django development server in production.

## 2. Runtime and package layout

```text
bloodconnect-bd/
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── development.py
│   │   ├── test.py
│   │   └── production.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
├── apps/
│   ├── accounts/
│   ├── donors/
│   ├── requests/
│   ├── matching/
│   ├── connections/
│   ├── notifications/
│   ├── organizations/
│   ├── locations/
│   ├── moderation/
│   ├── analytics/
│   ├── audit/
│   └── integrations/
├── templates/
├── static/
├── media/                 # local development only; production private storage
├── tests/
├── docs/
├── requirements/
├── scripts/
├── Dockerfile
├── compose.yaml
├── manage.py
├── pyproject.toml
└── .env.example
```

Each Django app should own its models, migrations, selectors/query helpers, services, forms/serializers, views and tests as appropriate. Avoid circular imports and cross-app model logic.

## 3. Application boundaries

- `accounts`: custom user, authentication, account status, role membership.
- `donors`: donor profile, visibility and availability.
- `requests`: blood request lifecycle.
- `matching`: discovery filters only; no medical compatibility logic.
- `connections`: contact request state machine and accepted connection.
- `notifications`: in-app and external delivery.
- `locations`: administrative geography.
- `moderation`: reports, blocks and moderation cases.
- `organizations`: optional verified organization records.
- `audit`: security-relevant event records.
- `integrations`: adapters for OTP, SMS, email, map and future authorized APIs.
- `analytics`: aggregated metrics with privacy controls.

## 4. Authentication

### Web
- Django session authentication.
- Secure, HttpOnly, SameSite cookies.
- CSRF middleware enabled.
- Session rotation on login and privilege changes.
- Password reset through a verified channel.

### API/mobile
- DRF authentication with short-lived access token and rotating refresh token, using a maintained JWT package after compatibility review.
- Refresh token rotation and blacklist/revocation.
- Never store long-lived secrets in browser local storage.
- Mobile secure storage (Keychain/Android Keystore) in future Flutter app.
- API rate limits on login, OTP, refresh and sensitive endpoints.

Do not mix session and JWT policies accidentally. Document which endpoints accept which authentication method.

## 5. Authorization

- Role-based permissions plus object-level ownership checks.
- Default deny for private endpoints.
- A user may read/update only their own private profile and requests unless an explicit permission allows otherwise.
- A donor can act only on contact requests addressed to that donor.
- A recipient can cancel only their own pending contact request.
- Admin/moderator access is least-privilege and audited.
- Never trust a role or owner ID sent by the client.

## 6. Data access and RLS

MVP uses Django ORM and server-side authorization as the primary access boundary. Browser and mobile clients never connect directly to PostgreSQL.

PostgreSQL Row-Level Security (RLS) is **not enabled in MVP** because connection pooling, transaction-local identity context and migration behavior must be designed and tested carefully. If RLS is introduced later:
- Use a non-owner application database role.
- Set user context transaction-locally, not as persistent session state.
- Ensure context is reset safely under connection pooling.
- Test every policy, background job and admin workflow.
- Keep Django authorization even with RLS; RLS is defense in depth, not a replacement.

## 7. API conventions

- Prefix: `/api/v1/`.
- JSON request/response.
- ISO 8601 timestamps in UTC; render in Asia/Dhaka for users.
- UUID public identifiers.
- Pagination on list endpoints.
- Consistent error envelope.
- Explicit serializer allowlists; never serialize models wholesale.
- Idempotency for state-changing operations that may be retried.
- OpenAPI schema generated and reviewed.
- No private fields in public search endpoints.

## 8. Background processing

Celery tasks:
- Send notification after database transaction commits.
- Retry transient provider failures with bounded exponential backoff.
- Use idempotency keys to avoid duplicate sends.
- Store delivery state and provider reference without storing secrets.
- Expire pending contact requests and stale requests via scheduled jobs.
- Reconcile failed notifications.

A task failure must not roll back a successful contact-request database transaction. Use an outbox or durable notification record to avoid lost notifications.

## 9. External APIs and adapters

Potential adapters:
- Email provider.
- SMS/OTP provider.
- Map tile provider.
- Future authorized hospital/blood-bank directory.
- Future authorized DGHS FHIR endpoint.
- Future authorized identity verification.

All adapters require:
- Environment-based credentials.
- Connect/read timeouts.
- Retry policy only for safe/idempotent calls.
- Circuit-breaker or failure isolation where appropriate.
- Structured logs with sensitive fields redacted.
- Provider sandbox/mock for development.
- Documentation of authorization and data-sharing basis.

## 10. Security constraints

See `07_Security.md`. At minimum:
- HTTPS in production.
- `DEBUG=False`.
- Strong `SECRET_KEY`.
- Allowed hosts and trusted origins configured.
- CSRF protection.
- Secure cookies and HSTS.
- ORM/parameterized queries.
- Template escaping.
- File upload allowlist, size limits and private storage.
- Rate limiting.
- Dependency scanning.
- Backup encryption and access control.
- No secrets in Git.

## 11. Scalability strategy

Initial architecture:
- Stateless Django web/API instances.
- PostgreSQL primary database.
- Redis cache and Celery broker.
- Object storage for uploaded documents.
- Nginx/load balancer.
- Horizontal application scaling when measured load requires it.

Optimization order:
1. Correct indexes and query plans.
2. Pagination and bounded result sets.
3. Eliminate N+1 queries.
4. Cache safe public/reference data.
5. Move slow work to Celery.
6. Add application replicas.
7. Tune database connections and connection pooling.
8. Add read replicas only when justified by measurements.

"100,000 registered users" is not a capacity benchmark. Define concurrent users, request mix, throughput, latency, error rate and test duration before making performance claims.

## 12. Observability

- Structured application logs.
- Request correlation ID.
- Error monitoring with PII scrubbing.
- Metrics: request count, latency, status codes, queue depth, task failures, DB pool saturation.
- Health endpoints: liveness and readiness.
- Audit events for privileged and sensitive operations.
- Alerts for error spikes, queue backlog, failed backups and resource saturation.

## 13. Non-functional technical constraints

- Maintainable modular code.
- Deterministic migrations.
- Repeatable local environment.
- Test suite runs in CI.
- No production secrets in environment files committed to Git.
- Graceful failure when external providers are unavailable.
- Data export/deletion workflows subject to legal retention obligations.
