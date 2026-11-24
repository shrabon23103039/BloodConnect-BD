# BloodConnect BD UI Audit — Baseline

**Date:** 2026-11-24
**Environment:** Playwright Chromium against Django `live_server`, `config.settings.test`, isolated in-memory SQLite and a synthetic active account. The existing human-authenticated browser session was not available to the automation and was not accessed.
**Scope:** Baseline infrastructure run only; no application UI or backend behavior was changed.

## Testing tools

- **Playwright:** already present in the pinned Python development requirements (`1.64.1`); browser tests run with the project’s existing pytest setup.
- **axe-core:** configured as an exact-pinned test-only npm dev dependency (`4.14.1`); scans WCAG 2.1 A/AA tags at 390px and 1366px.
- **Visual regression:** configured with exact-pinned `pixelmatch` (`8.0.0`) and `pngjs` (`7.0.0`); explicit compare mode allows 0.5% changed pixels and writes diff artifacts on regression.
- **Lighthouse:** unavailable/not installed; no network-based one-shot install was introduced.
- **Screenshots:** 20 reference images for ten representative routes at 390px and 1366px. They contain synthetic/anonymous application content and are organized at `tests/ui/screenshots/<page>/{mobile,desktop}/baseline.png`.

## Pages discovered and baseline status

The machine-readable page/viewport/browser findings are in [`tests/ui/baseline-results.json`](../tests/ui/baseline-results.json). The suite visited 20 actual route/context combinations (11 widths each):

| Page | Context | Status |
|---|---|---|
| Landing page `/` | Guest | PASS: route and all viewport geometry checks |
| Authenticated dashboard `/` | Synthetic signed-in user | ISSUES FOUND: axe contrast/ARIA accessible-name findings and 18px mobile overflow at 320–480px |
| How it works `/how-it-works/` | Guest | PASS |
| Privacy notice `/privacy/` | Guest | PASS |
| Safety `/safety/` | Guest | PASS |
| Terms `/terms/` | Guest | PASS |
| Contact `/contact/` | Guest | PASS |
| Sign in `/accounts/login/` | Guest | PASS |
| Create account `/accounts/register/` | Guest | PASS |
| Password reset `/accounts/password-reset/` | Guest | PASS |
| Verification start `/accounts/verify/request/` | Guest | PASS |
| Find donors `/app/` | Synthetic signed-in user | ISSUES FOUND: axe contrast |
| Donor Profile `/app/donor-profile/` | Synthetic signed-in user | ISSUES FOUND: axe contrast |
| Blood requests `/app/requests/` | Synthetic signed-in user | ISSUES FOUND: axe contrast |
| Create blood request `/app/requests/new/` | Synthetic signed-in user | ISSUES FOUND: axe contrast |
| Incoming contact requests `/app/contact-requests/incoming/` | Synthetic signed-in user | ISSUES FOUND: axe contrast |
| Outgoing contact requests `/app/contact-requests/outgoing/` | Synthetic signed-in user | ISSUES FOUND: axe contrast |
| Notifications `/app/notifications/` | Synthetic signed-in user | ISSUES FOUND: axe contrast |
| Privacy settings `/app/settings/privacy/` | Synthetic signed-in user | ISSUES FOUND: axe contrast |
| Account access `/accounts/google/link/` | Synthetic signed-in user | ISSUES FOUND: axe contrast |

The machine-readable per-page status combines route/geometry, expected active navigation and axe results. “PASS” does not mean complete visual, data-backed, manual accessibility, or functional acceptance. The mobile-drawer Requests activation issue is recorded separately in `navigation_smoke` because it is a cross-page interaction.

## Baseline results

- **Responsive:** all 20 route/context combinations were measured at 320, 375, 390, 414, 480, 768, 1024, 1280, 1366, 1440 and 1920px. The authenticated dashboard overflows horizontally by 18px at 320, 375, 390, 414 and 480px; other audited routes had no detected horizontal document overflow. The inspected 390px dashboard screenshot shows the secondary “Create a request” action extending beyond the right viewport edge near the empty-state card.
- **Accessibility:** axe reported `color-contrast` findings on authenticated pages at both representative widths; public pages had no axe violations in the selected WCAG 2.1 A/AA rules. Authenticated contrast findings include the shared sidebar section labels, sidebar note, topbar label and footer, plus low-contrast secondary text in Find Donors, Requests/contact-request cards, map/provider hints and the donor-profile return link. The dashboard also has `aria-allowed-attr` on `#dashboard-quick-search` and `label-content-name-mismatch` on its stat cards/user link. Exact affected selectors, nodes and contrast ratios are recorded without suppression in the JSON results. This automated scan is not a WCAG conformance claim.
- **Typography:** computed body font, size and line-height, document title, and H1 count were recorded at every width for follow-up. Inspected desktop/mobile screenshots include the landing page, authenticated dashboard and Donor Profile editor. On the editor screenshot, the map is intentionally unavailable in this isolated test settings environment without a Maps browser key; the page presents its fallback and privacy explanation.
- **Navigation:** the synthetic account followed desktop sidebar links to Find Donors, Requests, Donor Profile, Privacy Settings, Account Access and Safety; Logout was not submitted. The mobile drawer opens and exposes a visible Requests link with the expected href, but activating it leaves the browser at `/` in this run. This is recorded as an issue requiring a separate browser interaction check.
- **Forms/actions:** the baseline only rendered form pages. It did not submit registration, profile, request, contact, consent, password reset or location actions. No persistent data was created outside the isolated test database.
- **Browser errors:** zero uncaught page errors, console errors or failed requests were recorded in the test browser run.
- **Warnings:** Django emitted a non-blocking warning that local `staticfiles/` does not exist. Static assets loaded successfully in the test run; this warning is an environment configuration finding, not a reported broken asset.
- **Screenshot review:** landing desktop plus authenticated dashboard desktop/mobile and Donor Profile editor desktop/mobile screenshots were opened and visually inspected. Other captured route screenshots were not individually inspected.
- **Visual image diff:** the full opt-in comparison run passed for all 20 desktop/mobile screenshots (`20 MATCH`, changed pixels within the configured 0.5% tolerance). This establishes a same-environment baseline; it does not guarantee pixel identity across different operating systems, fonts or browser builds.

## Not included / unavailable

- The pre-existing authenticated development browser session could not be attached; the runner deliberately uses a synthetic account in a disposable test database instead. Therefore these results do not describe data or session-specific states in the running local server.
- Dynamic request/contact/accepted-connection details require synthetic domain records; moderator reports and operations require a moderator account. They are listed in `not_in_baseline` in the JSON and are not marked as passed.
- Documented paths with no matching route (including `/app/profile/`, `/app/help/`, `/app/donors/<id>/` and `/app/report/`) are explicitly listed as unavailable in the JSON; no routes were invented.
- Google Maps/Places is not functionally exercised by this baseline. Location picker screenshot/runtime behavior with a configured provider still needs a separate controlled browser check.
- The browser runner does not audit every link or manually review keyboard flow, focus, screen-reader output, validation states, all individual screenshot layouts or color contrast by eye. Use `tests/ui/QUALITY_CHECKLIST.md` for the controlled page-by-page review.

## Recommended next actions

1. Review the contrast findings, prioritizing shared authenticated shell and footer nodes, then page-specific secondary/help text.
2. Use the captured screenshots as a baseline before any per-page redesign and update only the target page’s reviewed baseline after an intentional design change.
3. Add isolated synthetic records for safe detail-page coverage and an explicit moderator fixture for moderator-only pages, keeping mutation workflows out of the baseline.
4. Perform manual keyboard, form validation, consent, location-picker and authenticated browser review when a separately provided test session/browser harness is available.
