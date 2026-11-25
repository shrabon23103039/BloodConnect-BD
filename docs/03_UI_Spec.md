# 03 — UI Specification and Design System

**Version:** 1.0  
**Design direction:** Professional healthcare coordination product; calm, trustworthy, accessible; mobile-first.

## Google sign-in and account access

Registration and sign-in show an accessible, full-width “Continue with Google” action when backend Google OAuth is configured. The action uses a CSRF-protected POST. When configuration is absent it is disabled with an explanation and local email/phone access remains available. Submit announces the connection state to assistive technology and prevents duplicate submits. Cancellation and provider errors return generic messages. Signed-in users can explicitly link Google from Account access only while ACTIVE; no unlink action is offered. A new Google account still requires the existing Terms of Service and Privacy Notice consent. After account creation, its Google-verified email is used to request one BloodConnect email-verification challenge automatically. The browser goes directly to `/accounts/verify/` with the email held in the session and only the six-digit code as user input. GET/refresh does not send another code, and OAuth callback retries reuse a live challenge. Google verification alone never activates the BloodConnect account.

## 1. Brand principles

- Clear and reassuring, not alarmist.
- Red is an accent for blood-related actions, not a full-page background.
- Use plain language and explain platform limitations.
- Avoid clinical imagery that implies medical authority.
- Never use a "medically verified donor" visual label.

## 2. Color tokens

### Light theme

| Token | Hex | Use |
|---|---|---|
| `color-primary-700` | `#9F1D20` | Primary brand/action |
| `color-primary-600` | `#B4232A` | Primary button |
| `color-primary-100` | `#FDEBEC` | Soft brand background |
| `color-navy-900` | `#172B4D` | Headings |
| `color-text` | `#253247` | Main text |
| `color-muted` | `#667085` | Secondary text |
| `color-surface` | `#FFFFFF` | Cards/panels |
| `color-page` | `#F7F8FA` | Page background |
| `color-border` | `#E4E7EC` | Borders |
| `color-success` | `#067647` | Success |
| `color-warning` | `#B54708` | Warning |
| `color-danger` | `#B42318` | Error/destructive |
| `color-info` | `#175CD3` | Informational |

### Dark theme

| Token | Hex | Use |
|---|---|---|
| `dark-page` | `#101828` | Page background |
| `dark-surface` | `#1D2939` | Cards/panels |
| `dark-surface-raised` | `#344054` | Raised controls |
| `dark-text` | `#F2F4F7` | Main text |
| `dark-muted` | `#D0D5DD` | Secondary text |
| `dark-border` | `#475467` | Borders |
| `dark-primary` | `#F97076` | Primary action |
| `dark-success` | `#6CE9A6` | Success |
| `dark-warning` | `#FEC84B` | Warning |
| `dark-danger` | `#FDA29B` | Error |

Use semantic CSS variables. Do not hardcode colors inside individual components.

## 3. Typography

- Primary Latin font: Inter.
- Bengali font: Noto Sans Bengali.
- Fallback: system UI, sans-serif.
- Body: 16px / 1.5 line height.
- Small text: 14px / 1.45.
- Caption: 12px / 1.4; never use for essential instructions.
- H1: 32px desktop / 28px mobile.
- H2: 24px.
- H3: 20px.
- H4: 18px.
- Button: 14–16px, weight 600.
- Minimum readable text size: 12px, with 14px preferred.

## 4. Spacing and layout

Use a 4px base spacing scale:
- `space-1`: 4px
- `space-2`: 8px
- `space-3`: 12px
- `space-4`: 16px
- `space-5`: 20px
- `space-6`: 24px
- `space-8`: 32px
- `space-10`: 40px
- `space-12`: 48px
- `space-16`: 64px

Layout:
- Content max width: 1200px.
- Main reading width: 760px.
- Card radius: 12px.
- Button radius: 8px.
- Input height: 44px minimum.
- Tap target: 44×44px minimum.
- Desktop sidebar: 256px.
- Mobile navigation: compact top bar + bottom navigation for primary actions where useful.
- Use 12-column grid on desktop; single-column default on mobile.

## 5. Responsive breakpoints

Bootstrap 5 defaults:
- xs: below 576px
- sm: 576px and up
- md: 768px and up
- lg: 992px and up
- xl: 1200px and up
- xxl: 1400px and up

Test at 360px, 390px, 768px, 1024px, 1366px and 1440px widths.

## 6. Core components and states

### Buttons
- Primary: solid primary color.
- Secondary: neutral surface with border.
- Danger: destructive red.
- Text/link: no filled background.
- States: default, hover, focus-visible, active, disabled, loading.
- Loading buttons prevent duplicate submission.

### Inputs
- States: default, focus, filled, invalid, disabled, read-only.
- Always show visible label; placeholder is not a label.
- Show field-specific validation text.
- Use correct input type and autocomplete attributes.

### Cards
- Surface background, subtle border, 12px radius.
- Donor cards show only public, consented fields.
- No phone/email/exact location in donor search card.
- Verification badge text must explain what was checked.

### Badges
- `Available`: donor opted to receive contact requests; not medical eligibility.
- `Unavailable`: donor is not accepting requests.
- `Platform verified`: account/contact/organization verification only, with scope shown.
- Never use `Medically eligible`, `Safe donor` or `Compatible donor`.

### Alerts
- Success, info, warning and danger.
- Use icon + text, not color alone.
- Emergency disclaimers must not imply the platform is an emergency service.

### Tables
- Responsive overflow or card conversion on small screens.
- Clear empty states.
- Do not show sensitive data to roles without permission.

### Modals
- Use for confirmation and focused short tasks.
- Destructive actions name the affected resource.
- Keyboard focus is trapped and restored.

## 7. Page composition

### Landing page
1. Header and navigation.
2. Hero with clear value proposition.
3. Primary CTA: Find potential donors.
4. Secondary CTA: Register as donor.
5. How it works (search → contact request → donor decision).
6. Safety and privacy explanation.
7. Platform limitations.
8. Footer with privacy, terms, contact and help.

### Dashboard
1. Welcome and account status.
2. Donor availability control (if donor profile exists).
3. Request summary.
4. Incoming/outgoing contact requests.
5. Quick actions.
6. Notifications.

### Search page
1. Search heading and safety note.
2. Clickable, keyboard-operable single-select blood-group controls with a visible selected state; preserve an “Any blood group” option unless product review makes the filter mandatory.
3. A normal, editable address input with the placeholder “Search address, area, or hospital,” an accessible Places suggestion list when configured, and a “Search address” action for manual Geocoding. Selecting a suggestion or resolving typed text moves one pin and synchronizes the input. If the Google key or service is unavailable, keep the input visible and show a concise error rather than rendering an empty custom widget.
4. One “Use my current location” action uses browser geolocation after a user gesture. Move the map pin immediately and reverse-geocode a readable address when possible; state that GPS is not independently verified. A map click or pin drag moves the same pin and attempts reverse geocoding. Include one reset action and a clear “Confirm location” action. Do not request browser location on page load or require manual latitude/longitude entry.
5. Optional radius control with exactly 5, 10, 20 and 50 km choices. Available donors are selected by default. Keep the optional hospital lookup within the place input and administrative filters collapsed until expanded.
6. **After backend matching is approved:** radius-qualified results use donor-confirmed coordinates only. Display generalized area and exactly one coarse straight-line distance band: `<2 km`, `2–5 km`, `5–10 km`, `10–20 km`, `20–50 km`, `>50 km`. Bands are display-only; PostGIS applies the selected radius to the underlying point.
7. **After backend matching is approved:** if supported as a clearly separate section, show area-only candidates under the exact heading **“Area matches — distance not verified”**. Show generalized area only—no distance and no statement or visual cue that they meet the selected radius. If that distinction cannot be maintained responsively and accessibly, omit area-only candidates from radius results.
8. Pagination and accessible empty, permission-denied, provider-unavailable, validation and service-error states.

#### Responsive donor-search layout (P12-05)

- At 992px and wider, show the search controls first in two top-aligned panels: blood group at about 32–35% of the available width on the left and location at about 65–68% on the right. Let each panel keep its natural height; do not stretch the blood-group panel to match the location panel.
- Below 992px, stack the blood-group panel before the location panel. This keeps both usable at 768px while leaving donor results below the complete search area.
- Put the single administrative search action after the search panels and before donor results. Keep address lookup as the location picker’s separate provider action; do not duplicate the donor-search submit button.
- Render donor results below the search area at every width, spanning the full content width. Show the real count, existing pagination and an unboxed-or-compact full-width empty state. Do not leave a results column beside an empty search area.
- Keep donor cards in a vertical list. At 992px and wider, align the blood-group indicator, public display identity, generalized area/availability and contact action in a horizontal row. Below 992px, stack or wrap these elements without horizontal overflow; preserve a 44px minimum contact target.
- Keep the map at about 200px high on desktop, tablet and mobile. At 1200px and wider, place it beside the location actions/radius/confirmation/privacy controls when the location panel has enough width; below 1200px, stack these controls after the map. The map remains a location-selection control, not the main content. Preserve the editable input and a useful fallback if the map/provider is unavailable.
- On mobile, keep the order blood group, location, search action, results; use one column, touch-friendly controls and no sticky elements. Keep advanced administrative filters collapsed by default and preserve the current selected values when navigating to results.
- Do not fabricate donor data, availability, distances, sorting, location success or nearby matching. Continue using the current consent-filtered administrative GET search until a separately approved backend implementation exists.

#### Final donor-discovery search-first refinement (P12-06)

- Use a cohesive two-panel desktop search area: blood group/quick search scope at approximately 36–38% and location at approximately 62–64%. Both panels align at the top and share the same visual padding and radius.
- Make the blood-group panel feel complete, not undersized. Use a balanced 3-column chip grid on desktop/tablet and a naturally wrapping grid on mobile. Keep the existing “Any” behavior and all eight blood-group choices; show only genuinely supported scope text, such as “Available donors only,” which is also the default backend filter.
- Do not add Rh-only, “available now,” verified-donor, donation-date or other unsupported quick filters. The existing availability choice remains available only in advanced filters and must not imply medical eligibility.
- Keep the location panel compact: at 1200px and wider, place the 180–220px map beside its GPS/reset/radius/confirmation controls; below 1200px, stack the map and controls. Preserve the editable address input, Places/geocoding behavior, pin synchronization, reset, confirmation and provider fallback.
- Put the collapsed advanced administrative filters in the location workflow, then place one search action after both panels and before full-width donor results. The mobile DOM/order remains blood group, location, search action and results.
- Keep the single full-width results heading/count/empty state below the search area. Empty results must explain that no records matched and provide a real clear-search action. Cards remain readable horizontal rows at wide widths and stack below 992px.
- Preserve GET parameters and privacy boundaries; requester coordinates stay client-only and are never persisted or submitted by the search action.

#### Production donor-discovery refinement (P12-07)

- Keep the page introduction compact: one small eyebrow, “Find potential donors,” one concise workflow sentence and one short medical/contact disclaimer. Do not repeat nearby-matching or privacy details in large paragraphs above the form.
- Keep two coordinated panels above the results. Use approximately 35–40% for blood-group controls and 60–65% for location. Align panel headings and padding, but do not force equal card heights solely to match the other panel.
- Make the blood panel complete and readable: all existing choices, visible selected state, 3-column natural chip grid on desktop/tablet and a wrapping 3-column grid on small mobile screens. Use only supported text such as available-donor scope; do not add unsupported verification or medical filters.
- Keep the location workflow compact: a 180–220px responsive map secondary to the editable address input and provider actions. Combine GPS/reset/radius/confirmation in one organized control block and keep advanced administrative filters collapsed.
- Place exactly one primary “Search donors” submit button in a connected action row directly below both panels. Preserve the secondary clear/reset action and existing GET parameter names. Do not submit requester coordinates or radius.
- Show “Available donors” as a full-width, prominent results heading with an actual count. Keep cards horizontal at wide widths and stacked below 992px. Keep exact addresses and private coordinates out of public markup.
- Use a compact empty state with a clear no-match explanation, a change-filters instruction and a clear-search action. Do not enlarge the card or imply nearby matching.
- Practical type targets: 28–36px desktop H1, 20–24px section headings, 16–20px card headings, 14–16px body copy and 12–14px helper copy. Preserve platform-required tiny map attribution only.
- At 768px and below, stack blood, location, search action and results. At 1024px and wider, keep two panels side by side only where both remain usable. Do not create sticky controls or horizontal overflow.

#### Approved rendered-layout correction (P12-08)

- Left search panel: at desktop, occupy approximately 35–40% of the search row and contain both blood-group chips and the existing administrative/availability filter controls. Its height is natural—no fixed height or decorative spacer.
- Move the existing `<details class="donor-search__advanced">` block out of the location card and into the blood-group card. Preserve its collapsed default, submitted field names and validation behavior.
- At desktop and tablet, administrative fields use compact readable rows in the left panel. Do not squeeze them into the narrow location/map workflow.
- Right location panel: occupy approximately 60–65%, use a vertical workflow, and never put the map in a narrow side column. Order address input/action, full-width 160–210px map, GPS/reset actions, radius, confirm action, and concise privacy helper copy.
- Keep exactly one primary “Search donors” action immediately below the paired panels, with a balanced width and the existing “Clear filters” secondary action. It remains within the GET form and submits no latitude, longitude, radius or hospital parameter.
- Preserve full-width results below the form, a prominent count and heading, horizontal donor cards at wide widths, compact empty state and privacy boundaries.

#### Approved two-column donor-discovery dashboard (P12-09)

- Replace the previous top-two-card layout with a desktop dashboard: approximately 40% left column and 60% right map column.
- The left column is a single workflow containing compact heading/copy, one search card, a direct donor-results section and pagination.
- The left search card contains blood chips, the existing address input/action, current-location/reset controls, radius choices, collapsed administrative filters, one “Search donors” submit and the clear action.
- The right column is a large, independent map dashboard. It is not nested inside the search card and uses a sticky/viewport-aware desktop height where practical.
- Desktop: search and results remain left, with the map spanning the same dashboard height on the right. Tablet below 1100px: stack search, map and results only when the two columns become cramped. Mobile: search, map, then results; alternatively results may follow the map. No sticky element covers content.
- Preserve selected radius as a visual Google Maps circle only when a client-side candidate point exists. Clearly label it as a radius preview that does not filter or claim nearby donor matches; do not add fake markers or invent distances.
- Preserve horizontal/stacked donor cards, compact empty state, private public fields and existing GET parameters. Never submit requester coordinates or persist them.

#### Registration page and identifier contract (P12-10)

- Accounts require exactly one login identifier: one email **or** one Bangladesh/general E.164 phone. They do not support both identifiers on one account.
- Registration starts with an Email/Phone selector. Email mode shows and submits only `email`; Phone mode shows and submits only `phone_e164`. The inactive identifier is disabled/omitted from submission.
- Preserve the existing backend field names and exactly-one/normalization rules. Valid email or normalized phone input must not trigger a missing-identifier error.
- Place field errors beside their inputs. Use a concise, non-sensitive summary only when several fields fail. Duplicate identifiers remain generic to avoid enumeration.
- New accounts remain PENDING. A successful registration is “Account created — verification required,” and the submitted identifier determines the email or phone verification step.
- Password fields use at least 44px targets, show/hide controls preserve password value and focus, strength follows Django's existing validators, and confirmation provides match feedback plus server-authoritative mismatch errors.
- Terms and Privacy acknowledgements remain required and remain beside accessible checkbox labels.
- Submit once: show “Creating account…” with a spinner, disable duplicate submission, and show success animation only after a successful redirected response. Reduced motion disables movement.

Current `/app/` status: the simplified picker uses a plain editable input; Places API (New) suggestions and Geocoding initialize only after the Google Maps script callback and required libraries are available. The map, GPS, place selection, typed-address resolution and pin all update one client-side point. Selecting a hospital/place suggestion makes it the candidate point, but it is not confirmed until the user presses “Confirm location”; Places does not verify a facility. Nearby matching is not implemented; confirmation does not submit or search, and the radius is not applied. Requester coordinates stay in JavaScript memory and are not submitted to the administrative GET form, placed in the URL, stored or logged. Google/provider failure leaves the address field and administrative search usable. Direct Django commands do not load `.env`; export `GOOGLE_MAPS_BROWSER_API_KEY` into the process, while Compose forwards its `.env` value. This does not select a production/matching provider.

Future matching privacy requirements: validate the requester point against a reviewed, approved Bangladesh boundary and submit it only in a POST body. Never expose it in the URL, page markup, result payload, browser storage, database records, analytics or logs, and do not persist it. Never render donor-specific coordinates or exact addresses. State that eventual distance bands are approximate straight-line distance, not road/travel distance. Provide a provider-neutral failure state and an alternative map/tile-provider path. Boundary source, license, version and import/use approval must be reviewed before implementation; do not use a hand-written bounding box.

### Donor profile editor — discovery location

- Replace unavailable administrative dropdowns in the profile form with a compact Google Maps area picker; keep the existing administrative fields in the model for legacy and other workflows.
- Search by city, district, area or nearby landmark; select a place, adjust/click the pin, and explicitly confirm before saving. Do not request browser geolocation.
- Show the selected general-area label. Require separate `donor_area_storage` consent before storing the private selected point, label, optional Place ID, source and server-set confirmation time. Explain that coordinates are not shared or used in donor search, and the point is not independently verified or assumed to be a home location. Disclose that the browser sends the donor's place query and selected pin coordinates directly to Google Maps Platform for the requested map/geocoding operation.
- Let the donor change or clear the saved area. Clearing removes all area metadata and records withdrawal of the storage consent. Do not display exact coordinates or Place IDs in public profiles, search results, admin exports, logs or errors. Map-only profiles remain outside current donor discovery; this picker does not implement matching.

### Blood request creation — selected request area

- Replace the unavailable division/district/upazila dropdowns with a compact Places API (New) search and map. Search for a hospital, blood bank, landmark, city or general area; selecting a suggestion uses Place Details to center the map and marker.
- Let the requester adjust the pin and explicitly confirm the selected area before publishing. Do not request browser GPS, call Geocoding, or describe an adjusted pin as a verified street address. Show useful loading, no-results, provider-error and confirmation states.
- Save a general-area label, selected coordinates, optional Place ID, source and server-set confirmation time. Keep facility name and facility address as separate optional user-entered details with clear help text.
- Preserve existing administrative request locations as a legacy fallback. A newly confirmed map area replaces the administrative references only for that request; clearing a map area must not make an otherwise locationless request publishable.
- Request detail and donor-facing public listing/API may show the general-area label, but never coordinates or Place ID. Public API fields for facility address and description remain excluded. Do not treat Places components as official Bangladesh records or imply facility affiliation.

## 8. Accessibility

Target WCAG 2.2 AA:
- Text contrast at least 4.5:1 for normal text and 3:1 for large text.
- Keyboard access to all controls.
- Visible focus indicator.
- Semantic heading order and landmarks.
- Labels and accessible error association.
- Do not communicate state by color alone.
- Respect reduced-motion preference.
- Alt text for meaningful images; decorative images have empty alt.
- Screen-reader announcement for async success/error.

## 9. Dark/light theme rules

- Default to system preference.
- Allow user override: light, dark, system.
- Persist preference in user setting/local preference; do not store sensitive information in local storage.
- Use semantic tokens for every component.
- Check contrast in both themes.
- Avoid pure black backgrounds and low-contrast muted text.

## 10. Content and tone

- Use simple English with optional Bengali localization later.
- Use respectful, non-alarming language.
- Say "potential donor" rather than "compatible donor".
- Say "contact request accepted" rather than "blood confirmed".
- Explain that a donor's availability is self-reported.
- Never promise response time or blood availability.
