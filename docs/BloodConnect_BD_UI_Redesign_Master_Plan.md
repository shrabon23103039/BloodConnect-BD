# BloodConnect BD — UI Redesign, Audit & QA Master Plan

## 1. Goal

Improve the BloodConnect BD website into a polished, modern, high-quality product while preserving the existing application functionality.

The redesign must be **safe and incremental**.

### Core rule

> UI/UX improvement first. Do not unnecessarily change backend logic.

Do not change without a clear technical reason:
- Django views
- Models/database
- URLs/routes
- Authentication/session behavior
- Google OAuth
- CSRF/security behavior
- Donor search/business logic
- Map functionality
- Blood request logic
- Contact-request logic
- Notification logic
- Permissions

---

# 2. Working Method

We will redesign the website **one page at a time**.

For every page:

1. Inspect the existing implementation.
2. Inspect the current rendered page.
3. Define the target visual design.
4. Implement only that page.
5. Test existing functionality.
6. Test desktop and mobile.
7. Fix visual issues.
8. Approve the page.
9. Move to the next page.

Do NOT redesign every page in one large risky change.

---

# 3. Development Access / VS Code Agent

If the coding agent needs to see authenticated pages, provide it with a safe way to access the application.

## Preferred approach

Create/use a **dedicated development/test account**.

Do NOT give an AI coding agent:
- production passwords
- production database credentials
- API secrets
- OAuth client secrets
- payment credentials
- private production tokens

The agent should work against the local/development environment whenever possible.

## What the agent may need to access

### Public pages
- Landing page
- Sign in
- Create account
- Password reset
- Verification

### Authenticated pages
- Dashboard
- Find donors
- Donor profile
- Blood requests
- Contact requests
- Notifications
- Privacy settings
- Account access
- Help & safety

If the authenticated UI cannot be inspected without login, use a dedicated test account with representative development data.

---

# 4. Current Design Direction

The dashboard reference establishes the overall visual language.

## Brand

- Deep burgundy / blood red primary
- White content surfaces
- Soft warm-gray page background
- Soft blush/pink supporting surfaces
- Subtle red accents

## Visual style

- Modern SaaS/health-tech aesthetic
- Professional and trustworthy
- Rounded cards, approximately 14–20px where appropriate
- Soft shadows
- Strong visual hierarchy
- Generous whitespace
- Clean icon system
- Minimal decorative elements
- No excessive gradients
- No excessive glassmorphism
- No generic Bootstrap appearance

The product should feel like **one coherent platform**, not a collection of unrelated pages.

---

# 5. Typography System

Typography is a major audit priority.

The website must not look like an AI-generated website with tiny text and excessive information density.

Use a consistent type scale.

Suggested starting point:

| Element | Desktop | Mobile |
|---|---:|---:|
| Page title | 32–40px | 26–30px |
| Section heading | 22–26px | 19–22px |
| Card heading | 17–20px | 16–19px |
| Body text | 15–17px | 15–16px |
| Secondary text | 14–15px | 14px |
| Labels | 13–14px | 13–14px |
| Buttons | 14–16px | 14–16px |
| Navigation | 14–16px | 14–16px |

These are starting values, not rigid requirements.

### Typography audit

For every page check:

- Is the main heading immediately visible?
- Is body text comfortably readable?
- Is secondary text actually secondary?
- Are labels readable?
- Are helper texts too small?
- Is there too much text?
- Can copy be shortened without losing meaning?
- Are line heights comfortable?
- Are headings and body text visually distinct?

Do not remove important safety, privacy, legal, or accessibility information just to reduce text.

---

# 6. Content / Copy Principle

Use concise UI copy.

Avoid:

> Long paragraphs explaining something that could be communicated in one short sentence.

Prefer:

> Clear heading

> One short supporting sentence

> Clear action

Example:

### Avoid

"Please provide all of the necessary information below so that other potential donors in your surrounding area can discover your profile and potentially contact you when they require assistance."

### Prefer

"Set up your profile so potential donors can find and contact you."

---

# 7. Shared Design System

Create/reuse a single design system across the application.

## Components

- Header
- Sidebar
- Mobile navigation
- Footer
- Buttons
- Inputs
- Selects
- Checkboxes
- Radio controls
- Cards
- Stat cards
- Alerts
- Badges
- Tabs
- Modals
- Empty states
- Loading states
- Error states
- Search/filter controls
- Donor cards
- Request cards
- Notification items
- Map panels

Do not invent a new visual style for every page.

---

# 8. Page-by-Page Redesign Order

## Phase A — Authenticated application

### 01. Dashboard
Reference style is already established.

Audit:
- sidebar
- header
- hero
- statistics
- recent requests
- safety reminder
- responsive behavior

### 02. Find Donors
Preserve:
- search
- filters
- map
- list/map switching
- donor results
- existing donor logic

### 03. Donor Profile
Preserve:
- profile fields
- location functionality
- map/location behavior
- save/update behavior

Reduce visual density and improve hierarchy.

### 04. Blood Requests
Improve:
- tabs
- request cards
- status badges
- empty states
- action hierarchy

### 05. Create Blood Request
Improve:
- form hierarchy
- labels
- spacing
- field grouping
- primary/secondary actions

### 06. Contact Requests
Improve:
- incoming/outgoing request presentation
- status
- consent messaging
- actions

### 07. Notifications
Improve:
- unread state
- notification hierarchy
- timestamps
- empty state

### 08. Privacy Settings
Improve:
- setting groups
- toggles
- descriptions
- save actions

### 09. Account Access
Improve:
- account information
- verification states
- security actions
- danger zone

### 10. Help & Safety
Improve:
- guidance hierarchy
- safety information
- support actions

---

## Phase B — Public/Auth pages

### 11. Landing / Home
Improve:
- hero
- value proposition
- how-it-works
- safety
- privacy/trust
- CTA hierarchy

### 12. Sign In
Improve:
- authentication card
- Google sign-in
- email/phone form
- password actions
- supporting links

### 13. Create Account
Improve:
- registration form
- password feedback
- verification information
- terms/privacy acknowledgements

---

# 9. Responsive Audit

Every approved page must be tested at:

- 320px
- 375px
- 390px
- 414px
- 480px
- 768px
- 1024px
- 1280px
- 1366px
- 1440px
- 1920px

Check:

- No horizontal overflow
- No clipped text
- No overlapping elements
- No broken cards
- No broken forms
- No unusably small buttons
- No unusably small text
- Sidebar/mobile navigation works
- Maps remain usable
- Tables/lists remain usable
- Modals fit the viewport

---

# 10. Accessibility Audit

Check:

- Semantic HTML
- Keyboard navigation
- Visible focus states
- Labels associated with controls
- Button/link semantics
- Accessible navigation
- Appropriate ARIA
- Color contrast
- Error messaging
- Form validation feedback
- Mobile navigation accessibility
- Modal/dialog accessibility

Do not remove existing accessibility features during redesign.

---

# 11. Visual Consistency Audit

After all individual pages are redesigned, perform a global audit.

Check:

### Typography
- Same font family
- Same type scale
- Same heading hierarchy
- Same line-height principles

### Spacing
- Consistent page padding
- Consistent section spacing
- Consistent card padding
- Consistent form spacing

### Components
- Same button styles
- Same input styles
- Same card radius
- Same shadows
- Same status badges
- Same icon treatment

### Colors
- Consistent brand red
- Consistent background
- Consistent text colors
- Consistent borders
- Consistent success/warning/error colors

---

# 12. "AI Website Smell" Audit

Specifically search for:

- Tiny typography
- Too much text
- Too many cards
- Too many borders
- Too many icons
- Excessive rounded containers
- Excessive gradients
- Excessive empty space
- Cramped sections
- Random font sizes
- Random colors
- Inconsistent spacing
- Generic Bootstrap appearance
- Repeated information
- Weak primary CTA
- Unnecessary helper text

Fix these instead of merely reporting them.

---

# 13. Functional Regression Testing

After each page redesign verify existing behavior.

### Authentication
- Google sign in
- Google sign up
- Email login
- Phone login
- Password visibility
- Password reset
- Verification

### Dashboard
- Navigation
- Statistics
- Create request
- Request list
- Notifications

### Donors
- Search
- Blood group filtering
- Location
- Radius
- Administrative filters
- List/map switching
- Map
- Donor profile

### Requests
- Create
- View
- Manage
- Incoming contact
- Outgoing contact
- Status

### Account
- Privacy
- Account access
- Help/safety
- Logout

---

# 14. Audit Report Format

At the end, produce a concise report:

## Pages audited
13

## Issues found

| Category | Found | Fixed |
|---|---:|---:|
| Typography | — | — |
| Spacing | — | — |
| Layout | — | — |
| Components | — | — |
| Responsive | — | — |
| Accessibility | — | — |
| Copy density | — | — |
| Visual consistency | — | — |

## Functional regression

| Area | Status |
|---|---|
| Authentication | PASS/FAIL |
| Dashboard | PASS/FAIL |
| Donor search | PASS/FAIL |
| Map | PASS/FAIL |
| Requests | PASS/FAIL |
| Contact requests | PASS/FAIL |
| Notifications | PASS/FAIL |
| Settings | PASS/FAIL |
| Logout | PASS/FAIL |

## Final rules

- Backend changed: YES/NO
- Routes changed: YES/NO
- Database changed: YES/NO
- Existing functionality preserved: YES/NO
- Responsive audit completed: YES/NO
- Accessibility audit completed: YES/NO

---

# 15. Definition of Done

The redesign is complete only when:

- All target pages use one design language.
- Typography is readable and consistent.
- UI copy is concise.
- Pages are not unnecessarily text-heavy.
- Desktop layouts are polished.
- Mobile layouts are polished.
- No horizontal overflow exists.
- Existing functionality still works.
- Maps still work.
- Authentication still works.
- Forms still work.
- Navigation still works.
- Accessibility has been checked.
- Visual inconsistencies have been fixed.
- Final regression testing passes.

## Most important principle

> Make BloodConnect BD look significantly more polished without turning the redesign into a risky rewrite of the application.
