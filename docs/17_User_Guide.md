# BloodConnect BD User Guide

**Audience:** recipients, donors and local evaluators
**Status:** describes the current server-rendered web workflows; verify the plan and deployment checkpoint for release status.

BloodConnect BD helps people discover potential blood donors and coordinate a contact request. It does not assess medical eligibility or compatibility, collect or supply blood, or replace advice from a qualified healthcare professional and authorized facility. Blood group is a search filter only.

Use synthetic accounts and data for demonstrations. Privacy, terms and safety text are drafts pending qualified local review. The current production verification adapter is not configured, so public account verification is not available in a deployed environment until an authorized provider is implemented.

## Create and verify an account

1. Open **Create account** and provide exactly one email address or phone number, a display name and password.
2. Review and acknowledge the displayed Terms and Privacy versions.
3. Submit the form. The account remains pending until the submitted identifier is verified.
4. In local development and automated tests, the mock verification provider keeps the code in process memory and does not send a real message. Follow the developer workflow for retrieving a synthetic test code; never use a real person's identifier in fixtures.
5. Sign in after verification. Use password reset only for an identifier/account that can receive its configured reset message.

## Find potential donors

The donor search at `/app/` is available to guests and signed-in users. Choose an exact blood group and, if desired, a division, district and upazila. Results are paginated at 20 per page. Invalid or mismatched location filters do not broaden the search.

Only active profiles marked available, with visibility enabled and current donor-discovery consent, can appear. Search cards show a public alias, blood group, availability and administrative location names. They do not show a donor's account name, email, phone number or contact preferences. A search result is not a statement of medical eligibility or transfusion compatibility.

## Create and manage a donor profile

After signing in, open **Donor profile** from the application navigation. Set the blood group and administrative location, choose whether the profile is visible, and manage availability. Discovery consent is managed separately in account privacy settings. A profile appears in search only while all required profile, availability, visibility and consent conditions remain true.

Do not enter another person's details. Keep phone visibility and other contact preferences private unless you understand the later acceptance and consent rules.

## Create a blood request

Open **Blood requests** and create a request with the required blood group, time, location and urgency. Facility details and the description are visible only to the request owner; the public listing omits those fields. Requests can be edited or moved through the available lifecycle by their owner. Use synthetic facility names and descriptions in tests and demonstrations.

## Contact a donor

From a donor result, an active recipient can send a contact request with an optional coordination message. The donor can review incoming requests and accept or decline; the recipient can cancel an outgoing pending request. A pending request does not reveal the donor's contact details.

After acceptance, the recipient may see only the donor contact channels that are currently verified and consented. Withdrawing consent removes the channel from subsequent disclosure. Keep messages respectful and limited to coordination; do not include sensitive medical narratives.

## Notifications, safety reports and account privacy

The signed-in application includes participant-scoped notifications and contact/request views. Users can report a safety concern and block another account. Report details remain private to the reporter and authorized moderators. Staff status alone does not grant moderator access.

Privacy settings record purpose-specific consent changes. Review those settings if you no longer want a profile discoverable or a contact channel shared. Account data retention and deletion policy remains unresolved; do not use the current application for real personal or health information.

## Sign-in and API use

The web application uses session login. API clients use the versioned token flow and examples in [`16_API_Usage_Guide.md`](16_API_Usage_Guide.md). Keep bearer tokens private; rotate refresh tokens as described there. API and web authorization rules both restrict private records to their owners or participants.

## Known limitations

- No reviewed official Bangladesh location snapshot is bundled; real donor profiles require reviewed location data.
- No production email/SMS account verification provider is enabled.
- Notifications use mock delivery adapters; no real SMS or product notification delivery is configured.
- The hosted staging Blueprint has not been applied; see [`09_Deployment.md`](09_Deployment.md) and [`EXECUTION_STATE.md`](EXECUTION_STATE.md).
- Privacy/terms content awaits local legal review; operational backup restore, load and hosted security evidence remain incomplete.
