# 11 — Data Governance, Privacy and Safety

## 1. Data minimization

Collect only data needed for account access, donor discovery, request coordination, safety and lawful operation.

Do not collect NID numbers, medical records, laboratory results, diagnoses or exact home coordinates in MVP.

## 2. Data classification

| Class | Examples | Handling |
|---|---|---|
| Public | Product pages, approved organization address | Public |
| User-private | Email, phone, profile settings | Owner/authorized access |
| Sensitive coordination | Blood group, request details, contact decisions | Restricted, minimized |
| Security | Audit events, auth events | Highly restricted |
| Secret | Password hashes, tokens, provider credentials | Never expose/log |

Blood group and request context should be treated as sensitive personal information even if a specific legal classification may vary.

## 3. Consent

Capture separate, versioned consent for:
- donor profile discoverability;
- contact channel disclosure after donor acceptance;
- optional notifications;
- optional location/map display;
- future organization sharing, if introduced.

Consent must be clear, purpose-specific, revocable where applicable and recorded with policy version and timestamp.

## 4. Donor privacy

- Donor contact details are hidden by default.
- Donor profile is discoverable only after explicit opt-in.
- Generalized area is displayed; exact address is not.
- Donor can pause or hide their profile.
- Donor may accept/decline contact requests.
- Only donor-selected contact channels are disclosed after acceptance.
- Avoid displaying last donation date publicly.

## 5. Medical and safety boundaries

- Platform does not assess donor eligibility.
- Platform does not calculate transfusion compatibility.
- Exact blood-group search is a discovery filter only.
- Healthcare professionals and authorized facilities determine clinical suitability and compatibility.
- Platform does not guarantee that a donor will respond or donate.
- Users should coordinate through an authorized healthcare facility.
- Emergency messaging must not imply the platform replaces emergency services.

## 6. Verification terminology

Allowed:
- Phone verified.
- Email verified.
- Account reviewed.
- Organization identity reviewed (scope shown).

Not allowed:
- Medically verified donor.
- Safe donor.
- Clinically eligible.
- Compatible donor.
- Blood guaranteed.

## 7. Bangladesh legal and regulatory review

Before real public launch, obtain qualified local legal and healthcare review of:
- applicable personal-data protection requirements;
- cyber/security obligations;
- consent and retention rules;
- electronic communications and OTP/SMS provider obligations;
- blood transfusion and blood-bank regulatory boundaries;
- terms, privacy notice and incident response.

Do not claim legal compliance solely because a feature exists. Government or health-data integration requires written authorization, API documentation, data-sharing basis and security review.

## 8. Retention and deletion

- Define retention schedule for accounts, requests, reports, audit events and backups.
- Deactivation immediately hides a donor profile from discovery.
- Provide an account/data request workflow.
- Preserve records only where a documented legal, safety or security reason requires it.
- Apply deletion/retention policy consistently to backups and third-party providers.
- Record administrative exceptions.

## 9. Analytics

- Prefer aggregate counts.
- Avoid small-cell reporting that could re-identify individuals.
- Do not expose individual donor histories to public analytics.
- Do not use sensitive attributes for advertising or ranking.
