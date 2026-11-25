# 01 — Product Requirements Document (PRD)

**Product:** BloodConnect BD  
**Version:** 1.0  
**Status:** Baseline for MVP  
**Date:** 2026-11-06

## 1. Product summary

BloodConnect BD is a Bangladesh-focused, P2P-first platform for discovering potential blood donors and coordinating contact between people requesting blood and registered donors. A recipient searches using requested blood group and location, submits a contact request, and the donor chooses whether to accept. The system protects donor contact information until acceptance.

The platform is a coordination and discovery service. It is not a blood bank, hospital, diagnostic service or clinical decision-support tool.

**Find Donor product change (2026-11-22):** The previous administrative-filter-first search is superseded by a location-first concept: clickable blood-group buttons, a required confirmed search location, browser geolocation, a draggable map pin, optional radius and hospital search, with administrative filters collapsed under advanced options. The `/app/` selection UI is now implemented, but nearby matching is not: the location/radius controls do not search donors or submit requester coordinates, and existing administrative GET search remains the only result-producing search.

## 2. Problem statement

People seeking blood may rely on fragmented social networks and informal contacts. It can be difficult to find potential donors by blood group and location, understand whether a donor is currently willing to be contacted, track requests and protect donor privacy. BloodConnect BD provides a structured discovery and consent-based coordination workflow.

## 3. Vision

Make potential blood-donor discovery and coordination more organized, privacy-conscious and accessible across Bangladesh, while allowing authorized institutions to participate in future versions.

## 4. Target users and personas

### 4.1 Recipient / requester
- Needs to publish a blood request.
- Searches for potential donors by requested blood group and location.
- Needs a safe way to request contact.
- Must understand that the platform does not guarantee a donor or medical suitability.

### 4.2 Donor
- Wants control over availability and visibility.
- Wants to receive relevant requests without exposing a phone number publicly.
- Can accept, decline, ignore or report contact requests.
- Can pause or deactivate a donor profile.

### 4.3 Moderator / administrator
- Reviews reports and suspicious behavior.
- Manages user accounts and platform content.
- Reviews organization applications if that optional module is enabled.
- Must not impersonate medical verification.

### 4.4 Organization representative (future/optional)
- Represents a hospital or licensed blood bank.
- Can maintain an organization profile after verification.
- Does not receive privileged access to donor private data by default.

## 5. Product principles

1. Consent before contact disclosure.
2. Minimum necessary personal data.
3. Clear distinction between platform verification and medical eligibility.
4. Accessible, mobile-first interface.
5. No false promises about blood availability.
6. Modular architecture and auditable workflows.
7. No dependence on government or hospital APIs for MVP operation.

## 6. MVP scope

### Included
- Public landing page and product information.
- Account registration, login, logout and password reset.
- Email/phone verification integration seam; development may use a clearly labeled mock provider.
- Donor profile creation and editing.
- Donor profile area selection using the existing Google Maps browser integration: the donor may select and confirm a general area, then explicitly consent to private storage of its point, general-area label, source and confirmation timestamp. This profile-only selector does not request GPS or enable donor matching; do not collect an exact street address.
- Donor availability toggle.
- Location-first Find Donor search with a required, user-confirmed search location; users may choose a place, explicitly request browser current location, or adjust and confirm a draggable map pin.
- Clickable single-select blood-group buttons using the exact labels A+, A-, B+, B-, AB+, AB-, O+, O-; retain an “Any blood group” option unless product review decides the group must be required.
- Optional radius choices of 5, 10, 20 or 50 km; default results include available donors only.
- Optional hospital/place lookup as a way to select a search location; it does not assert hospital affiliation or clinical suitability.
- Collapsed advanced administrative filters for available reviewed location levels.
- Map-based location selection and generalized results. The local browser UI reuses Google Maps JavaScript, Places and Geocoding when its restricted development browser key is configured. This does not select a production or backend-matching provider; provider terms, cost, data transfer and legal review remain required. Browser geolocation is browser-native and does not require Google.
- Requester and donor coordinates must be inside an approved Bangladesh boundary. Requester coordinates are submitted by POST, used for that search only, and never persisted or logged. PostGIS performs server-side `ST_DWithin` radius eligibility using donor-confirmed points only. Donors with only administrative-area data may appear separately under “Area matches — distance not verified”; they are never radius-qualified or assigned a distance. If the interface cannot separate them clearly, omit them from radius results. Public distance is straight-line and approximate, displayed only in the defined coarse bands; never expose donor coordinates or exact address.
- Blood request creation, editing, cancellation and closure.
- Recipient-to-donor contact request.
- Donor accept/decline workflow.
- Contact detail disclosure only after acceptance and only for explicitly consented fields.
- In-app notifications.
- User reporting and blocking.
- Admin moderation dashboard.
- Audit events for sensitive actions.
- Responsive web interface.
- Basic operational dashboard metrics without exposing individual health details.

### Optional only if time permits
- Email notifications.
- SMS adapter using a sandbox/mock provider.
- Organization directory with manually curated public information.
- CSV export for authorized administrators, with privacy review.

## 7. Explicit non-goals / out of scope

The following are not part of MVP and must not be quietly added by an agent:

- Blood collection, storage, processing, sale, transport or transfusion.
- Medical advice, donor eligibility assessment or clinical compatibility determination.
- A blood inventory system or real-time stock claim.
- Hospital appointment, laboratory or electronic medical record management.
- NID verification or direct access to government identity databases.
- DGHS production integration, NRDEX integration or any other government API without formal authorization.
- Automatic donor selection that claims clinical compatibility.
- Payments, commissions, paid donor ranking or sale of donor information.
- Public display of donor phone numbers, email addresses or exact locations.
- Public direct messaging before donor acceptance.
- Native mobile app in MVP; mobile is a future client using the same API.
- Microservices, Kubernetes, event streaming or multi-region deployment in MVP.
- Claiming 100,000 concurrent users or national production readiness without load-test and operational evidence.

## 8. MVP user stories and acceptance criteria

### US-01 — Register
As a visitor, I want to create an account so that I can use platform features.
- Required fields are validated server-side.
- Duplicate email/phone handling is clear.
- Passwords are never stored in plaintext.
- Verification status is explicit.

### US-02 — Become a donor
As a registered user, I want to create a donor profile so that recipients can discover me.
- Blood group is required. The donor may search for and explicitly confirm an optional general donation area in the profile editor.
- Store the point, general-area label, optional Google Place ID, source and server-set confirmation timestamp privately only after separate `donor_area_storage` consent. The point is not assumed to be the donor's home; no exact street address or browser GPS is collected.
- The donor can review, replace or remove the point. Clearing the area removes all associated point metadata and records withdrawal of storage consent.
- This selector alone does not make map-only profiles discoverable or enable coordinate/radius matching. Existing active-account, availability, visibility and discovery-consent requirements remain unchanged.
- Availability defaults to unavailable until the donor explicitly opts in.
- Profile visibility and contact preferences are consent-based.
- The UI does not label the user medically eligible.

### US-03 — Search donors
As a recipient, I want to find potential donors around a location I choose.
- The user selects an exact blood-group label with accessible clickable controls; “Any blood group” remains available unless a later decision makes blood group mandatory.
- A location must be selected and explicitly confirmed before search. Choices include place lookup, browser geolocation after a user gesture and permission, or a draggable map pin.
- The frontend submits the requester's confirmed latitude/longitude to the backend using POST; those search coordinates are transient and are never stored in database records, logs or analytics. Reject requester and donor points outside a reviewed, approved Bangladesh boundary; do not use a hand-written bounding box.
- Optional radius values are 5, 10, 20 or 50 km. PostGIS performs server-side radius eligibility using donor-confirmed coordinates and the exact geospatial threshold. Administrative-only donors are never radius-qualified; if included, they appear in a separate “Area matches — distance not verified” section with no distance. Omit them from radius results if the UI cannot clearly separate the sections.
- Available, visible, active profiles with current discovery consent are the default results. Inactive, suspended, hidden and unavailable profiles are excluded.
- Results are paginated and rate-limited and may show only a generalized area and one coarse straight-line approximate distance band: `<2 km`, `2–5 km`, `5–10 km`, `10–20 km`, `20–50 km`, or `>50 km`. Distance bands do not control radius eligibility. Never include donor phone, email, exact address, donor coordinates, or a distance for area-only matches.
- Advanced administrative filters are collapsed by default and supplement, rather than replace, the required search location.
- Optional hospital lookup selects a search location only; it does not verify a facility or imply medical suitability.

### US-04 — Create blood request
As a recipient, I want to publish a request with relevant details.
- Required fields are validated.
- Emergency priority is informational and does not guarantee response.
- The request has a controlled status lifecycle.
- The requester can edit/cancel according to state rules.

### US-05 — Request donor contact
As a recipient, I want to ask a donor to contact me.
- The recipient must be authenticated and the request must be active.
- Duplicate pending contact requests are prevented.
- Donor receives a notification.
- No private contact details are disclosed before acceptance.

### US-06 — Accept or decline
As a donor, I want to decide whether to respond.
- Only the addressed donor can decide.
- Decision is recorded with timestamp.
- Acceptance reveals only the contact channels the donor consented to share.
- Decline does not reveal private data.
- Expired/cancelled requests cannot be accepted.

### US-07 — Report or block
As a user, I want to report or block abusive accounts.
- Reports are private to authorized moderators.
- Blocked parties cannot create new contact requests to each other.
- Report details are not exposed to the reported user.

### US-08 — Moderate
As an administrator, I want to review suspicious activity.
- Admin access requires a privileged role.
- Sensitive actions are audit logged.
- Admin views follow least privilege.
- Admins cannot mark a donor medically eligible.

## 9. Success metrics

Metrics are product indicators, not promises:
- Registration completion rate.
- Percentage of donor profiles with complete, consented discovery fields.
- Search-to-contact-request conversion.
- Donor response rate.
- Percentage of requests closed with a requester-confirmed outcome.
- Median time from request publication to first donor response (measured only after sufficient real usage).
- Abuse report rate and moderation resolution time.
- Search/API p50 and p95 latency under a documented test workload.
- Error rate and notification delivery rate.

Do not use "units of blood supplied" as a platform success metric unless independently verified by an authorized facility and collected lawfully.

## 10. User roles and permissions

- Guest: public pages and limited search results according to privacy policy.
- Authenticated user: own profile, own requests, contact requests addressed to them, reports.
- Donor: donor profile and donor decisions.
- Moderator: assigned reports and moderation actions.
- Superadmin: platform configuration and privileged administration.
- Organization user: future, scoped organization records only.

## 11. Product constraints and assumptions

- Initial launch is a controlled demonstration/MVP, not a nationwide medical service.
- Bangladesh administrative location data must be loaded from a reviewed source and versioned.
- External OTP/SMS/email services may require credentials and paid plans.
- Government and institutional integrations require approval, documentation and credentials.
- Medical and legal content must be reviewed by qualified local professionals before public launch.
- All metrics must be measured; no invented results.

## 12. Release definition

MVP can be released for controlled testing only when all critical acceptance criteria in `08_Testing.md` and `15_Release_Checklist.md` pass, privacy and security review is complete, backups are tested, and all known critical defects are resolved.
