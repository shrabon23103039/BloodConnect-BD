# BloodConnect BD --- App UI Redesign Specification

## 1. Purpose

This document is the visual source of truth for the **authenticated
BloodConnect BD application**.

It is based on the supplied screenshots of:

-   Dashboard
-   Find donors
-   Blood requests
-   Create donor profile

The objective is to make these screens feel like **one coherent
application**, not four separate websites.

The current authenticated pages already share a sidebar concept, but
differences in hero treatment, spacing, card composition, control
density, illustration usage, and page hierarchy make the product feel
inconsistent.

The implementation must preserve existing Django routes, views, forms,
donor-search logic, Google Maps behavior, contact-request logic,
notifications, profile logic, permissions, CSRF, sessions and backend
behavior.

------------------------------------------------------------------------

# 2. Primary Design Problem

The authenticated application needs one strong design system.

Current issues visible across the supplied screens include:

1.  Different hero/banner compositions.
2.  Different visual density between pages.
3.  Sidebar/header elements do not always feel like one navigation
    system.
4.  Some pages use decorative illustrations heavily while others use
    almost none.
5.  Forms have inconsistent visual hierarchy.
6.  Cards and sections have slightly different border/radius/shadow
    language.
7.  Search controls are dense and visually complex.
8.  Empty states need a stronger common pattern.
9.  Maps need to feel integrated with the product rather than embedded
    as an unrelated Google Maps block.
10. The donor profile form is much denser than the dashboard/requests
    experience.
11. Some actions compete visually with each other.
12. The product should feel premium without becoming visually heavy.

------------------------------------------------------------------------

# 3. App Design Direction

BloodConnect BD should feel like a modern community-impact SaaS product.

Visual character:

-   deep burgundy/red brand
-   dark navy text
-   white surfaces
-   soft warm-gray background
-   blush/red accent panels
-   subtle shadows
-   medium rounded corners
-   strong but restrained typography
-   clear iconography
-   generous whitespace
-   compact professional controls

Do not make every section red.

Red is for:

-   primary actions
-   active navigation
-   key emphasis
-   important status
-   brand accents

Neutral surfaces should dominate.

------------------------------------------------------------------------

# 4. Global App Layout

## Desktop

Use:

-   fixed/structured left sidebar
-   top application bar
-   scrollable main content
-   consistent max content width

### Sidebar

Keep:

Brand:

`BloodConnect BD`

Subtitle:

`Donor Coordination Platform`

Navigation groups:

### Workspace

-   Dashboard
-   Find donors
-   Requests
-   Donor profile

### Settings

-   Privacy settings
-   Account access
-   Help & safety

### Support

-   Help & safety
-   Sign out

The active item should have:

-   subtle red/burgundy background
-   white/high-contrast text
-   consistent radius
-   icon + label

Do not use different active states on different pages.

## Sidebar logo

Use one consistent BloodConnect logo/mark.

Avoid changing the logo treatment between pages.

------------------------------------------------------------------------

# 5. Top Application Bar

Use one shared top bar.

Recommended:

Left:

-   menu button on mobile
-   breadcrumb/page context

Center/large area:

-   optional global search

Right:

-   notifications
-   avatar
-   display name
-   account menu

The current dashboard screenshot has a useful global search field.

If the search is retained, make it a shared app component and keep its
placement identical across app pages.

------------------------------------------------------------------------

# 6. Mobile Navigation

At mobile widths:

-   sidebar becomes drawer/offcanvas
-   menu button remains accessible
-   drawer has same navigation hierarchy
-   active item remains visible
-   no content should be hidden behind drawer
-   Escape closes drawer
-   focus management should be accessible

------------------------------------------------------------------------

# 7. Global App Design Tokens

Use the same tokens as the public site.

Important:

The public site and authenticated app should feel like the same brand.

They can have different layout structures, but they must share:

-   colors
-   typography
-   icon style
-   radius
-   button system
-   focus style
-   border treatment
-   alert language
-   illustration family

------------------------------------------------------------------------

# 8. App Page Header Pattern

Most pages should use a common page-header pattern.

Recommended:

-   small eyebrow
-   H1
-   concise description
-   optional primary action
-   optional contextual illustration

Do not create a completely different hero design for every page.

The illustration can vary by page, but the container geometry should
remain related.

------------------------------------------------------------------------

# 9. Dashboard

## Current strengths

The current dashboard screenshot has:

-   strong welcome message
-   Find donors CTA
-   Create blood request CTA
-   three stat cards
-   recent request area
-   safety reminder

Keep this structure.

## Recommended hierarchy

### Header

`Welcome back, Shrabon.`

Supporting copy:

Help save lives by connecting with voluntary blood donors across
Bangladesh.

Actions:

-   Find donors --- primary
-   Create a blood request --- secondary

### Status notice

The current area-filter notice should be a compact informational alert.

Do not let it visually dominate the dashboard.

### KPI row

Three cards:

-   Open blood requests
-   Contact requests
-   Unread notifications

Each card:

-   icon
-   label
-   large number
-   supporting text
-   optional arrow/action

Use one consistent stat-card component.

### Recent requests

Use a large content card.

Header:

-   icon
-   title
-   subtitle
-   View all requests action

Empty state:

-   illustration/icon
-   `No blood requests yet`
-   explanation
-   Create a request CTA

### Safety reminder

Use a shared safety component across the whole app.

------------------------------------------------------------------------

# 10. Dashboard Empty States

Create one reusable empty-state pattern.

Structure:

-   soft icon/illustration
-   title
-   short explanation
-   optional action

Use it for:

-   no blood requests
-   no donors found
-   no notifications
-   no incoming requests
-   no outgoing requests
-   no profile
-   no saved preferences

Empty states must feel intentional, not like missing UI.

------------------------------------------------------------------------

# 11. Find Donors

This is one of the most important application screens.

It must remain highly functional while becoming easier to scan.

## Header

Use:

-   eyebrow `FIND DONORS`
-   H1 `Find donors`
-   concise explanation
-   safety/medical disclaimer

Avoid making the illustration dominate the page.

## Search panel

Create a structured search/filter card.

Primary row:

-   Blood group
-   Location
-   Search address
-   radius preview
-   Search donors

Secondary row:

-   More filters

Use clear grouping.

## Location controls

The existing functionality must remain.

Preserve:

-   address search
-   map/place search
-   use my location
-   reset location
-   confirm location
-   radius preview
-   administrative filters

Do not rewrite the map logic just to change the UI.

## Map

The map is a functional part of the experience.

Style the surrounding map container:

-   same border radius as app cards
-   subtle border
-   correct clipping
-   clear header/label
-   helpful status text
-   no awkward Google Maps overflow

The map itself may remain Google Maps.

Do not attempt to fake a map with CSS.

## Results

Use a results header:

-   donor count
-   explanation
-   list/map toggle
-   sort control

Donor result cards should have consistent hierarchy:

-   donor identity/name
-   blood group
-   area
-   availability
-   relevant contact/request action

Never expose private contact information before consent.

## No donors found

Use the shared empty-state component.

Message should explain:

-   broaden search
-   change blood group
-   change administrative area
-   only currently discoverable/consented profiles appear

------------------------------------------------------------------------

# 12. Find Donors --- Filter UX

Filters must not feel like a wall of controls.

Use:

-   clear labels
-   grouped fields
-   consistent spacing
-   compact controls
-   collapsible advanced filters

Primary search action should be visually dominant.

Secondary controls:

-   Reset
-   Use my location
-   Confirm location

should not compete with Search donors.

------------------------------------------------------------------------

# 13. Blood Requests

## Header

Use one standard page header:

Eyebrow:

`BLOODCONNECT BD`

H1:

`Blood requests`

Description:

Manage your blood requests and track their status.

Primary CTA:

`Create request`

The decorative header illustration can remain but should follow the same
illustration family as other app pages.

## Tabs

Current tabs:

-   My requests
-   Incoming
-   Outgoing

Keep them.

Use a shared tab component.

Active state:

-   brand red
-   clear underline or filled indicator
-   accessible selected state

Badges should use consistent small pill styling.

## Summary cards

Three summary cards:

-   My blood requests
-   Incoming requests
-   Outgoing requests

Use one reusable metric card.

## Main activity card

Header:

-   eyebrow
-   title
-   supporting description

Empty state:

-   icon
-   message
-   Create a blood request

## Safety note

Use the same safety banner as the dashboard.

------------------------------------------------------------------------

# 14. Create Donor Profile

This screenshot exposes the biggest density challenge.

The page currently contains:

-   page hero
-   Your details
-   Blood & location
-   map
-   Availability
-   Contact preference
-   Donation history
-   Quick tips

All functionality should remain, but the information architecture should
be clearer.

## Page header

Use:

-   back link
-   eyebrow
-   H1 `Create Donor Profile`
-   concise description

Do not make the header excessively tall.

## Section cards

Each major section should use the same card system.

### Your details

Fields:

-   Public profile name
-   Thana name

Helper text should be compact and clearly secondary.

### Blood & location

Fields:

-   Blood group
-   Location

Then:

-   map status
-   map
-   location instructions
-   selected-area state
-   confirm/change controls
-   privacy toggle

The map must remain functional.

### Availability

Fields:

-   Availability status
-   Show in search

Explain that availability is self-reported.

### Contact preference

Fields:

-   Preferred contact method
-   Share email after accepted request

### Donation history

Optional:

-   Last donation date

Do not visually imply medical eligibility.

------------------------------------------------------------------------

# 15. Donor Profile --- Quick Tips

The right-side `Quick tips` card is useful.

On desktop:

-   sticky/side panel is acceptable if it does not interfere with form
    scrolling.

On mobile:

-   move below the main form
-   never squeeze it beside the form

Use concise bullets:

-   use real information
-   keep availability current
-   contact details are shared only after request acceptance

------------------------------------------------------------------------

# 16. Donor Profile --- Actions

Bottom action bar:

-   Cancel
-   Save Profile

Primary Save action should be clearly dominant.

On mobile:

-   actions can stack or become a sticky bottom action area if
    implemented accessibly.

Do not let the buttons become too small.

------------------------------------------------------------------------

# 17. Forms --- App-Wide Standard

Every form must use the same system.

Fields:

-   label
-   control
-   helper text
-   validation/error

Controls:

-   input
-   select
-   textarea
-   checkbox
-   radio
-   toggle
-   date
-   segmented control

All should share:

-   height
-   padding
-   border
-   radius
-   typography
-   focus ring

------------------------------------------------------------------------

# 18. Cards

Use one card language.

Recommended:

-   white surface
-   subtle border
-   subtle shadow
-   14--18px radius
-   consistent padding

Avoid excessive nested cards.

If a section is already a card, do not put five visually identical cards
inside it without clear hierarchy.

------------------------------------------------------------------------

# 19. Illustrations

The screenshots use a distinctive BloodConnect illustration family:

-   blood drop
-   hands
-   Bangladesh/urban lines
-   donor/request imagery

Continue this family.

Rules:

-   consistent line weight
-   consistent red/blush palette
-   same visual language
-   decorative illustrations should not overpower content
-   meaningful illustrations may be used in empty states

Do not mix stock illustrations with the existing custom illustration
style.

------------------------------------------------------------------------

# 20. Icon System

Use one icon library/style throughout.

Icons should be:

-   consistent stroke weight
-   similar optical size
-   aligned with text
-   accessible when conveying meaning

Avoid random emoji icons.

------------------------------------------------------------------------

# 21. Safety and Privacy Components

Create reusable components for:

### Safety reminder

Used on:

-   dashboard
-   requests
-   donor search
-   donor profile where appropriate

### Privacy notice

Used near:

-   contact information
-   location
-   donor visibility
-   consent controls

These should share one visual language.

------------------------------------------------------------------------

# 22. Status System

Create reusable status styles.

Examples:

-   Available
-   Unavailable
-   Pending
-   Accepted
-   Declined
-   Open
-   Closed

Do not use arbitrary colors per page.

Each status must be understandable through:

-   text
-   icon where useful
-   color

Color alone must not carry meaning.

------------------------------------------------------------------------

# 23. Responsive Requirements

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

-   sidebar becomes drawer
-   page headers stack
-   search/filter controls stack
-   cards become one column
-   map moves into a sensible position
-   tables/lists remain scrollable or transform appropriately
-   action buttons remain reachable
-   no horizontal overflow

------------------------------------------------------------------------

# 24. Accessibility

Preserve/improve:

-   semantic headings
-   labels
-   keyboard navigation
-   visible focus
-   accessible sidebar drawer
-   accessible tabs
-   accessible map controls
-   accessible toggles
-   accessible validation messages
-   sufficient contrast
-   logical tab order

Do not hide important functionality behind hover-only interactions.

------------------------------------------------------------------------

# 25. Functional Preservation

Do NOT unnecessarily modify:

-   Django views
-   models
-   database
-   URL routes
-   donor search algorithms
-   Google Maps integration
-   location picker logic
-   blood request logic
-   contact request logic
-   notification logic
-   privacy settings
-   account access
-   permissions
-   CSRF
-   authentication/session behavior

UI redesign first.

If a backend change is genuinely required, document it before making it.

------------------------------------------------------------------------

# 26. Implementation Architecture

Create reusable application UI primitives.

Suggested concepts:

-   AppShell
-   Sidebar
-   Topbar
-   PageHeader
-   SectionCard
-   MetricCard
-   EmptyState
-   SafetyBanner
-   StatusBadge
-   SearchPanel
-   FilterGroup
-   MapPanel
-   Tabs
-   FormField
-   Toggle
-   ActionBar
-   DonorCard
-   RequestCard
-   NotificationItem

These can be Django template partials/components or the project's
existing component approach.

Do not duplicate identical markup and CSS across pages.

------------------------------------------------------------------------

# 27. Visual Consistency Rules

All app pages must share:

-   same sidebar
-   same topbar
-   same background
-   same card language
-   same buttons
-   same form controls
-   same page-header geometry
-   same icon system
-   same illustration family
-   same spacing scale
-   same status language
-   same safety components

The user should be able to move from:

Dashboard → Find donors → Requests → Donor profile

without feeling that they opened another website.

------------------------------------------------------------------------

# 28. Final Acceptance Criteria

The authenticated app is complete only when:

-   Dashboard feels like the same product as Find donors.
-   Find donors feels like the same product as Requests.
-   Donor profile feels like the same product as the rest of the app.
-   Sidebar/topbar are truly shared.
-   Page headers are consistent.
-   Search/filter controls are organized.
-   Maps are visually integrated.
-   Forms are consistent.
-   Empty states are reusable.
-   Safety/privacy components are reusable.
-   Mobile navigation works.
-   No horizontal overflow exists.
-   All existing backend functionality still works.
-   Google Maps/location behavior still works.
-   Donor consent/privacy behavior remains intact.
-   Keyboard and accessibility behavior is preserved/improved.

------------------------------------------------------------------------

# 29. Final QA Checklist

Before declaring the redesign finished, test:

## Dashboard

-   load
-   navigation
-   stats
-   create request
-   find donors
-   empty state
-   safety banner

## Find donors

-   blood group filter
-   location search
-   map
-   use current location
-   reset
-   confirm location
-   radius
-   advanced filters
-   search
-   list/map toggle
-   sort
-   empty results

## Requests

-   tabs
-   create request
-   incoming requests
-   outgoing requests
-   empty state
-   request status

## Donor profile

-   all fields
-   blood group
-   location
-   map
-   address search
-   confirm/change location
-   privacy toggle
-   availability
-   show in search
-   contact preference
-   donation date
-   save
-   cancel

## Global

-   sidebar
-   mobile drawer
-   notifications
-   account menu
-   logout
-   keyboard navigation
-   focus states
-   responsive widths
-   browser autofill
-   validation
-   error states
