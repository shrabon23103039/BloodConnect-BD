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
