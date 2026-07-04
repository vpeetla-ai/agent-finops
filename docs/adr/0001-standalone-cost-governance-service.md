# ADR-0001: Standalone Cost-Governance Service, Not Embedded Per-Repo Logic

## Status

Accepted — 2026-07-04

## Context

An org-wide security/architecture audit found `aegisai-enterprise-agent-platform`'s and
`aegisloop-agentops-workbench`'s FinOps modules both compute cost from fabricated data: AegisAI's
`RegisteredAgent.monthly_cost_usd` is a static seed value that never updates from real usage;
AegisLoop's `estimate_mission_cost` guesses tokens from output character count even when a real,
metered API call is made. Both discard the real `usage`/`usageMetadata` field their own provider
responses already carry.

The initial proposal was to fix this by adding pricing/budget/enforcement logic directly inside
each of the two repos. That would have worked, but it duplicates pricing tables and budget math
in every consumer, and doesn't help the three *other* repos in this portfolio that also make real
LLM calls with no FinOps at all (VAP, Content Factory, Sentinel Brief).

## Decision

Build this as a standalone repo and service — consistent with how every other capability in this
org is its own single-purpose repo (VAP = orchestration, AegisAI = governance, Enterprise RAG =
knowledge, AegisLoop = fleet ops). Mirrors AegisAI's own `sdk/python/aegisai_gateway` + service
split, the org's established "shared capability + thin client" pattern:

1. A FastAPI service with its own ledger (SQLite dev / Postgres prod) — real usage events in,
   real running totals and budget-breach signals out.
2. A thin Python SDK (`agent_finops_client`) other repos import, with graceful local-fallback
   when the service isn't configured — a consumer never hard-fails on this being unavailable.
3. **This service reports cost truth; it does not enforce.** AegisAI's kill-switch and
   AegisLoop's dispatch-refusal are each consumer's own job — this service doesn't reach into
   another repo's control plane, matching the org's existing separation of orchestration vs.
   governance (see `ai-architecture-portfolio` ADR-001).

Consumer wiring (AegisAI, AegisLoop) is deliberately staged as a follow-up, not done in this
initial build — proving the service works standalone first avoids a shallow, half-wired result
across three repos in one pass.

## Consequences

### Positive
- One canonical pricing table instead of N per-repo copies that drift independently.
- Real cross-repo/cross-tenant budget totals become possible (schema already supports
  `scope_type="tenant"`), which per-repo FinOps modules could never provide.
- Any future repo with real LLM calls gets FinOps for the cost of one HTTP client call, not a
  re-implementation.

### Negative
- A new service to deploy and keep available — the SDK's local-fallback mode exists specifically
  to make this non-fatal if it's down or not yet wired.
- Consumer wiring (the part that actually fixes AegisAI's and AegisLoop's fake dashboards) is not
  done in this repo — it's a tracked follow-up in each consumer repo and in
  `ai-architecture-portfolio/docs/ORG_IMPROVEMENT_PLAN_2026.md`.

### Follow-ups
- Wire `aegisai-enterprise-agent-platform`'s `WebsiteBuildOrchestrator` (5 agents already map to
  existing registry entries) as the first real consumer, with budget breach wired to the
  existing, real `KillSwitchService`.
- Wire `aegisloop-agentops-workbench`'s mission runtime as the second consumer.
- Consider splitting `agent_finops_client` into its own lightweight package (no FastAPI/uvicorn
  dependency) if a consumer wants a thinner install footprint.

## References
- `src/agent_finops/pricing.py`, `store.py`, `api/main.py`
- `sdk/python/agent_finops_client/client.py`
- Org pattern precedent: [aegisai-enterprise-agent-platform `sdk/python/aegisai_gateway`](https://github.com/vpeetla-ai/aegisai-enterprise-agent-platform/tree/main/sdk/python)
- [ai-architecture-portfolio ORG_IMPROVEMENT_PLAN_2026.md](https://github.com/vpeetla-ai/ai-architecture-portfolio/blob/main/docs/ORG_IMPROVEMENT_PLAN_2026.md) (Phase 6 backlog item)
