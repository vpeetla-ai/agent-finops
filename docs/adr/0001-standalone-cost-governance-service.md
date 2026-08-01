# ADR-0001: Standalone Cost-Governance Service, Not Embedded Per-Repo Logic

## Status

Accepted — 2026-07-04

## In one breath (panel)

I'd put cost truth in one shared ledger service and let each control plane enforce — embedding fake FinOps in every repo is how seeded dashboards become "governance."

## Context

Org audit: AegisAI's `monthly_cost_usd` was static seed; AegisLoop's `estimate_mission_cost` guessed tokens from character count even after a metered API call. Both discarded real `usage` / `usageMetadata`.

Initial pitch: patch pricing into each repo. That duplicates rate tables, drifts, and leaves VAP / Content Factory / Sentinel Brief still blind.

What I refused: N copies of "FinOps" that never see provider tokens.

## Decision

Standalone service — same single-purpose pattern as VAP / AegisAI / RAG / AegisLoop:

1. FastAPI + ledger (SQLite dev / Postgres prod) — usage in, totals + breach signals out.
2. Thin SDK (`agent_finops_client`) with local fallback when unset — consumers don't hard-fail if FinOps isn't wired.
3. **This service reports cost truth; it does not enforce.** Kill-switch / dispatch refusal stay in the consumer (orchestration vs governance split — portfolio ADR-001).

Consumer wiring staged as follow-up (done later for AegisAI Website Build and AegisLoop) — prove the service alone first.

## Consequences

### Positive

- One pricing table
- Cross-repo / tenant budgets become possible (`scope_type="tenant"`) — schema ready; consumers may not set tenant scopes yet
- Next LLM-calling repo gets FinOps via one HTTP client, not a rewrite

### Negative

- Another service to deploy — SDK fallback makes absence non-fatal
- Enforcement lives in consumers — this ADR alone doesn't green their dashboards

## References

- `src/agent_finops/pricing.py`, `store.py`, `api/main.py`
- `sdk/python/agent_finops_client/client.py`
- [ai-architecture-portfolio ADR-011](https://github.com/vpeetla-ai/ai-architecture-portfolio/blob/main/adr/ADR-011-agent-finops-standalone-service.md)
