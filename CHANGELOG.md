# Changelog

Notable project changes are recorded here. This repository has no tagged or numbered release yet.

## Unreleased

### Added

- Local registration, login, account verification seam, and password recovery.
- Self-reported donor profiles, consent-gated potential donor discovery, and availability controls.
- Requester-owned blood request workflows and donor-controlled contact requests.
- Acceptance- and consent-gated contact disclosure, in-app notifications, reports, blocks, moderation, and minimized audit records.
- Aggregate operational metrics, a documented versioned API, local Docker Compose services, and developer/test guides.

### Security and privacy

- Donor contact data stays private until the donor explicitly accepts and has consented to share the selected channel.
- Local verification is mock-only. Production provider delivery and hosted deployment remain unverified.

### Limitations

- Reviewed official Bangladesh location data is not bundled.
- Terms and Privacy Notice are drafts that require local legal/healthcare review.
- No hosted Render deployment, backup restore rehearsal, staging load test, or production release has been verified.
