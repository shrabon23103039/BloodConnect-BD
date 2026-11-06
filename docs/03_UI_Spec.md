# 03 — UI Specification and Design System

**Version:** 1.0  
**Design direction:** Professional healthcare coordination product; calm, trustworthy, accessible; mobile-first.

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
2. Filter panel.
3. Result count.
4. Donor cards with generalized location.
5. Pagination.
6. Empty/error states.

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
