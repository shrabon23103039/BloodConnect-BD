# 07 — Security Requirements and Threat Model

## 1. Security objectives

Protect account access, donor privacy, request integrity, consent and service availability. Apply least privilege and defense in depth.

## 2. Assets

- Authentication credentials and session/token material.
- Donor identity and contact details.
- Donor blood-group and self-reported profile data.
- Recipient requests and free-text descriptions.
- Contact-request decisions.
- Moderation reports.
- Consent history.
- Admin actions and audit events.
- External provider credentials.

## 3. Threat actors

- Unauthenticated scraper.
- Malicious registered user.
- Fake donor or requester.
- Abusive user attempting harassment.
- Compromised administrator account.
- External provider compromise.
- Accidental internal disclosure.

## 4. Main threats and controls

| Threat | Control |
|---|---|
| Donor data scraping | Authentication where appropriate, pagination, throttling, minimal public fields |
| Contact harvesting | Contact request gate; no public phone/email |
| Account takeover | Strong password hashing, verification, throttling, secure sessions, optional MFA for admins |
| IDOR/BOLA | Object-level authorization on every endpoint |
| Fake emergency requests | Reporting, moderation, rate limits, duplicate detection |
| OTP abuse | Per-account/IP/device throttling, expiry, one-time use |
| CSRF | Django CSRF middleware and secure cookie policy |
| XSS | Template escaping, safe rendering, content sanitization |
| SQL injection | ORM and parameterized SQL only |
| File upload abuse | Allowlist, size limits, content inspection, private storage |
| Admin misuse | Least privilege, MFA where available, immutable audit events |
| Provider compromise | Adapter isolation, secret rotation, minimum scopes |
| Data loss | Encrypted backups and restore tests |
| Denial of service | Rate limits, request size limits, reverse-proxy protections, monitoring |

## 5. Privacy boundaries

Public donor search must never return:
- phone number;
- email;
- exact home address;
- precise GPS coordinates;
- identity documents;
- private notes;
- verification evidence.

Before donor acceptance, recipient sees only the donor's consented public profile. After acceptance, reveal only the contact method explicitly selected by the donor.

## 6. Sensitive action requirements

- Contact-request accept/decline must be authenticated and authorized.
- State transition and audit record must be atomic.
- Sensitive profile changes require re-authentication where appropriate.
- Account deletion/deactivation must immediately remove donor from search.
- Admin exports must be permission-gated and audited.
- Logs must redact phone, email, tokens, OTP and message content.

## 7. Operational controls

- Separate development, staging and production secrets.
- Secret manager or protected environment variables.
- Dependency scanning in CI.
- Regular patch review.
- Backup encryption and access control.
- Restore drills.
- Incident response owner and escalation process.
- Security contact and vulnerability-reporting process before public launch.

## 8. Release blockers

Do not launch publicly if:
- private donor fields are exposed by any route/API;
- object-level authorization is missing;
- production DEBUG is enabled;
- secrets are committed;
- critical/high vulnerabilities remain without accepted mitigation;
- backups cannot be restored;
- privacy notice/consent is absent;
- the platform presents itself as a medical authority.
