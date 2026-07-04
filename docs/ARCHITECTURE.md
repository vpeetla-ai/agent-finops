# Architecture — Agent FinOps

## System context

```text
Consumer repo (AegisAI, AegisLoop, ...)
    │  real LLM call → real (prompt_tokens, completion_tokens) from provider response
    ▼
agent_finops_client.FinOpsClient.record_usage(...)
    │  HTTP if base_url configured, else local pricing fallback
    ▼
FastAPI (Render) — POST /v1/usage
    │
    ├── pricing.estimate_cost_usd(model, prompt_tokens, completion_tokens) → real $
    ├── store.record_usage(event) → append to ledger, sum running total for scope
    └── compare total against store.get_budget(scope) → {breached: bool}
    ▼
Response back to consumer: {cost_usd, total_cost_usd, budget_usd, breached}
    │
    ▼
Consumer decides enforcement (this service does not reach into another repo's control plane)
```

## Data model

- `usage_events`: append-only ledger — every recorded completion, with real token counts and
  the computed cost, keyed by `(scope_type, scope_value)`.
- `budgets`: current budget per `(scope_type, scope_value)`. `scope_type` is a plain string
  (`agent`, `tenant`, `repo`, ...) — this service doesn't validate what a scope *means*, only
  sums against a stable key. That keeps AegisAI's per-agent budgets and AegisLoop's
  per-mission/per-repo budgets on the same schema without either repo's vocabulary leaking in.

## Key decisions

- **Standalone service, not embedded per-repo logic.** Every other capability in this org is its
  own single-purpose repo (VAP = orchestration, AegisAI = governance, Enterprise RAG =
  knowledge). A shared cost ledger is also the only way to get a *real* cross-tenant total
  instead of per-repo fragments.
- **This service computes cost and detects breaches; it does not enforce.** AegisAI already has
  a real, working kill-switch (`KillSwitchService`) — this service's job is to tell the truth
  about cost, not duplicate policy enforcement that already exists elsewhere. AegisLoop has no
  kill-switch, so its enforcement is a lighter "refuse further paid-mode dispatch."
- **Real token counts come from the consumer, not this service.** Only the consumer repo can see
  the actual provider response (`usage`/`usageMetadata` field) — this service can't reach into
  another repo's LLM gateway. The SDK's job is making that data easy to report, not extracting it.
- **Pricing lives in one file.** `pricing.py`'s `RATES` table is the single place model $/1M-token
  rates are maintained across the whole org, instead of N stale copies drifting independently.
- **SQLite dev default, Postgres production**, selected via `AGENTFINOPS_DB_BACKEND` — same
  pattern as `aegisai-enterprise-agent-platform/infrastructure/persistence/factory.py`.

## Deployment topology

| Component | Local | Production |
|-----------|-------|-------------|
| API | FastAPI :8000 | Render (Docker) |
| Database | SQLite `:memory:` | Postgres (`AGENTFINOPS_DB_BACKEND=postgres`) |
| Demo UI | `demo/index.html` | Vercel static |

## Related repos

| Layer | Repo |
|-------|------|
| Governance (fast-follow consumer) | [aegisai-enterprise-agent-platform](https://github.com/vpeetla-ai/aegisai-enterprise-agent-platform) |
| AgentOps (fast-follow consumer) | [aegisloop-agentops-workbench](https://github.com/vpeetla-ai/aegisloop-agentops-workbench) |
| Org ADRs | [ai-architecture-portfolio](https://github.com/vpeetla-ai/ai-architecture-portfolio) |
