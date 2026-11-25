# 15 — Release Readiness Checklist

A release is not approved until applicable checks are completed with evidence.

## Product and scope
- [ ] MVP scope matches `01_PRD.md`.
- [ ] No medical eligibility or compatibility claims.
- [ ] No blood collection/storage/sale/transfusion function.
- [ ] Safety and privacy notices are visible.
- [ ] No fake government or hospital integration.

## Privacy and security
- [ ] Donor contact data hidden before acceptance.
- [ ] Donor consent checked before each contact disclosure.
- [ ] Object-level authorization tested.
- [ ] Admin permissions reviewed.
- [ ] Rate limits enabled.
- [ ] OTP/session/token security tested.
- [ ] File upload controls tested.
- [ ] Secrets absent from repository and build artifacts.
- [ ] Production DEBUG disabled.
- [ ] HTTPS and secure cookies configured.
- [ ] Logs scrubbed of PII/secrets.

## Quality
- [ ] Unit tests pass.
- [ ] Integration tests pass.
- [ ] End-to-end critical flows pass.
- [ ] Regression tests pass.
- [ ] Accessibility review completed.
- [ ] Responsive layouts reviewed.
- [ ] Critical/high defects resolved or formally accepted with mitigation.

## Operations
- [ ] Database migrations reviewed.
- [ ] Backup schedule configured.
- [ ] Restore test completed.
- [ ] Health/readiness checks work.
- [ ] Monitoring and alerts configured.
- [ ] Rollback plan documented.
- [ ] External provider failure behavior tested.

## Performance
- [ ] Workload defined.
- [ ] Load test executed.
- [ ] p50/p95/p99 latency recorded.
- [ ] Throughput and error rate recorded.
- [ ] Infrastructure and dataset described.
- [ ] No unsupported user-capacity claims.

## Documentation
- [ ] SRS matches implementation.
- [ ] API schema updated.
- [ ] User guide updated.
- [ ] Known limitations listed.
- [ ] Release notes written.
- [ ] `06_Plan.md` updated with evidence.

## Approval
- Release version:
- Commit:
- Environment:
- Date:
- Reviewer:
- Known limitations:
- Decision: APPROVED / NOT APPROVED

## Local review evidence (2026-11-21 Asia/Dhaka)

- [x] Local test evidence reviewed: prior complete run was 172 pytest passed, 1 skipped, and 6 subtests passed; Django runner 160 passed; Playwright Chromium workflow passed. This task did not rerun the suite.
- [x] Local source checks: Django test-settings system check, migration drift check, applied-migration check, Compose config validation, and `git diff --check` passed. Production `check --deploy` passed with synthetic process-only settings.
- [x] Migration review: location source ID migration is additive and preserves existing primary keys and foreign-key references.
- [x] Secret/environment handling review: `.env` exists and remains ignored; it was not opened or modified. Production settings require configured secrets and HTTPS origins and enable secure cookies/HSTS. No real production values were validated.
- [x] Local data safety: the existing PostgreSQL database still contains 567 inactive candidate locations (8/64/495); none were activated or changed during this review.
- [ ] Official location dataset and reuse terms: unresolved. National Portal reports 502 upazilas but exposes no reviewed stable identifiers or reuse license in the inspected page; NSDI map data is 2023/ongoing and provider terms vary. Keep candidate inactive.
- [x] Isolated local PostgreSQL 17.11 synthetic custom-format dump/restore rehearsal: verified; archive listed, restored 34 migrations and two synthetic rows, passed Django system check and Django query. See `09_Deployment.md`.
- [ ] Backup schedule, encryption, retention, RPO/RTO and hosted/provider restore: not verified; local rehearsal does not establish these operational controls.
- [ ] Production/staging infrastructure, HTTPS endpoint, SMTP/SMS delivery, monitoring/alerts, admin review, load metrics, formal accessibility, legal/privacy approval and release sign-off: not verified or not authorized.
- Decision: NOT APPROVED for staging or production. Local synthetic demo only; location filters remain empty until a reviewed source is approved. See `EXECUTION_STATE.md` for evidence and boundaries.

## Final staging-readiness assessment (2026-11-21 Asia/Dhaka)

The following labels classify the checklist against recorded evidence. A historical local pass is not a staging or production pass.

| Checklist area / item | Classification | Evidence or remaining action |
|---|---|---|
| MVP scope, non-medical boundary, safety/privacy notices and no false government integration | Documentation prepared; requires human approval | Product and safety docs exist; owner/legal/healthcare review remains required before public use. |
| Contact privacy, consent gate, object authorization, rate limits, OTP/session and auth regression coverage | Verified locally (2026-11-21 QA record) | Automated suite and Chromium workflow passed; production Redis/provider behavior remains infrastructure-dependent. |
| Admin permission review | Requires human approval | Automated role checks exist; appoint an independent reviewer and review real deployment roles. |
| File-upload controls | Not completed | Confirm whether uploads are in release scope; if enabled, perform controls and abuse tests before staging. |
| Secret scan of source and built artifacts | Not completed | Gitleaks was unavailable in the recorded QA environment; obtain an artifact/repository scan and independent review. `.env` was not inspected. |
| Production `DEBUG=False`, required hosts/origins, database TLS, secure cookies and HSTS configuration | Verified locally with synthetic settings | Production `check --deploy` passed; actual HTTPS, proxy headers, certificate and cookie behavior require infrastructure. |
| PII-safe logging | Verified by local code review; hosted log review requires infrastructure | Logger uses an allowlist; verify deployed logs and retention after infrastructure exists. |
| Unit, integration and regression suite | Verified locally (historical) | 172 pytest passed, 1 skipped, 6 subtests; Django runner 160 passed. Not rerun for this assessment. |
| Critical browser workflow | Verified locally (historical) | Playwright Chromium workflow passed using synthetic data. |
| Responsive smoke checks | Verified locally (2026-11-07); full accessibility audit not completed | Viewports 320/375/768/1280 passed on selected pages; keyboard/screen-reader and full WCAG review remain. |
| Critical/high defect acceptance | Requires human approval | No independent release risk acceptance recorded. |
| Migration review and consistency | Verified locally (2026-11-21) | Additive location source-ID migration reviewed; migration consistency check passed. |
| Local backup and restore procedure | Verified locally (2026-11-21) | Disposable PostgreSQL 17.11 custom-format backup/restore passed; see `09_Deployment.md`. |
| Automated backup schedule, encryption, retention, RPO/RTO, off-site copy and restore alerts/drills | Requires infrastructure; proposed values require human approval | Recommendations are documented in `09_Deployment.md`; no service or schedule is configured. |
| Health/readiness | Verified locally (historical) | Local endpoints checked dependencies; hosted endpoint and alert integration require infrastructure. |
| Monitoring and alert delivery | Requires infrastructure | Select provider, service-level signals, retention, alert route and responder. |
| Rollback/recovery plan | Documentation prepared; not rehearsed | Deployment guide describes rollback principles; test against the eventual hosting/migration design. |
| External provider failure behavior | Verified locally with mocks only; real provider behavior requires infrastructure | No real SMS/email provider contacted; test sandbox and failure modes after authorization. |
| Workload, load test, latency percentiles, throughput and error rate | Requires infrastructure; not completed | P8-05 needs a representative authorized staging target and approved synthetic workload. |
| Bangladesh location hierarchy, identifiers and reuse rights | Requires authoritative data or licensing | Candidate 495 upazilas vs National Portal 502; no exact reconciliation/license; 567 rows remain inactive. |
| API schema | Verified locally (historical) | `spectacular --validate` passed in prior QA. |
| SRS, user guide and known limitations | Documentation prepared; implementation alignment review required | Review each against the intended staged scope before release. |
| Release notes | Not completed | Prepare notes for the approved release/version. |
| HTTPS/DNS, PostgreSQL/Redis, workers, storage, secret manager and monitoring | Requires infrastructure | Provision only after explicit owner authorization and cost/region review. Required variable names are listed in `09_Deployment.md`; values must be supplied through protected secret channels. |
| Staging deployment, smoke tests and hosted restore | Requires infrastructure and human approval | Not performed; Render Blueprint remains unapplied. Owner approval required for account connection, resource costs, region, initial provisioning and deployment. |
| Privacy/legal/healthcare review, provider authorization and release sign-off | Requires human approval | No external delivery, legal determination or release decision is implied by local tests. |

### Staging decision

**NO-GO at this time.** Before provisioning: owner approval of staging scope, account, region and expected charges; an approved provider/secret-handling path; named privacy/security and operations reviewers; and a decision whether staging may operate with location filters empty. Do not activate the candidate dataset. Once authorized, staging can validate HTTPS/proxy/cookies, migrations, monitoring and alerts, synthetic critical flows, provider sandboxes, rate limits, workload, and a restore drill into a separate target. Those checks have not been performed.
