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
- Dashboard `/app/`
- Find donors `/app/donors/`
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

### S-05 Dashboard
Route: `/app/`
Shows: own request summary, incoming contact requests (for donors), outgoing requests (for recipients), donor availability.
Actions: create request, search donors, update availability.
Empty state: explain how to start.
Rules: dashboard data scoped to authenticated user.

### S-06 Donor profile editor
Route: `/app/donor-profile/`
Fields: blood group, division, district, upazila, availability, preferred contact channels, last donation date (optional self-reported), visibility consent.
Actions: Save, pause donor profile, deactivate.
States: unsaved changes, validation error, save success.
Rules: explain that profile data is self-reported and not medical clearance.

### S-07 Donor search
Route: `/app/donors/`
Filters: exact blood-group label, division, district, upazila, availability.
Actions: Search, clear filters, open donor public card, request contact.
States: loading, no matches, filters invalid, rate-limited, service error.
Result card may show: display name or chosen public alias, blood group, generalized area, availability, platform verification badge with explicit meaning.
Must not show: phone, email, exact address, precise coordinates, identity documents, private notes.
Safety copy: "Results are potential contacts only. Medical suitability and compatibility must be assessed by an authorized healthcare professional."

### S-08 Donor public profile
Route: `/app/donors/{public_id}/`
Shows only consented public fields.
Actions: Request contact, report profile, block user.
States: profile hidden, unavailable, not found, contact already pending.
Rules: use UUID/public identifier; do not disclose internal database IDs.

### S-09 Create blood request
Route: `/app/requests/new/`
Fields: requested blood-group label, units (integer, informational only), required date/time, division/district/upazila, facility name/location (free text with clear validation; no implication of affiliation), urgency, description. Replies are coordinated in app only; requester phone/email are not shared through a blood request.
Actions: Publish request, save draft if supported, cancel.
States: validation error, duplicate warning, success.
Rules: no medical recommendation, no blood inventory claim, no guarantee of response.

### S-10 Request details
Route: `/app/requests/{public_id}/`
Shows: request details, status, owner-visible contact request summary.
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
