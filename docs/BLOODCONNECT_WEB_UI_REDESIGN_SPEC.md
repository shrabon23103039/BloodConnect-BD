# BloodConnect BD --- Web UI Redesign Specification

## 1. Purpose

This document is the visual source of truth for the **public-facing
BloodConnect BD website and authentication flows**.

It is based on the supplied screenshots of the current implementation:

-   Public landing/home page
-   Sign in page
-   Create account page
-   Registration-submitted / verification-request page
-   Verification-code request page

The goal is not to redesign each page independently. The goal is to make
every public/auth page feel like **one polished BloodConnect BD
product**.

The implementation must preserve the existing Django routes, forms,
authentication logic, OAuth behavior, validation, CSRF, session
behavior, verification flow, and backend functionality unless a change
is absolutely necessary.

------------------------------------------------------------------------

# 2. Core Design Diagnosis

The current public pages are already moving toward a strong BloodConnect
BD visual identity, but several screens still feel like separate
templates.

The most important consistency problems to eliminate:

1.  Header proportions and spacing vary between pages.
2.  Public pages and verification pages can fall back to a much more
    generic/plain layout.
3.  Authentication pages must share one visual system rather than
    looking like separate forms.
4.  Google OAuth must be consistently visible where the existing flow
    supports it.
5.  Verification and post-registration pages need the same polished
    card, typography, spacing, button, footer, and navigation treatment
    as sign-in/sign-up.
6.  Brand treatment must remain consistent:
    -   BloodConnect BD
    -   deep burgundy/red
    -   dark navy text
    -   soft blush/pink surfaces
    -   white cards
    -   thin warm borders
7.  Illustrations must feel like one illustration family.
8.  Buttons, inputs, links, labels, alerts, dividers and cards must use
    the same component rules.
9.  Public pages must not visually resemble an unstyled Django/Bootstrap
    fallback.
10. Mobile behavior must be designed as part of the system, not patched
    later.

------------------------------------------------------------------------

# 3. Product Visual Direction

## Brand personality

BloodConnect BD should feel:

-   trustworthy
-   community-driven
-   calm
-   human
-   modern
-   privacy-conscious
-   healthcare-adjacent but NOT hospital-like
-   professional enough for a serious production platform

Avoid:

-   generic Bootstrap appearance
-   excessive gradients
-   excessive glassmorphism
-   overly clinical blue healthcare styling
-   random emoji
-   inconsistent icon families
-   giant decorative elements that compete with the form
-   overly dense forms
-   inconsistent red shades

------------------------------------------------------------------------

# 4. Global Design Tokens

Create a reusable design-token layer instead of page-specific arbitrary
values.

## Colors

Use one primary brand red/burgundy family.

Suggested semantic tokens:

-   `--bc-primary`: primary BloodConnect red
-   `--bc-primary-hover`: darker primary
-   `--bc-primary-soft`: very light red/blush
-   `--bc-primary-subtle`: soft pink surface
-   `--bc-text`: dark navy/ink
-   `--bc-text-muted`: muted slate
-   `--bc-border`: warm light gray/pink-gray
-   `--bc-surface`: white
-   `--bc-surface-soft`: warm off-white
-   `--bc-success`
-   `--bc-warning`
-   `--bc-danger`
-   `--bc-focus`

Do not introduce unrelated accent colors simply because Bootstrap
provides them.

## Typography

Use one modern sans-serif family throughout the public site.

Hierarchy:

-   Display / hero heading: bold, strong, compact
-   Page heading: bold
-   Section heading: semibold
-   Body: comfortable reading size
-   Helper text: smaller muted text
-   Labels: semibold and highly readable
-   Buttons: semibold

Do not mix typography styles between pages.

## Radius

Use a small, coherent radius scale.

Example:

-   small controls: 8--10px
-   cards: 14--18px
-   major hero cards: 18--22px
-   pills/badges: full radius

## Shadows

Use subtle elevation only.

Cards should feel lifted from the background without looking glossy.

## Borders

Prefer 1px subtle warm borders.

Avoid heavy black borders.

------------------------------------------------------------------------

# 5. Global Public Header

The header must be a shared reusable component.

## Desktop

Structure:

-   centered max-width container
-   BloodConnect BD logo on the left
-   vertical divider after brand when appropriate
-   navigation on the right
-   `How it works`
-   `Safety`
-   `Privacy`
-   `Find donors`
-   divider
-   `Sign in`
-   `Create account` primary CTA

The screenshots show the public header already approaching this
structure. Keep it, but make the exact height, padding, border, radius
and typography identical on every public page.

## Header behavior

Do not recreate the header separately inside every template with
slightly different CSS.

Create a shared template/component.

## Mobile

At approximately tablet/mobile widths:

-   collapse navigation
-   preserve logo
-   use an accessible menu button
-   menu must be keyboard accessible
-   no horizontal overflow
-   CTA remains usable

------------------------------------------------------------------------

# 6. Global Public Footer

The footer must also be shared.

Left:

-   BloodConnect BD brand
-   short disclaimer: donor discovery/contact coordination project not a
    blood bank or medical service

Center/right:

-   How it works
-   Privacy
-   Terms
-   Help and safety
-   Contact

Far right:

-   copyright

Keep footer spacing and typography identical across:

-   landing
-   sign in
-   create account
-   verification
-   reset/password-related pages
-   other public informational pages

------------------------------------------------------------------------

# 7. Landing Page

## Current direction

The current landing page already has the strongest public visual
language:

-   blush background
-   strong dark heading
-   red emphasis
-   consent-first card
-   three-step process
-   safety notice
-   clean footer

Treat this page as the **visual anchor for the entire public website**.

## Hero

Maintain the concept:

> Make it easier to reach a potential donor.

The hero should contain:

### Left

-   eyebrow/pill
-   strong headline
-   selected words highlighted in brand red
-   supporting explanation
-   primary CTA
-   secondary CTA
-   small implementation/status note

### Right

Consent-first visual card.

The card should communicate:

-   privacy
-   consent
-   donor control
-   contact details are not exposed automatically

## Hero illustration

Use one consistent BloodConnect illustration family.

The existing hand + blood-drop + Bangladesh/urban-line illustration can
remain.

Do not introduce a completely unrelated illustration style on
authentication pages.

------------------------------------------------------------------------

# 8. Landing Page --- Three-Step Section

Keep three steps:

1.  Find potential donors
2.  Request contact
3.  The donor decides

Use identical card dimensions and icon treatment.

Each card should have:

-   numbered circular marker
-   icon
-   title
-   short explanation

Do not overload the cards.

------------------------------------------------------------------------

# 9. Landing Page --- Safety Section

The safety notice should remain visually prominent but calm.

Use:

-   soft red/blush background
-   shield/safety icon
-   small eyebrow
-   strong title
-   concise explanation
-   link to full safety guidance

Important wording concept:

Search results are potential contacts, not medical advice.

Do not imply:

-   guaranteed donor availability
-   medical compatibility
-   blood inventory
-   hospital service

------------------------------------------------------------------------

# 10. Sign In Page

## Desired structure

Use the same public header and footer as the landing page.

Main area:

Two-column composition on desktop.

### Left

Brand storytelling panel:

-   small `Welcome back` badge
-   heading: `Sign in to BloodConnect BD`
-   supporting copy
-   three compact trust/value points:
    -   Privacy first
    -   Consent-led contact
    -   Community driven
-   same BloodConnect illustration family

### Right

Authentication card.

Card contains:

-   heading `Sign in`
-   short description
-   Google OAuth button
-   divider
-   email/phone field
-   password field
-   recovery links
-   primary sign-in button
-   registration link

## Google OAuth

The Google OAuth action is a first-class authentication option.

It must not disappear due to CSS, template branching, or redesign.

Use a proper Google icon treatment.

The OAuth button must visually match the rest of the form while
remaining recognizable as Google authentication.

## Email/phone form

The field should:

-   have consistent height
-   have clear label
-   support existing backend input
-   show validation errors elegantly
-   preserve browser autofill behavior
-   preserve accessibility

Password:

-   support existing show/hide behavior
-   use an accessible button/icon
-   never break form layout

## Recovery links

Do not scatter links randomly.

Group:

-   Reset password by email
-   Reset by phone
-   Verify a pending account

Use a compact recovery row/stack with consistent spacing.

------------------------------------------------------------------------

# 11. Create Account Page

## Current strongest direction

The current screenshot with Google OAuth is the correct direction.

Desktop:

Two-column card.

### Left panel

-   `JOIN BLOODCONNECT BD`
-   `Create your account`
-   concise description
-   illustration
-   trust statements

Trust statements:

-   Privacy first
-   Consent-based

### Right panel

Registration form.

Order:

1.  Display name
2.  Google OAuth
3.  divider
4.  Email / Phone selector
5.  selected identifier field
6.  password
7.  confirm password
8.  password-strength/helper feedback
9.  terms checkbox
10. privacy checkbox
11. Create account
12. Sign in link

## Important

Do not remove Google OAuth from the create-account page.

The Google OAuth button must be rendered whenever the existing
backend/provider supports it.

Do not replace working OAuth logic with a fake button.

## Identifier toggle

Email/Phone should look like a segmented control.

Active state:

-   white surface
-   red text
-   subtle border/shadow

Inactive:

-   soft blush surface
-   dark text

The selected input should update without causing layout jumps.

## Password controls

Keep:

-   show/hide
-   password strength
-   confirm-password feedback

But style all states consistently.

------------------------------------------------------------------------

# 12. Registration Submitted Page

The current screenshot shows a plain centered card with:

`Registration request received`

This page should NOT look like a completely different website.

Redesign it as an extension of the authentication design.

Use:

-   same public header
-   same page background
-   centered auth/status card
-   same radius
-   same border
-   same shadow
-   same typography
-   same primary button

Card:

-   success/verification icon
-   eyebrow/status label
-   heading
-   concise privacy-safe explanation
-   primary `Continue to verification`
-   secondary `Return home`

The message about not revealing whether an account already exists must
remain because it is a privacy/security behavior.

------------------------------------------------------------------------

# 13. Verification Request Page

The screenshot currently shows a generic/plain layout.

This is a major redesign target.

It must use the same auth shell as Sign in and Create account.

Recommended structure:

-   shared header
-   centered or two-column auth composition depending on viewport
-   verification icon/illustration
-   heading: `Request a verification code`
-   explanatory text
-   email/phone field
-   primary `Send or resend code`
-   sign-in link
-   privacy explanation

The form should feel like a first-class BloodConnect page, not a Django
utility page.

------------------------------------------------------------------------

# 14. All Auth Utility Pages

Apply the same system to:

-   password reset by email
-   password reset by phone
-   pending account verification
-   verification code entry
-   verification success/failure
-   account recovery
-   logout-related public state
-   authentication errors

Rules:

-   same header
-   same footer
-   same background
-   same form component
-   same card
-   same button system
-   same alert/error system
-   same spacing scale

No auth utility page may fall back to browser-default-looking controls.

------------------------------------------------------------------------

# 15. Forms

Create shared public form components.

Every field should have:

1.  label
2.  input/select/control
3.  helper text when needed
4.  error state when needed

States:

-   default
-   hover
-   focus
-   filled
-   disabled
-   error
-   success

Focus must be visibly accessible.

Inputs should have consistent:

-   height
-   border
-   radius
-   font
-   padding
-   icon placement

------------------------------------------------------------------------

# 16. Buttons

Create three core variants:

### Primary

Brand red background, white text.

### Secondary

White background, brand border, brand text.

### Tertiary / text

Minimal visual weight.

All buttons:

-   same height system
-   same radius
-   same font weight
-   same hover behavior
-   disabled state
-   keyboard focus state

Do not use different red buttons with different heights on different
pages.

------------------------------------------------------------------------

# 17. Alerts and Validation

Errors must appear close to the relevant field or form.

Avoid large generic red blocks unless the error is truly global.

Use:

-   subtle background
-   icon
-   clear message
-   accessible semantics

Privacy/security messages should remain understandable without exposing
account existence.

------------------------------------------------------------------------

# 18. Responsive Requirements

Explicitly test:

-   320px
-   375px
-   390px
-   414px
-   480px
-   768px
-   1024px
-   1280px
-   1366px
-   1440px
-   1920px

At mobile:

-   two-column auth layouts become one column
-   illustration can move below/above content
-   forms remain comfortable
-   header becomes mobile navigation
-   footer stacks naturally
-   no horizontal scrolling
-   no clipped buttons
-   no tiny text
-   no overlapping cards

------------------------------------------------------------------------

# 19. Accessibility

Must preserve/improve:

-   semantic headings
-   labels
-   keyboard navigation
-   visible focus
-   accessible menu
-   accessible password toggle
-   accessible Google button
-   checkbox labels
-   error announcements
-   sufficient color contrast
-   logical tab order
-   reduced-motion friendliness

Do not use color alone to communicate errors or selected states.

------------------------------------------------------------------------

# 20. Implementation Architecture

Prefer shared Django templates/components and shared CSS variables.

Suggested structure:

-   shared public base template
-   shared header
-   shared footer
-   shared auth shell
-   shared form styles
-   shared button styles
-   shared alert styles
-   shared card styles
-   shared design tokens

Avoid page-specific CSS duplication.

Do not create five different versions of the same button.

------------------------------------------------------------------------

# 21. Non-Negotiable Functional Constraints

Do not break:

-   Google OAuth
-   email registration
-   phone registration
-   sign in
-   password reset
-   verification
-   CSRF
-   session/authentication
-   form validation
-   existing URLs
-   Django messages
-   backend privacy behavior

The redesign is primarily a presentation-layer task.

------------------------------------------------------------------------

# 22. Acceptance Criteria

The public website is complete only when:

-   Landing, sign-in, sign-up and verification pages look like one
    product.
-   Google OAuth is visible and functional where supported.
-   Verification pages no longer look like generic utility pages.
-   Header and footer are shared.
-   Typography is consistent.
-   Buttons are consistent.
-   Form controls are consistent.
-   Illustrations belong to one visual family.
-   Responsive behavior is clean.
-   Accessibility is preserved/improved.
-   No existing authentication behavior is broken.
-   No horizontal overflow exists at supported widths.
-   Browser autofill/password manager behavior still works.
