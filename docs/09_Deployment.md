# 09 — Deployment and Operations Guide

## 1. Environments

- Development: local developer machine, synthetic data.
- Test/CI: ephemeral environment, isolated database.
- Staging: production-like configuration, synthetic or anonymized data.
- Production: real users only after release gates and legal/privacy review.

## 2. Production topology

```text
Web / Mobile clients
        |
      HTTPS
        |
 Nginx / Load Balancer
        |
 Django + Gunicorn replicas
        |
   +----+------------------+
   |                       |
PostgreSQL              Redis
   |                       |
Backups                Celery workers
                           |
                   Email/SMS adapters

Private object storage for approved uploads
Monitoring / logs / alerting across services
```

## 3. Environment variables

Maintain `.env.example` with names only, never real values:
- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG`
- `DJANGO_ALLOWED_HOSTS`
- `DJANGO_CSRF_TRUSTED_ORIGINS`
- `DATABASE_URL`
- `REDIS_URL`
- `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`
- `SMS_PROVIDER`, `SMS_API_KEY`
- `ALLOWED_UPLOAD_TYPES`
- `SENTRY_DSN` or equivalent
- `STORAGE_BUCKET`, `STORAGE_ACCESS_KEY`, `STORAGE_SECRET_KEY`

Production secrets must be stored in a secret manager or protected deployment environment.

## 4. Deployment sequence

1. Provision PostgreSQL, Redis and private object storage.
2. Provision app and worker runtime.
3. Configure DNS and TLS.
4. Set production environment variables.
5. Build immutable application image.
6. Run `python manage.py check --deploy`.
7. Run migrations in a controlled release step.
8. Collect static files.
9. Start Gunicorn web processes and Celery workers.
10. Verify liveness/readiness endpoints.
11. Run smoke tests.
12. Verify logs, metrics and alerting.
13. Verify backup schedule and restore procedure.
14. Record release version and rollback plan.

## 5. Django production requirements

- `DEBUG=False`.
- Strong unique `SECRET_KEY`.
- Explicit `ALLOWED_HOSTS`.
- HTTPS redirect.
- Secure session and CSRF cookies.
- HSTS after HTTPS is verified.
- Correct trusted origins.
- Database credentials with least privilege.
- No public media bucket for private documents.
- Run Django deployment checks.
- Do not use `runserver` in production.

## 6. Database backups and recovery

- Automated encrypted backups.
- Define RPO and RTO before launch.
- Restrict backup access.
- Test restoration periodically.
- Do not assume a successful backup job means a valid restore.
- Document retention and deletion behavior across backups.

## 7. Scaling path

1. Optimize indexes and queries.
2. Add pagination and request limits.
3. Add Redis caching for safe public/reference data.
4. Add Celery workers for slow tasks.
5. Add stateless Django replicas behind load balancer.
6. Tune PostgreSQL connections and storage.
7. Add read replicas only if measurements justify them.
8. Consider service extraction only after clear operational need.

## 8. Rollback

- Keep prior immutable image.
- Back up before risky migrations.
- Prefer backward-compatible expand/contract migrations.
- Document migration reversibility.
- Roll back application code without destructive data rollback where possible.
- Validate health and core user journeys after rollback.
