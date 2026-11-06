# 08 — Test Strategy and Quality Assurance

## 1. Testing objectives

Verify functional behavior, privacy, authorization, state transitions, accessibility, resilience and measured performance.

## 2. Test levels

### Unit tests
- Blood-group enum validation.
- Location hierarchy validation.
- Donor availability state.
- Blood-request state transitions.
- Contact-request state transitions.
- Permission helper functions.
- Notification idempotency.

### Integration tests
- Registration and verification.
- Donor profile creation and search.
- Request creation and donor search.
- Contact request and notification.
- Donor acceptance and contact disclosure.
- Report/block workflow.
- Celery retry and provider failure.

### End-to-end tests
- Visitor registers.
- User creates donor profile.
- Recipient creates a blood request.
- Recipient searches donor and sends contact request.
- Donor signs in and accepts.
- Recipient sees only donor-consented contact channel.
- Recipient closes request.
- Admin reviews a report.

### Security tests
- Unauthenticated access to private endpoints.
- Cross-user object access.
- Serializer field leakage.
- CSRF behavior.
- Rate limits.
- Upload restrictions.
- Admin privilege boundaries.
- Token expiry/revocation.

### Non-functional tests
- Responsive layout at defined widths.
- Keyboard navigation and accessible labels.
- Load test for search and request creation.
- Backup restore.
- Provider outage behavior.

## 3. Critical acceptance tests

| ID | Scenario | Expected result |
|---|---|---|
| T-001 | Guest requests donor private profile | Private data not returned |
| T-002 | Recipient searches donor | Only consented public fields returned |
| T-003 | Recipient sends contact request | Pending request created once |
| T-004 | Duplicate request submitted | Duplicate blocked/idempotently handled |
| T-005 | Wrong user accepts request | 403 or non-disclosing 404 |
| T-006 | Donor declines | Contact data remains hidden |
| T-007 | Donor accepts without phone-share consent | Phone remains hidden |
| T-008 | Donor accepts with phone-share consent | Only allowed phone field is returned to parties |
| T-009 | Donor becomes unavailable | Excluded from new discovery results |
| T-010 | Request cancelled | New contact requests blocked |
| T-011 | User blocks another user | New contact request blocked according to policy |
| T-012 | Admin suspends account | Account cannot use restricted features |
| T-013 | OTP replay | Rejected |
| T-014 | OTP brute force | Rate limited |
| T-015 | Notification provider down | Core transaction remains committed; retry recorded |

## 4. Tooling

- pytest and pytest-django for unit/integration tests.
- Django TestCase for framework-specific tests.
- DRF APIClient for API tests.
- Playwright for browser flows.
- Locust for load tests.
- Coverage.py for coverage reporting.
- Bandit or equivalent static security scanning.
- Dependency vulnerability scanner.
- OWASP ZAP for controlled staging DAST where configured.

## 5. Performance test protocol

Before running a load test, document:
- Environment and hardware/hosting plan.
- Database size and synthetic data distribution.
- Number of virtual users.
- Ramp-up period.
- Test duration.
- Request mix (search, dashboard, request read/write).
- Cache warm/cold state.
- p50, p95 and p99 latency.
- Throughput.
- Error rate.
- CPU, memory, database connections and queue depth.

Do not equate registered users with concurrent users. Do not publish a capacity claim without a repeatable test report.

## 6. Defect severity

- Critical: data exposure, account takeover, unauthorized state change, core service unavailable.
- High: major workflow broken, significant privacy/security weakness.
- Medium: feature degraded with workaround.
- Low: cosmetic or minor usability issue.

Critical and high defects block release unless a formally documented exception is approved by the project owner and appropriate reviewer.

## 7. Evidence requirements

For each test run, record:
- commit hash;
- environment;
- command;
- date;
- pass/fail count;
- failing test IDs;
- artifact/report location;
- known limitations.

Never fabricate test output or mark a test passed based on code inspection alone.
