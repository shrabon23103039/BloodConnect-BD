# BloodConnect BD UI quality review checklist

Use this checklist during page-by-page manual review. Record observations and evidence; do not automatically rewrite application files.

## Typography and content

- [ ] Page title, section heading, card title, body, helper, label, button and badge sizes form a readable hierarchy.
- [ ] Body copy is comfortably readable; line-height and line length support scanning.
- [ ] Font family and weights match the shared design; text does not clip, collide or truncate unexpectedly.
- [ ] Copy is accurate, concise, consistently capitalized and free of spelling/punctuation errors.
- [ ] Safety, privacy, consent and validation copy remains clear and complete.

## Layout and components

- [ ] Shared shell, active navigation, page width, header, footer and spacing are consistent.
- [ ] Cards align; padding, radii, borders and shadows appear intentional and consistent.
- [ ] Inputs, selects, textareas, tabs, alerts, badges, buttons and empty/error states are legible and usable.
- [ ] Primary and secondary actions have clear hierarchy and visible state feedback.
- [ ] Images and icons render correctly and support the content.

## Responsive

- [ ] Review widths 320, 375, 390, 414, 480, 768, 1024, 1280, 1366, 1440 and 1920px.
- [ ] No horizontal overflow, clipped/overlapping content, broken grids or excessive empty space.
- [ ] Mobile drawer opens, closes, supports keyboard operation and exposes navigation links.
- [ ] Forms stack appropriately; buttons remain reachable and touch-friendly.
- [ ] Tables, maps, search results and long text remain usable at narrow widths.

## Accessibility

- [ ] Run axe-core; review every violation, impact and affected element without blanket suppression.
- [ ] Heading hierarchy, landmarks and semantic controls communicate structure.
- [ ] Every form control has an associated label; errors identify the relevant field and state.
- [ ] Keyboard order and visible focus are clear; icon-only controls have accessible names.
- [ ] Color is not the sole signal; contrast is reviewed for text and controls.
- [ ] Images have appropriate alt text; decorative images are hidden from assistive technology.

## Functionality and privacy

- [ ] Links, tabs, search, filters, pagination and non-destructive navigation work.
- [ ] Validation and cancel/save paths work in the isolated test environment.
- [ ] Do not submit real requests, messages, payments, destructive actions or consent changes during an audit.
- [ ] Verify private contact details and precise location values are not exposed in page content, URLs, screenshots or logs.
- [ ] Record whether an action was only observed, safely exercised with synthetic data, or blocked.
