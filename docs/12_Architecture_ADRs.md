# 12 — Architecture Decision Records (ADRs)

Record important decisions here. New decisions should be appended, not silently substituted.

## ADR-001 — Modular monolith for MVP

**Status:** Accepted  
**Decision:** Use one Django deployment with clearly separated Django apps.  
**Reason:** Appropriate for one primary developer, faster delivery, simpler operations and sufficient scale path.  
**Consequences:** Keep module boundaries explicit; extract services only when measured operational needs justify it.

## ADR-002 — P2P-first product model

**Status:** Accepted  
**Decision:** Donor-to-recipient coordination is the core workflow; hospital participation is optional.  
**Reason:** MVP must function without external institutional partnerships.  
**Consequences:** Do not make hospital accounts or integrations a dependency for core flows.

## ADR-003 — Consent-gated donor contact

**Status:** Accepted  
**Decision:** Recipient sends contact request; donor explicitly accepts before consented contact channels are disclosed.  
**Reason:** Reduce scraping, spam and unwanted disclosure.  
**Consequences:** Implement state machine, audit trail, rate limits and object-level permissions.

## ADR-004 — Django templates + Bootstrap for web MVP

**Status:** Accepted  
**Decision:** Use server-rendered Django templates and Bootstrap; expose DRF APIs for mobile/future clients.  
**Reason:** One developer can deliver a maintainable web product without separate frontend deployment.  
**Consequences:** Keep UI components reusable and API contracts independent of templates.

## ADR-005 — PostgreSQL as system of record

**Status:** Accepted  
**Decision:** Use PostgreSQL and Django ORM.  
**Reason:** Relational constraints, transactions, indexing and mature operational tooling.  
**Consequences:** No direct client database access.

## ADR-006 — No PostgreSQL RLS in MVP

**Status:** Accepted  
**Decision:** Use server-side Django authorization; evaluate RLS later as defense in depth.  
**Reason:** RLS with pooling and transaction identity context adds complexity and must be deliberately tested.  
**Consequences:** Every query and endpoint must enforce owner/role access. RLS can be added after a dedicated design review.

## ADR-007 — Flutter as future mobile client

**Status:** Accepted  
**Decision:** Build responsive web MVP first; use DRF API for future Flutter Android/iOS client.  
**Reason:** Avoid parallel web/mobile implementation before product workflows are stable.  
**Consequences:** API contract, auth and pagination must be mobile-ready.

## ADR-008 — No medical compatibility engine

**Status:** Accepted  
**Decision:** Search by exact requested blood-group label and location only; do not implement transfusion compatibility or eligibility rules.  
**Reason:** These are clinical decisions requiring professional assessment.  
**Consequences:** Product language must consistently say "potential donor".

## ADR-009 — External integrations behind adapters

**Status:** Accepted  
**Decision:** Email, SMS, map, hospital, identity and DGHS integrations use adapters.  
**Reason:** Credentials, authorization and provider availability are uncertain.  
**Consequences:** Mock adapters in development; production integration disabled until approved.

## ADR template

### ADR-NNN — Title
- Status: Proposed / Accepted / Rejected / Superseded
- Date:
- Context:
- Decision:
- Alternatives:
- Consequences:
- Related documents:
