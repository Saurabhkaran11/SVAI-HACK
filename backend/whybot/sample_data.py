"""Static content: opt-in starter knowledge, default personas and suggested questions.

Nothing here is loaded into the brain unless the user asks for starter data.
"""

# Opt-in starter set. Loaded only via `ingest.py --sample` or the UI button.
SAMPLE_DOCS = {
    "adr_007": {
        "title": "ADR-007: Payments API v1 to v2 Migration",
        "type": "adr",
        "text": """# ADR-007: Migrate from Payments API v1 to v2
Status: Accepted | Date: 2026-03-15 | Team: Payments

## Context
v1 payments API uses synchronous Stripe calls with per-request connection setup.
p99 latency exceeds 1200ms at 500 RPS. v2 introduces connection pooling, async
webhook handling, and batch settlement.

## Decision
Deprecate v1 by Q3 2026. All consuming services must migrate to v2.
Highest-priority consumers: billing-service, invoice-generator, checkout-service.

## Consequences
- checkout-service: update payment initiation calls (owner: frontend-platform)
- billing-service: migrate recurring charge logic (owner: payments)
- invoice-generator: switch settlement endpoints (owner: payments)
""",
    },
    "meeting_notes": {
        "title": "Architecture Review: Payments v1 Deprecation",
        "type": "meeting_notes",
        "text": """# Architecture Review: Payments v1 Deprecation
Date: 2026-04-02 | Attendees: Sarah Chen (Payments Lead), Mike Torres (Platform),
Priya Patel (Billing), James Wright (SRE)

Sarah: ADR-007 is accepted. v1 sunset target is September 1. Billing-service is the
critical path - Priya, your team owns that migration.
Priya: We can start in May. Recurring charge logic is tightly coupled to v1's
synchronous response format. Estimate: 3-4 sprints.
Mike: checkout-service has a thinner integration. We can parallelize.
James: The March 12 incident (INC-0312) was v1 connection exhaustion under load.
That postmortem recommended this migration. Link the timeline so on-call knows.
""",
    },
    "slack_thread": {
        "title": "#payments-eng: v1 Deprecation Timeline",
        "type": "slack_thread",
        "text": """# Slack #payments-eng thread
sarah.chen: Migration tracking sheet is live. billing-service target: June 30.
checkout-service target: July 15. invoice-generator target: August 1.
priya.patel: Billing needs a feature flag for cutover: use_payments_v2.
We can't do a hard switch mid-billing-cycle.
james.wright: SRE keeps v1 monitoring active until all services confirm migration.
Dashboard: go/payments-v1-deprecation
mike.torres: checkout-service PR is up - only 3 call sites. Merge by April 25.
After that, billing is the only hard blocker.
""",
    },
    "postmortem": {
        "title": "Incident Postmortem: INC-0312",
        "type": "postmortem",
        "text": """# Incident Postmortem: INC-0312
Severity: SEV-2 | Duration: 47 minutes | Date: 2026-03-12
Service: payments-api-v1 | On-call: James Wright (SRE)

## Summary
payments-api-v1 exhausted its Stripe connection pool under sustained load (>600 RPS),
causing cascading timeouts in billing-service and checkout-service. Customer-facing
payment failures lasted 47 minutes.

## Root Cause
v1 creates a new Stripe connection per request. At 600+ RPS the pool ceiling
(default 500) is exceeded. No circuit breaker existed.

## Resolution
Temporarily raised pool ceiling to 1000. Permanent fix: migrate to v2
(persistent connection pooling, see ADR-007).
""",
    },
    "onboarding": {
        "title": "New Engineer Onboarding Guide",
        "type": "guide",
        "text": """# New Engineer Onboarding
- Payments questions: ask in #payments-eng, owner Sarah Chen.
- Billing on-call rotation is owned by Priya Patel's team.
- SRE escalation: James Wright, pager alias sre-primary.
- All payment changes need a feature flag and an SRE sign-off before rollout.
""",
    },
}

MANIFEST_ID = "service_manifest"
MANIFEST_TEXT = """# Service Dependency Manifest
- checkout-service (owner: frontend-platform) -> payments-api-v1, payments-api-v2
- billing-service (owner: payments) -> payments-api-v1, stripe-api
- invoice-generator (owner: payments) -> payments-api-v1, billing-service
- auth-service (owner: platform) -> rate-limit-config
- rate-limit-config -> references payments-api-v1 routes
"""

MANIFEST_GRAPH = {
    "entities": {
        "checkout": {"name": "checkout-service", "type": "SERVICE", "namespace": "services"},
        "billing": {"name": "billing-service", "type": "SERVICE", "namespace": "services"},
        "invoice": {"name": "invoice-generator", "type": "SERVICE", "namespace": "services"},
        "auth": {"name": "auth-service", "type": "SERVICE", "namespace": "services"},
        "payments_v1": {"name": "payments-api-v1", "type": "API", "namespace": "apis"},
        "payments_v2": {"name": "payments-api-v2", "type": "API", "namespace": "apis"},
        "stripe_api": {"name": "stripe-api", "type": "API", "namespace": "apis"},
        "rate_limit_config": {"name": "rate-limit-config", "type": "CONFIG", "namespace": "platform"},
        "team_frontend": {"name": "frontend-platform", "type": "TEAM", "namespace": "teams"},
        "team_payments": {"name": "payments", "type": "TEAM", "namespace": "teams"},
        "team_platform": {"name": "platform", "type": "TEAM", "namespace": "teams"},
    },
    "relations": [
        {"source": "checkout", "target": "payments_v1", "predicate": "DEPENDS_ON", "context": "checkout-service still calls payments-api-v1."},
        {"source": "checkout", "target": "payments_v2", "predicate": "DEPENDS_ON", "context": "checkout-service has started integrating payments-api-v2."},
        {"source": "billing", "target": "payments_v1", "predicate": "DEPENDS_ON", "context": "billing-service depends on payments-api-v1 for recurring charges."},
        {"source": "billing", "target": "stripe_api", "predicate": "DEPENDS_ON", "context": "billing-service also calls stripe-api."},
        {"source": "invoice", "target": "payments_v1", "predicate": "DEPENDS_ON", "context": "invoice-generator depends on payments-api-v1 settlement endpoints."},
        {"source": "invoice", "target": "billing", "predicate": "DEPENDS_ON", "context": "invoice-generator depends on billing-service."},
        {"source": "auth", "target": "rate_limit_config", "predicate": "DEPENDS_ON", "context": "auth-service references payment route rate limits."},
        {"source": "rate_limit_config", "target": "payments_v1", "predicate": "REFERENCES", "context": "rate-limit-config references payments-api-v1 routes."},
        {"source": "payments_v2", "target": "payments_v1", "predicate": "REPLACES", "context": "payments-api-v2 is the migration target for v1 consumers."},
        {"source": "checkout", "target": "team_frontend", "predicate": "OWNED_BY"},
        {"source": "billing", "target": "team_payments", "predicate": "OWNED_BY"},
        {"source": "invoice", "target": "team_payments", "predicate": "OWNED_BY"},
        {"source": "auth", "target": "team_platform", "predicate": "OWNED_BY"},
    ],
}

# Generic roles - work on ANY company's data. Users can add their own in the UI.
PERSONAS = {
    "engineer": {
        "label": "Engineer",
        "memories": [
            "I am an engineer. I prefer concrete steps, code-level details, APIs and dependencies.",
        ],
    },
    "manager": {
        "label": "Manager",
        "memories": [
            "I am a manager. I prefer timelines, owners, risks and blockers over implementation details.",
        ],
    },
    "new_hire": {
        "label": "New Hire",
        "memories": [
            "I joined the company this week and don't know who owns what yet.",
            "I prefer plain-language explanations with the names of people to ask.",
        ],
    },
}

# Questions that work on any knowledge base
STARTER_QUESTIONS = [
    "Who owns what, and who should I ask first?",
    "What are the biggest open risks or blockers?",
    "Summarize the key decisions and why they were made.",
]

SAMPLE_QUESTIONS = [
    "What would break if we deprecated the v1 payments API?",
    "Who should I talk to before changing billing-service?",
    "Why are we migrating to payments v2?",
    "What is blocking the v1 sunset on September 1?",
]
