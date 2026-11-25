# 02 — Application Flow and Screen State Machine

**Version:** 1.0  
**Client:** Responsive web MVP; API supports future mobile client.

## 1. Global navigation

### Guest navigation
- Home `/`
- How it works `/how-it-works/`
- Find donors `/donors/` (public fields only; access policy may require sign-in)
- Register `/accounts/register/`
- Login `/accounts/login/`
- Privacy `/privacy/`
- Safety `/safety/`

### Authenticated navigation
- Find donors `/app/`
- Blood requests `/app/requests/`
- Contact requests `/app/contact-requests/`
- Notifications `/app/notifications/`
- Profile `/app/profile/`
- Donor settings `/app/donor-profile/`
- Help and safety `/app/help/`

Admin routes use Django Admin and/or a protected custom area under `/admin/`. Never rely on hidden navigation as authorization.

## 2. Global states

Every data-driven screen must support:
- `INITIAL`: initial render.
- `LOADING`: request in progress.
- `SUCCESS`: data loaded.
- `EMPTY`: no records.
- `VALIDATION_ERROR`: user input invalid.
- `AUTH_REQUIRED`: login required.
- `FORBIDDEN`: user lacks permission.
- `NOT_FOUND`: resource unavailable or not visible.
- `RATE_LIMITED`: too many requests.
- `NETWORK_ERROR`: retryable connectivity failure.
- `SERVER_ERROR`: generic failure with correlation ID.
- `OFFLINE`: browser offline; never imply a write was saved unless confirmed.

Use inline field errors for validation and a non-sensitive global message for unexpected errors. Do not expose stack traces, SQL errors, tokens or private data.

## 3. Screen specifications

### S-01 Home
Route: `/`
- Actions: Find donors, Register, Login, How it works.
- Content: purpose, safety boundary, how P2P contact works, emergency disclaimer.
- Empty state: not applicable.
- Error state: static content remains usable if analytics or optional API calls fail.

### S-02 Registration
Route: `/accounts/register/`
Fields: display name, email or phone (depending on selected auth path), password, confirm password, terms/privacy consent.
Actions: Create account, show/hide password, go to login.
States: submitting, validation errors, duplicate account, verification required, success.
Rules: never reveal whether an arbitrary phone/email belongs to an account in a way that enables enumeration.

### S-03 Login
Route: `/accounts/login/`
Actions: Sign in, forgot password, register.
States: invalid credentials, throttled, disabled account, success.
Rules: generic authentication failure message; rate-limit attempts.

### S-04 Verification
Route: `/accounts/verify/`
Actions: submit code, resend code.
States: pending, verified, expired, invalid, rate-limited.
Rules: OTP is short-lived, single-use, stored hashed where feasible, never logged.
Google-created pending email accounts use the verified provider email automatically. After the user accepts the existing terms/privacy signup form and the account is created, the existing verification service sends one email code and redirects directly to this form; only the six-digit code needs entry. The email identifier is session-bound and is not editable in this flow. Refreshing the form does not request another code. A live unexpired challenge is reused on OAuth callback retries.

### S-05 Dashboard
Route: No separate dashboard route is currently mounted; `/app/` is the Find Donor page.
Shows: own request summary, incoming contact requests (for donors), outgoing requests (for recipients), donor availability.
Actions: create request, search donors, update availability.
Empty state: explain how to start.
Rules: dashboard data scoped to authenticated user.

### S-06 Donor profile editor
Route: `/app/donor-profile/`
Fields: required blood group, optional donor-selected general donation area and source, separate consent for private area storage, availability, preferred contact channels, last donation date (optional self-reported), visibility consent.
Actions: Search/select a place, adjust and confirm a map pin, save, change or clear the selected area, pause donor profile, deactivate.
States: no area selected, map/place lookup loading or unavailable, no general label found, confirmation required, storage consent declined/withdrawn, unsaved changes, validation error, save success.
Rules: explain that profile data and location are self-reported, not independently verified and not medical clearance. Save only a general-area label and selected point after explicit confirmation and separate `donor_area_storage` consent. Do not request browser GPS or store an exact street address. The browser sends the donor's place query and selected pin coordinates directly to Google Maps Platform for the requested map/geocoding operation. The point, Place ID and source remain private and are not used in donor search; map-only profiles remain undiscoverable under the current administrative search rules. The owner may clear the selection to withdraw storage consent and remove its metadata. Deactivation continues to exclude the donor under existing visibility/availability rules.

### S-07 Donor search
Route: `/app/`
Controls: accessible clickable single-select blood-group buttons (preserve an “Any blood group” choice unless made mandatory); required location search and confirmation; optional radius of 5, 10, 20 or 50 km; available donors by default; optional hospital/place lookup as another way to select the search center; collapsed advanced administrative filters.
Current location-first UI:
1. The page always renders an editable address/area/hospital input and a “Search address” action. With the development browser key loaded, Places API (New) suggestions appear; selecting one resolves its place and moves the map pin. A manually typed address can be resolved with Geocoding. If Google is unavailable, the input remains usable and reports that lookup cannot run.
2. The user may explicitly request browser location or click/drag the single map pin. Browser geolocation is requested only after the user action and does not require Google. GPS and changed pin positions are reverse-geocoded for a readable label when possible.
3. The selected point stays in JavaScript memory. “Confirm location” confirms the selection locally; it does not submit coordinates to BloodConnect or search nearby donors.
4. Hospital/place names use the same address input. Selecting a Places suggestion makes it the candidate location, which remains unconfirmed until the user presses “Confirm location”; Places does not verify facility services or blood availability.
5. Nearby matching is not available; confirming a location or selecting a radius does not search donors or submit either value. The existing administrative GET endpoint remains the only result-producing search.

Future matching flow, pending P12-02 backend approvals:
1. Submit confirmed requester coordinates and approved filters in a POST body, never a URL; validate against the reviewed Bangladesh boundary and do not persist or log coordinates.
2. Use PostGIS against donor-confirmed points for radius eligibility. Administrative-only donors are not radius-qualified.
3. If clearly separated, area-only donors may appear under “Area matches — distance not verified,” with no distance/radius claim. Otherwise omit them. Public distance bands are approximate straight-line only; never return donor coordinates or exact address.
Actions: Search, clear, open donor public card, request contact, expand advanced filters.
States: location not selected, confirmation required, browser permission denied/unavailable, map or provider unavailable, loading, no matches, invalid filters, rate-limited, service error.
Radius-qualified result card may show: display name or chosen public alias, blood group, generalized area, one coarse approximate straight-line distance band, availability, platform verification badge with explicit meaning. The separate “Area matches — distance not verified” card shows no distance.
Must not show: phone, email, exact address, donor coordinates, identity documents, private notes, or the user's search coordinates.
Safety copy: "Results are potential contacts only. Approximate location and distance do not establish medical suitability or compatibility. An authorized healthcare professional must assess those decisions."
Provider status: `/app/` and `/location-demo/` share the browser-side Google Maps/Places picker when the development browser key is configured. This UI use does not approve Google as the production/matching provider. Review current terms, costs and data-sharing requirements before production use. Nearby matching and omitted-radius behavior remain unimplemented product decisions.

### S-08 Donor public profile
Route: `/app/donors/{public_id}/`
Shows only consented public fields.
Actions: Request contact, report profile, block user.
States: profile hidden, unavailable, not found, contact already pending.
Rules: use UUID/public identifier; do not disclose internal database IDs.

### S-09 Create blood request
Route: `/app/requests/new/`
Fields: requested blood-group label, units (integer, informational only), required date/time, confirmed general request area, optional facility name/address text, urgency, description. The area picker uses Places API (New) and an adjustable map pin; facility details remain separate from the selected map area. Replies are coordinated in app only; requester phone/email are not shared through a blood request.
Actions: Search/select a place, adjust the pin, explicitly confirm or clear the request area, publish request, save draft, cancel.
States: no area selected, Places/map unavailable, suggestions/details failure, confirmation required, validation error, success.
Rules: do not request GPS or use Geocoding. Save the selected point only after explicit confirmation and set its timestamp on the server. Keep coordinates and Place ID private; public request listings may show only the general-area label. Preserve legacy administrative areas as a fallback. Do not treat Places components as official Bangladesh records, a pin as a verified street address, or a facility name as proof of affiliation. No medical recommendation, blood inventory claim or guarantee of response.

### S-10 Request details
Route: `/app/requests/{public_id}/`
Shows: request details, status, the selected general-area label or legacy administrative location, owner-visible facility text and contact request summary. Do not display coordinates or Place ID.
Actions: edit, cancel, close/mark outcome, report.
Rules: only owner and authorized moderators can see private request fields. Public listing, if enabled, uses minimized fields.

### S-11 Contact request composer
Route: `/app/contact-requests/new/?donor={public_id}&request={public_id}`
Fields: short message, selected active blood request.
Actions: Send request, cancel.
States: sending, duplicate pending, donor unavailable, request closed, rate limited.
Rules: do not include or expose private recipient/donor data unnecessarily.

### S-12 Incoming contact requests
Route: `/app/contact-requests/incoming/`
Actions: View, accept, decline, report.
States: pending, accepted, declined, expired, cancelled.
Rules: donor can decide only on requests addressed to them. Accept action must be atomic and idempotent.

### S-13 Outgoing contact requests
Route: `/app/contact-requests/outgoing/`
Actions: view status, cancel pending request, report.
Rules: no private donor contact until accepted.

### S-14 Accepted connection detail
Route: `/app/connections/{public_id}/`
Shows: contact channels the donor explicitly chose to share, request context and status.
Actions: copy/contact, mark coordination outcome, report/block.
Rules: accepted contact does not mean donation occurred or donor is medically eligible. Do not expose more than consented fields.

### S-15 Notifications
Route: `/app/notifications/`
Actions: open related resource, mark read, notification preferences.
States: empty, loading, failed.
Rules: notification preview must not contain sensitive health details or private contact fields.

### S-16 Profile and privacy settings
Route: `/app/profile/`
Actions: edit account details, change password, manage visibility/consent, request account deletion.
Rules: re-authenticate for sensitive changes; provide confirmation and clear consequences.

### S-17 Report and block
Route: `/app/report/`
Fields: reason, description, optional evidence subject to file rules.
Actions: submit report, block user.
Rules: protect reporter identity; prevent abuse of reporting; do not promise immediate emergency response.

### S-18 Admin moderation
Route: protected admin area.
Actions: review reports, suspend accounts, hide content, record resolution, review audit events.
Rules: least privilege, reason required, immutable audit event. Admin cannot certify clinical eligibility.

### S-19 Organization directory (future)
Route: `/organizations/`
Shows only reviewed public information. Organization verification means identity/authorization review only, not confirmation of real-time blood stock.

## 4. State machine: donor contact request

```text
DRAFT
  | recipient submits
  v
PENDING
  | donor accepts       | donor declines       | recipient cancels
  v                     v                      v
ACCEPTED              DECLINED               CANCELLED
  | time limit / request closure
  v
EXPIRED (only from eligible prior states)

Rules:
- Only addressed donor can accept/decline.
- Only recipient can cancel their pending request.
- Repeated commands are idempotent.
- ACCEPTED reveals only donor-consented contact channels.
- No transition may reopen a terminal state.
- State transition and audit event occur in one database transaction.
```

## 5. State machine: blood request

```text
DRAFT -> OPEN -> FULFILLED
          |  \-> CANCELLED
          \----> EXPIRED

Only owner may edit/cancel according to state policy.
A donor response does not automatically set a request to FULFILLED.
Fulfilled is a requester-reported coordination outcome, not clinical verification.
```

## 6. Navigation and access rules

- Unauthenticated users visiting private routes go to login with a safe local return path.
- Authenticated users cannot access another user's private dashboard by changing a URL.
- A missing and unauthorized private resource may both return a non-disclosing not-found response.
- Back navigation must not resubmit a state-changing POST.
- All state changes use POST/PATCH/DELETE as appropriate, never GET.
- Destructive actions require confirmation.
- Forms preserve safe non-sensitive values after validation errors.
