# 09 — Deployment and Operations Guide

## 1. Environments

### Google OAuth provider setup

Set `GOOGLE_OAUTH_CLIENT_ID` and `GOOGLE_OAUTH_CLIENT_SECRET` in the protected web-service environment only. Configure an OAuth client with the deployed origin and exact redirect URI `https://<verified-deployment-host>/accounts/google/login/callback/`; the callback derived from this local browser URL is `http://127.0.0.1:8000/accounts/google/login/callback/`. Add `http://localhost:8000/accounts/google/login/callback/` only if the app is accessed through `localhost`. Google returned `redirect_uri_mismatch` during the local flow, so the active OAuth client still needs its exact authorized redirect URI updated in Google Cloud. Request only `openid`, `email` and `profile`, and complete the provider consent-screen setup before enabling use. No production hostname is asserted; never put credentials in source, browser code, logs or docs.

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
- `DATABASE_SSLMODE`
- `REDIS_URL`
- `BLOODCONNECT_PROCESS_ROLE`
- `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USE_TLS`, `EMAIL_USE_SSL`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`
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
10. Start one Celery beat process for configured periodic tasks.
11. Verify liveness/readiness endpoints, including PostgreSQL and Redis separately.
12. Run smoke tests.
13. Verify logs, metrics and alerting.
14. Verify backup schedule and restore procedure.
15. Record release version and rollback plan.

### Runtime image data boundary

The Dockerfile's `COPY . /app` includes the build context after `.dockerignore` filtering. `/data/locations/` is excluded from that context, so the unreconciled candidate snapshot and its accompanying attribution/license files are not present in the runtime image. The attribution and CC BY 4.0 license files remain in the repository. No application runtime code requires these source files; `load_locations` accepts an operator-supplied `--file` and must only be used after source review and explicit authorization. Do not treat the candidate as approved or activate it because it exists in the repository.

The application uses the `REDIS_URL` Redis URL with logical database 0 for Django's shared cache and database 1 for the Celery broker. Use `redis://` only for trusted local networks; production settings require `rediss://` so cache and broker traffic use TLS. Local development and isolated tests may continue to use `redis://` where configured. Do not expose broker URLs or credentials in logs. Run the worker with `celery -A config worker` and a single beat scheduler with `celery -A config beat`; Windows development may use `--pool=solo`. Notification rows remain durable and visible in PostgreSQL if enqueueing is temporarily unavailable; Celery beat redrives pending rows in bounded batches.

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
- The revised location-search design requires a PostgreSQL service with PostGIS support. Before implementation, confirm the selected runtime supports the required PostGIS extension/version and review its backup/restore behavior. No extension setup or location migration is authorized by this documentation change.
- Before accepting requester or donor coordinates, review and approve the Bangladesh boundary dataset's source, license, version, provenance and import/use approval. Do not deploy or activate an unreviewed boundary.

## 6. Database backups and recovery

- Automated encrypted backups.
- Define RPO and RTO before launch.
- Restrict backup access.
- Test restoration periodically.
- Do not assume a successful backup job means a valid restore.
- Document retention and deletion behavior across backups.

### Local PostgreSQL restore rehearsal (2026-11-21)

Verified a PostgreSQL custom-format dump/restore using a disposable PostgreSQL `17.11-alpine` container on the local Compose network, with its data directory mounted as `tmpfs` (512 MiB), no published port and synthetic-only rows. The existing Compose database was not used as a dump source or restore target. The temporary container was named `bcbd-pg-restore-aba8f0cb2f`; its one-time synthetic database password is intentionally omitted from this record.

Commands and results:

1. Started the isolated instance with `docker run --rm -d --name bcbd-pg-restore-aba8f0cb2f --network bloodconnect-bd_default --network-alias bcbd-pg-restore-aba8f0cb2f --mount type=tmpfs,dst=/var/lib/postgresql/data,tmpfs-size=536870912 -e POSTGRES_USER=synthetic -e POSTGRES_PASSWORD=<one-time-synthetic-value> -e POSTGRES_DB=synthetic_source postgres:17.11-alpine`. `docker inspect` confirmed the only mount was `tmpfs` at `/var/lib/postgresql/data`; `SHOW server_version` returned `17.11`.
2. Applied the project schema using `docker compose exec -T -e DATABASE_URL=postgresql://synthetic:<one-time-synthetic-value>@bcbd-pg-restore-aba8f0cb2f:5432/synthetic_source web python manage.py migrate --noinput --settings=config.settings.development`. All migrations completed; `django_migrations` contained 34 rows. Created a synthetic `rehearsal_probe` table with two marker rows.
3. Created and checked the archive: `docker exec bcbd-pg-restore-aba8f0cb2f pg_dump --format=custom --file=/tmp/bcbd-rehearsal.dump --dbname=synthetic_source --username=synthetic`. The file was non-empty at 91,866 bytes; `pg_restore --list /tmp/bcbd-rehearsal.dump` succeeded and listed the synthetic table and data plus Django migration table/data.
4. Restored to a newly created database in the same disposable instance: `docker exec bcbd-pg-restore-aba8f0cb2f createdb --username=synthetic synthetic_restored`, then `docker exec bcbd-pg-restore-aba8f0cb2f pg_restore --exit-on-error --no-owner --username=synthetic --dbname=synthetic_restored /tmp/bcbd-rehearsal.dump`. Restore exited successfully. SQL verification found 34 migration rows and exactly `1:synthetic-backup-row,2:synthetic-second-row` in the restored probe table.
5. `docker compose exec -T -e DATABASE_URL=postgresql://synthetic:<one-time-synthetic-value>@bcbd-pg-restore-aba8f0cb2f:5432/synthetic_restored web python manage.py check --settings=config.settings.development` passed with no issues. A Django shell query against that same target read 34 applied migrations and two probe rows. Backup, restore, and application-query checks took 13.57 seconds after schema setup.
6. The container was stopped and auto-removed; its tmpfs and archive disappeared with it. Post-cleanup inspection confirmed the original `bloodconnect-bd-db-1` container ID and `bloodconnect-bd_postgres_data` named-volume mount remained unchanged. The application database still had 567 location rows (0 active; 8/64/495).

This verifies a local synthetic PostgreSQL logical backup/restore path for PostgreSQL 17.11 and the current Django schema. It does not verify production backup encryption, scheduling, retention, RPO/RTO, provider-managed snapshots/PITR, or restore into a hosted database. Those remain separate release gates.

### Proposed backup operations baseline — approval required

The following is an operational recommendation, not an organizational requirement or configured service. The owner, privacy/legal reviewer and infrastructure operator must approve the RPO/RTO, retention, storage region, cost and handling of sensitive personal data before implementation.

| Control | Proposed starting point | Approval / implementation needed |
|---|---|---|
| Backup frequency | Daily encrypted full logical backup; enable continuous WAL/PITR only if the selected managed PostgreSQL service supports it and the owner approves the cost. | Infrastructure owner selects the provider and recovery method. |
| Retention | Backups containing precise donor coordinates must be purged no later than 30 days after account deletion or consent revocation; configure backup lifecycle so no retained copy exceeds that proposed deadline. | Owner/privacy reviewer approves the final maximum purge window and deletion behavior, including provider-side copies. |
| Encryption and storage | Provider-managed encryption at rest using a controlled KMS key; TLS in transit; store a second encrypted copy in a separate account or region with access logging. Do not keep persistent plaintext dumps on the application host. | Infrastructure owner selects services, key ownership, region and recovery access. |
| Access and secrets | Dedicated least-privilege backup identity; separate restore identity; MFA for human access; audit all reads/restores; keep credentials in the provider secret manager and rotate them. Never put credentials in the repository, command history, logs or this document. | Security/infrastructure owner provisions and reviews identities and secret rotation. |
| RPO | Proposed target: at most 15 minutes if continuous WAL/PITR is enabled; without it, the daily-backup design has an expected worst-case RPO approaching 24 hours. | Owner approves an achievable RPO after provider and cost review. |
| RTO | Proposed target: restore core database service within 4 hours, measured on a production-sized staging copy and including validation. | Owner approves the business target; operator measures actual recovery time. |
| Monitoring and alerts | Alert on failed backup, missing expected backup, stale last-success timestamp, failed integrity/listing check, storage-capacity threshold and failed restore drill. Route alerts to a named on-call owner and test alert delivery. | Requires monitoring/alert infrastructure and named responders. |
| Restore drills | Monthly automated archive integrity/listing check; quarterly restore into a separate isolated database, followed by migration/schema and application smoke checks. Record elapsed time and row/schema assertions. | Owner approves drill cadence; never restore over the live database. |

No real schedule, encryption service, key, secret, alert or remote storage was configured by this proposal. The proposed 30-day coordinate purge window is subject to final privacy/legal policy. The 2026-11-21 disposable PostgreSQL rehearsal documented above is local synthetic evidence only and does not satisfy these operational controls.

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

## 9. Proposed Render staging deployment

`render.yaml` is a proposed Render Blueprint. It describes a Docker web service, managed PostgreSQL 17, private Render Key Value, a Celery worker and a separate Celery beat scheduler. The web service and both workers use the existing hash-pinned Docker image. `autoDeployTrigger: off` disables automatic deploys on later Git changes; it does not prevent initial resources/deploys when a Blueprint is created or synced, or a manual deploy. Do not create/sync the Blueprint or initiate a deployment until the project owner explicitly authorizes the resulting resources and charges.

### GitHub repository status

Historical checkpoint (2026-11-07): local notes record that `master` and `origin/master` were equal after a normal push through `5aa42cfb631f9e59f975f4904b244465576e2b17`. This is historical Git evidence, not evidence that Render was connected or deployed.

Current local Git check (2026-11-22): `master` is at `0ad4f58767ad3aa46742a6885c0baf29b08d5082`; its configured upstream is `origin/master`, and the local `origin/master` tracking ref points to the same commit (left/right divergence `0/0`; 29 commits in local `master` history). No remote fetch was performed for this check, so the current server-side ref was not independently verified. The worktree has modified and untracked files; those changes are not represented by the current commit. No Render repository connection, account/workspace, resources or deployment is evidenced. Review and finalize the worktree before preparing a release. Future pushes and any Render connection/provisioning/deployment require separate owner authorization. Never use `--force` or `--force-with-lease`; before an authorized push, fetch and inspect remote history and resolve divergence without discarding commits.

Historical actions completed at the 2026-11-07 checkpoint:

- [x] Confirm repository URL, owner and target branch.
- [x] Configure `origin`, fetch remote refs and verify the initially empty remote.
- [x] Push the existing `master` history after explicit authorization and confirm `master` and `origin/master` matched.
- [ ] Connecting GitHub to Render and applying its Blueprint are separate actions. Render provisioning/deployment requires separate explicit authorization and may incur charges.

### Account and repository setup

1. Create or select a Render account and workspace; none is assumed to exist. Confirm billing and who can approve resource creation.
2. Review the expected services and cost estimate below with the account owner. Confirm Singapore is an acceptable region; Render does not allow changing a service's region after creation.
3. Connect the Git provider account that owns the intended BloodConnect repository only after owner authorization. Confirm in Render that it can access the intended repository and branch; a local `origin/master` tracking ref does not establish Render access or approval.
4. Select **New > Blueprint**, choose the connected repository and `render.yaml`, and inspect every planned resource, region, plan and environment variable. Do not press the create/sync/apply action before explicit approval: the initial Blueprint create/sync provisions resources and starts their first builds/deploys even with `autoDeployTrigger: off`.
5. Provide the three `sync: false` SMTP settings in Render's protected prompt/dashboard only when an approved SMTP provider is available. The web service will fail closed without them. Do not substitute fake credentials or enable the mock verification provider.
6. After separate authorization, apply the reviewed Blueprint and observe the initial build/deploy. Keep automatic deploys disabled; subsequent releases must use an explicitly reviewed manual deploy.
7. Use the account checklist in the next section. Record workspace, environment, service IDs, generated web URL and actual billing configuration without recording secret values.

### Render account setup checklist

Preparation is complete locally; the actions below require a Render account and explicit authorization before creation or deployment:

- [ ] Confirm a Render account/workspace and billing owner; choose the Hobby workspace unless a feature explicitly requires another tier. Workspace tier is separate from service compute plans.
- [ ] Review the current cost estimator and approve the five-resource baseline and any possible usage-based charges listed below.
- [ ] Confirm the `singapore` region for the web service, database and Key Value before creation; region changes require replacement/migration.
- [ ] In Render, confirm the intended repository URL, owner, branch and access. This is separate from the locally configured `origin` remote and requires account-side verification.
- [ ] Before any future push, review the complete worktree and obtain explicit owner authorization; then fetch refs and inspect ancestry/divergence. Preserve remote history, use a normal fast-forward push where possible, and never force-push.
- [ ] At the 2026-11-22 local checkpoint, `master` and its local `origin/master` tracking ref both point to `0ad4f58767ad3aa46742a6885c0baf29b08d5082` (0/0 divergence); no fetch was performed and the worktree is not clean. Recheck current refs and worktree before any release action.
- [ ] Confirm an approved SMTP provider and obtain its hostname, username and password through an authorized secret channel. If unavailable, defer initial Blueprint creation because the production web process requires SMTP configuration at startup.
- [ ] In the Blueprint review screen, confirm exactly one web service, one PostgreSQL database, one Key Value instance, one worker and one scheduler; check plans, data disk, region, environment references and first-deploy behavior.
- [ ] Before creating, explicitly approve the initial paid resource provisioning and first build/deploy. A future change to manual deploy policy is not equivalent to initial provisioning approval.
- [ ] After authorized creation, verify the generated `onrender.com` URL, liveness/readiness, migrations, static assets, web/worker/beat logs and a synthetic-only smoke path. Do not claim verification before those checks pass.
- [ ] Prepare a reviewed synthetic location/profile/request fixture set for search and request smoke/load paths. No official Bangladesh location snapshot is currently bundled; do not populate staging with real donor or patient data.
- [ ] Keep auto-deploy off, use synthetic data only, and document actual workspace plan, per-service plans, storage, bandwidth and billing before beginning P8-05/P8-06.

### Region, hostname and DNS

The Blueprint proposes Render's `singapore` region for the web, database and Key Value services. This uses synthetic staging data; do not put real donor/patient data into staging. The selected region cannot be changed in place and should be reviewed before provisioning.

No custom domain or DNS record is required. Render assigns an `onrender.com` subdomain to the web service after provisioning. `DJANGO_ALLOWED_HOSTS` and `DJANGO_CSRF_TRUSTED_ORIGINS` reference Render's runtime `RENDER_EXTERNAL_HOSTNAME` and `RENDER_EXTERNAL_URL` values, so the generated host is not hardcoded here. Do not add a custom domain unless separately approved.

### Environment variables and secrets

The Blueprint defines all configuration needed by these services. Render-generated/service-reference values are populated by Render; only the SMTP values require authorized owner-provided values. Never put actual credentials in the Blueprint, `.env.example`, repository, screenshots or chat.

| Variable | Source/value | Secret? |
|---|---|---|
| `DJANGO_SECRET_KEY` | Generated 256-bit value in the shared Render environment group. | Yes; keep protected. |
| `DJANGO_SETTINGS_MODULE` | `config.settings.production` in the shared group. | No. |
| `DJANGO_DEBUG` | `false` in the shared group; production settings also force `DEBUG=False`. | No. |
| `DATABASE_SSLMODE` | `require` in the shared group; adds TLS to the internal Postgres URL. | No. |
| `DJANGO_ALLOWED_HOSTS` | Self-reference to web service `RENDER_EXTERNAL_HOSTNAME`. No custom host is entered. | No. |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Self-reference to web service `RENDER_EXTERNAL_URL`. Render supplies the HTTPS URL. | No. |
| `DATABASE_URL` | Private connection string from the managed Postgres service. | Yes; contains database credentials. |
| `REDIS_URL` | Private Key Value `connectionString` service reference. With default internal auth disabled this may not include a password; protect it as private connection information. | Private. |
| `BLOODCONNECT_PROCESS_ROLE` | `web`, `worker` or `scheduler` per service. | No. |
| `EMAIL_HOST` | `sync: false`; approved SMTP host. | No, but provider-specific. |
| `EMAIL_HOST_USER` | `sync: false`; approved SMTP username. | Treat as sensitive credential. |
| `EMAIL_HOST_PASSWORD` | `sync: false`; approved Brevo SMTP key/token. | Yes; keep protected. |
| `DEFAULT_FROM_EMAIL` | `sync: false`; verified sender address authorized in Brevo. | Sender identity; protect as operational configuration. |
| `EMAIL_PORT` | `587`. | No. |
| `EMAIL_USE_TLS` | `true`. | No. |
| `EMAIL_USE_SSL` | `false`. | No. |
| `PORT` | Injected by Render for the web process; `scripts/render_start.sh` requires it. | No. |

`DATABASE_URL` and `REDIS_URL` are populated from private service references; they are not values to manually copy. Render's Key Value internal URL is private-network-only by default and internal authentication is not enabled by this Blueprint; an operator can enable it in Render, after which services must use the updated authenticated connection string. `ipAllowList: []` blocks public Key Value access. `noeviction` avoids silently evicting queued tasks but can cause writes to fail when memory is exhausted; monitor memory and queue depth.

Render prompts for `sync: false` values only during initial Blueprint creation. For later secret rotation, change protected service environment settings and perform a reviewed manual deploy/restart. The worker/scheduler do not require web SMTP credentials. The web process requires TLS SMTP credentials and an authorized `DEFAULT_FROM_EMAIL` sender to start. Email account verification uses Django's configured email backend synchronously; there is no SMS verification adapter. Product-notification email, government or identity integrations are not configured.

### Services and cost estimate

The Blueprint currently describes five paid resources (prices below were checked on 2026-11-07; USD, continuous month, before usage extras):

| Resource | Blueprint plan | Current listed baseline |
|---|---|---:|
| Django web | `0.5c-512mb` (0.5 CPU, 512 MB; 1 instance) | $7/month |
| Celery worker | `0.5c-512mb` (0.5 CPU, 512 MB; 1 instance) | $7/month |
| Celery beat scheduler | `0.5c-512mb` (0.5 CPU, 512 MB; 1 instance) | $7/month |
| PostgreSQL 17 | `0.1c-256mb` (0.1 CPU, 256 MB, up to 100 connections), 15 GB disk | $6/month compute + storage beyond included capacity |
| Render Key Value | `256mb` (256 MB, 200 connections), persistent | $10/month |

This is about **$37/month before Postgres storage and metered usage**. Render currently includes 1 GB of Postgres SSD storage and lists additional storage at $0.30/GB/month; if 14 GB of the configured 15 GB is billable, the estimate becomes about **$41.20/month**. Render's Hobby workspace currently has no monthly workspace fee; it includes 5 GB outbound bandwidth and 500 build-pipeline minutes, with overages currently listed at $0.15/GB and $5/1,000 minutes. Charges are prorated by active time, but these figures can change. A PITR recovery database is an additional resource while it exists. SMTP charges, taxes, bandwidth/build overages or workspace-plan upgrades are extra. Verify the Render dashboard's estimate before approving creation; this estimate is not authorization to spend.

These are low starting sizes, selected for a small synthetic staging environment, not a capacity or reliability claim. In particular, the Postgres plan has only 256 MB RAM and 100 connections. Observe memory, CPU, connection count, Key Value memory/queue depth and web/worker restarts during authorized staging checks. Resize only after measured need and explicit cost approval.

### Database provisioning and migrations

The Blueprint creates PostgreSQL 17 with a private connection, no external IP allowlist entries, and a 15 GB disk on the smallest listed paid database compute plan. Keep the database and its services in the same Render region, use the Blueprint's internal `DATABASE_URL` reference, and retain `DATABASE_SSLMODE=require`. Never copy a production database or real personal/health information into staging.

The paid web service's `preDeployCommand` runs `python manage.py migrate --noinput` before a deploy starts. This is a one-off pre-deploy migration step, not a migration on every Gunicorn worker. The web start script runs `collectstatic` and binds Gunicorn to Render's injected `PORT`.

### Staging backup and restore rehearsal

The proposed PostgreSQL service uses a paid compute plan. Render currently documents point-in-time recovery (PITR) for paid Postgres; the available recovery window depends on the workspace plan. PITR creates a separate recovery database so it can be checked before application services are switched over. Render also supports on-demand logical exports in `.dir.tar.gz` format and retains those exports for seven days. Check the database's Recovery page and current workspace terms before relying on either mechanism; a backup or recovery feature description is not proof that a restore works for this application.

When staging has been authorized and contains only synthetic data, use this rehearsal:

1. Record the staging database identity, PostgreSQL major version, application release, current migration state and intended recovery point. Define acceptable recovery point and recovery time objectives before the rehearsal.
2. In the Render Dashboard, select the staging database's Recovery page and create a recovery instance from the intended point in time. This creates a separate resource and may incur charges; do not perform it without explicit resource authorization.
3. Wait until the recovery instance reports available. Connect with the dashboard-provided connection details kept in a protected shell/secret store; never paste URLs into logs, screenshots or chat.
4. Verify expected synthetic reference/fixture records and migration state on the recovery database. Do not use production data or point the running service at the recovery instance during initial validation.
5. If performing a cutover rehearsal, update the staging database reference in the protected Render environment configuration, trigger an authorized manual deploy/restart, then verify readiness, a synthetic search/request flow, and worker connectivity. Restore the original reference if the rehearsal fails.
6. Record elapsed recovery time, selected recovery point, checks performed, discrepancies and actual RPO/RTO. Do not claim success until the recovered database and application checks pass.
7. Keep the original database until the recovery result and any cutover are confirmed. Delete/suspend temporary or old resources only after review and explicit authorization; PITR instances are separate resources.

For a portable logical backup rehearsal, create an export from the dashboard, download and protect the `.dir.tar.gz`, restore it with PostgreSQL's `pg_restore` into a separate empty staging database, and perform the same data/migration/application checks. A Render logical export is retained for seven days, so copy it to an authorized protected archive if longer retention is required. Never restore with `--clean` into a database containing data that must be kept. See [Render Postgres recovery and backups](https://render.com/docs/postgresql-backups) for current recovery and export behavior. P8-06 remains unverified until an actual authorized rehearsal is completed and its evidence recorded.

### Workers, health checks and smoke checks

- The `worker` service runs `celery -A config worker --loglevel=INFO`.
- The `beat` service runs the configured periodic redrive schedule with its schedule file under `/tmp`.
- `/health/ready/` is the Render web health check. It returns 200 only when PostgreSQL and Redis respond. `/health/live/` only indicates that the Django process is serving requests.
- After an authorized deployment, check the generated web URL, `GET /health/live/`, `GET /health/ready/`, static assets, web/worker/beat logs, applied migrations, database and queue connectivity, and one synthetic flow. Do not report a successful deployment until these checks have actually run.

### Render limitations and unresolved integration

Render's free PostgreSQL expires after 30 days and has no managed backups; free Key Value has no persistence, and free web services may spin down. The Blueprint therefore describes paid, persistent staging data services. Render also requires paid web/background-worker resources for the pre-deploy command and Celery processes. Confirm current pricing and workspace billing limits in the Render dashboard before any apply; this document does not authorize charges.

Account-verification codes use the existing digest/expiry/attempt/cooldown service. Development uses the in-memory mock when the complete SMTP configuration is absent; complete SMTP settings select Django SMTP for email, while `EMAIL_BACKEND=django.core.mail.backends.locmem.EmailBackend` explicitly forces the mock. Production uses SMTP and fails closed unless host, credentials, TLS or SSL, and `DEFAULT_FROM_EMAIL` are configured. Delivery is synchronous; phone verification still requires a separately authorized SMS adapter. Never enable the local mock on a public staging service.

### Official Render references

- [Blueprint YAML reference](https://render.com/docs/blueprint-spec)
- [Render Django deployment guide](https://render.com/docs/deploy-django)
- [Render health checks](https://render.com/docs/health-checks)
- [Render Postgres connections](https://render.com/docs/postgresql-creating-connecting)
- [Render Key Value](https://render.com/docs/key-value)
- [Free instance limits](https://render.com/docs/free)
- [Render compute plans](https://render.com/docs/compute-plans)
- [Render pricing](https://render.com/pricing)
- [Render environment variables and secrets](https://render.com/docs/configure-environment-variables)
