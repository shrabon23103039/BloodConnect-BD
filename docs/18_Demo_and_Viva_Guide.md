# BloodConnect BD Demonstration and Viva Guide

**Demonstration target:** local Compose environment with synthetic accounts and data.
**Duration:** approximately 10 minutes.
**Evidence status:** local test/build evidence only; this is not staging or production evidence.

## Before the demonstration

1. Review `docs/EXECUTION_STATE.md` and disclose that hosted staging, restore, load and release verification are still pending.
2. Start the local stack with `docker compose up --build -d` and confirm `docker compose ps` shows the web, PostgreSQL, Redis, worker and beat services healthy/running.
3. Check `http://localhost:8000/health/live/` and `http://localhost:8000/health/ready/`.
4. Use only synthetic accounts, locations, donor profiles, requests and contact details. Do not project `.env`, secrets, real personal data or real provider credentials.
5. For the browser acceptance flow, run `pytest --ds=config.settings.test tests/e2e/test_browser_flows.py -q --tb=short -p no:cacheprovider`; it creates isolated test records and verifies its own workflow.

## Suggested walkthrough

| Time | Demonstration | Evidence point |
|---|---|---|
| 0:00–1:00 | Explain the product boundary and show the public home/safety pages. | Coordination only; no medical eligibility/compatibility decisions, blood handling, or assumed institutional integration. |
| 1:00–2:30 | Open donor search while signed out; filter by exact blood group and synthetic location. | Guest search is consent-gated and paginated; only public alias, group, availability and administrative location are shown. |
| 2:30–4:00 | Register and verify a synthetic recipient in the local mock flow, then sign in. | Pending accounts cannot use active workflows; the mock sends no real message and is not available in production. |
| 4:00–5:00 | Show privacy settings and create or inspect a synthetic donor profile with discovery consent. | Visibility, availability and current purpose-specific consent all gate discovery. |
| 5:00–6:30 | Create a synthetic blood request and compare public listing/detail with owner view. | Owner-only facility/description fields are not included in public output. |
| 6:30–8:00 | Submit a contact request as recipient; inspect pending state as donor, then accept. | Contact remains hidden while pending; accepted disclosure rechecks current channel verification and consent. |
| 8:00–9:00 | Show participant-scoped notifications, report/block path or moderator-only queue using pre-seeded synthetic roles. | Report privacy and explicit moderator authorization; staff status alone is insufficient. |
| 9:00–10:00 | Show API schema/usage guide, readiness endpoint and checkpoint. | Explain token rotation, current route scope and remaining hosted-operation limitations. |

If a step requires moderator seeding or an account state not prepared in advance, show the relevant automated test rather than weakening authorization or using real data. Do not activate real email/SMS delivery during a demonstration.

## Evidence to retain

- Test command output and the actual pass count for the current run.
- Redacted screenshots of synthetic public search, pending contact privacy, post-acceptance disclosure and health endpoints.
- The current plan/checkpoint and API schema validation result.
- A note identifying local Compose/SQLite test context and explicitly stating that no hosted load, restore or security test was performed.

Screenshots must not include tokens, emails/phone numbers belonging to real people, environment values, database URLs or browser password-manager content. Avoid capturing private donor channels even if synthetic; the recipient disclosure screen may show only designated synthetic test values.

## Likely viva questions

**How is donor privacy protected?** Search uses an eligible queryset that requires active status, availability, enabled visibility and current discovery consent. Search serializers/templates use an explicit public field allowlist. Contact details are withheld from a pending request and checked again after acceptance.

**Does a matching blood group prove compatibility?** No. It is only a discovery filter. Medical eligibility and compatibility decisions belong to qualified healthcare professionals and authorized facilities.

**Why can guests search?** Guests can see only the same limited result fields, and only when the donor's current discovery consent and profile visibility permit discovery. Throttling applies to the route.

**What has not been validated?** A Render staging deployment, live verification delivery, load behavior, a hosted backup restore, independent security testing, legal text and real location data. Do not claim capacity, compliance or clinical validation without evidence.

**Why is Render not deployed yet?** `render.yaml` is a paid-resource blueprint and the owner has not authorized account/resource setup or deployment. It uses dynamic Render-provided host values; no account, DNS name or credentials are assumed.
