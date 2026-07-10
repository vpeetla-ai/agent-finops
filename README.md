# Agent FinOps

<!-- vpeetla-tech-stack:start -->
[![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square)]() [![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square)]() [![Vercel](https://img.shields.io/badge/Vercel-000000?style=flat-square)]() [![Render](https://img.shields.io/badge/Render-46E3B7?style=flat-square)]()
<!-- vpeetla-tech-stack:end -->
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Portfolio](https://img.shields.io/badge/🌐_venkat--ai.com-Portfolio-5eead4?style=flat-square)](https://venkat-ai.com/work)

**Real, enforced cost governance for AI agent fleets — usage metering, budgets, and breach signals as a shared service, not a seeded dashboard.**

> Two other repos in this portfolio (`aegisai-enterprise-agent-platform`, `aegisloop-agentops-workbench`) shipped a "FinOps" module that computed cost from fabricated seed data, never real usage. This is the fix — as a standalone service, not duplicated logic in each.

**Live demo (UI):** [agent-finops.vercel.app](https://agent-finops.vercel.app) · **API:** [agent-finops-api.onrender.com](https://agent-finops-api.onrender.com)

---

## Why this exists

Enterprise AI cost governance keeps failing the same way in 2026: teams build a dashboard *after* production traffic arrives, wire it to guessed or seeded numbers, and call it FinOps. Real governance needs three things in place *before* traffic arrives:

1. **Real metering** — actual token counts from the provider's own response, not a character-count guess
2. **A budget, per agent or per tenant** — not just a number to look at
3. **Enforcement** — a budget breach has to *do* something (pause the agent, block the next call), not just render red

This service is the shared ledger + budget check other agent platforms call into, instead of re-implementing pricing tables and cost math per repo.

## 60-second overview

```text
Agent completes an LLM call → real (prompt_tokens, completion_tokens) from the provider response
      → POST /v1/usage {scope, provider, model, tokens}
      → real $ cost computed from one canonical pricing table
      → running total compared against the scope's budget
      → {total_cost_usd, budget_usd, breached} returned to the caller
      → caller decides enforcement (AegisAI: kill-switch; AegisLoop: refuse further paid dispatch)
```

FinOps tells the truth about cost. Each consumer still owns what happens when a budget breaks — this service doesn't reach into another repo's control plane.

## Implementation status (honest)

| Component | Status | Notes |
|-----------|--------|-------|
| Real cost calculation | ✅ | `pricing.py` — real per-model $/1M-token table, non-zero fallback for unknown models |
| Usage ledger | ✅ | SQLite (dev) / Postgres (prod via `AGENTFINOPS_DB_BACKEND=postgres`) |
| Budget set + breach detection | ✅ | `PUT /v1/budget/{scope_type}/{scope_value}`, checked on every `POST /v1/usage` |
| API-key gate on mutating routes | ✅ | Set `AGENTFINOPS_API_KEY` — unset in dev/demo |
| Python SDK (`agent_finops_client`) | ✅ | Graceful local fallback when no service URL configured |
| Consumers wired (AegisAI, AegisLoop) | ✅ | Both call this service for real per-node/per-mission metering and halt real dispatch on breach — see [ai-architecture-portfolio ADR-011/012](https://github.com/vpeetla-ai/ai-architecture-portfolio/blob/main/adr/ADR-012-aegisloop-finops-metering.md) |
| Cross-repo budget totals (e.g. per-tenant across all platforms) | 🟡 | Schema supports it (`scope_type="tenant"`); no consumer sets tenant-scoped budgets yet |
| Multi-provider pricing beyond OpenAI/Gemini/local | ❌ | Add to `pricing.RATES` as new providers get wired |
| Real GCP deploy path (Cloud Run + Cloud SQL) | ✅ | `deploy/terraform/gcp/` — verified with a real `terraform apply`/`destroy` cycle against a live GCP project (real budget breach detected against real Cloud SQL, then torn down). See [ADR-0002](docs/adr/0002-paas-vs-iac-deploy-tradeoffs.md) |

## Quick start (local)

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q                                    # 22 tests, no network required

uvicorn agent_finops.api.main:app --reload --port 8000
# then, in another terminal:
curl -X POST localhost:8000/v1/usage -H "Content-Type: application/json" -d \
  '{"scope_type":"agent","scope_value":"demo","provider":"openai","model":"gpt-4o-mini","prompt_tokens":1000,"completion_tokens":200}'
```

## Using the SDK from another repo

```python
from agent_finops_client import FinOpsClient

client = FinOpsClient(base_url="https://agent-finops-api.onrender.com", api_key=os.getenv("AGENTFINOPS_API_KEY"))
result = client.record_usage(
    scope_type="agent", scope_value="agent-requirements-analyst",
    provider="openai", model="gpt-4.1-mini",
    prompt_tokens=real_prompt_tokens, completion_tokens=real_completion_tokens,
)
if result.breached:
    ...  # caller decides: kill-switch, refuse next call, alert — this service just tells the truth
```

If `base_url` is unset, `record_usage` computes cost locally from the same pricing table and
returns `breached=False` — a consumer repo never hard-fails just because this service isn't
deployed yet, matching the "fail open when not configured" convention used across this org.

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) · [docs/PRODUCT.md](docs/PRODUCT.md) · [ADR-0001](docs/adr/0001-standalone-cost-governance-service.md)

## Interview map

**Business function:** Shared FinOps service — usage metering, budgets, cost-breach signals for agent fleets.

Staff+ prep crosswalk — [playbook](https://github.com/vpeetla-ai/ai-architect-interview-playbook) · [study UI](https://ai-architect-interview-playbook.vercel.app) · [Practice Arena](https://ai-architect-practice-arena.vercel.app) · [org matrix](https://github.com/vpeetla-ai/ai-architecture-portfolio/blob/main/docs/REPO_INTERVIEW_MAP.md). Only entries this repo honestly exercises.

| Category | Entry | Fit |
|----------|-------|-----|
| Cloud | [Orchestration & cost optimization](https://ai-architect-interview-playbook.vercel.app/q/cloud-architecture/06-container-orchestration-and-cost-optimization-at-scale/) ([md](https://github.com/vpeetla-ai/ai-architect-interview-playbook/blob/main/cloud-architecture/06-container-orchestration-and-cost-optimization-at-scale.md)) | Cost governance as a shared service |
| System design | [Multi-tenant AI platform](https://ai-architect-interview-playbook.vercel.app/q/ai-system-design/09-multi-tenant-ai-platform-architecture/) ([md](https://github.com/vpeetla-ai/ai-architect-interview-playbook/blob/main/ai-system-design/09-multi-tenant-ai-platform-architecture.md)) | Partial — per-tenant budgets / quotas |
| Trade-offs | [Cost vs latency vs safety](https://ai-architect-interview-playbook.vercel.app/q/scalability-governance-tradeoffs/01-cost-vs-latency-vs-safety/) ([md](https://github.com/vpeetla-ai/ai-architect-interview-playbook/blob/main/scalability-governance-tradeoffs/01-cost-vs-latency-vs-safety.md)) | Enforced budgets vs best-effort dashboards |
| Trade-offs | [Build vs buy shared services](https://ai-architect-interview-playbook.vercel.app/q/scalability-governance-tradeoffs/02-build-vs-buy-shared-services/) ([md](https://github.com/vpeetla-ai/ai-architect-interview-playbook/blob/main/scalability-governance-tradeoffs/02-build-vs-buy-shared-services.md)) | Why a dedicated metering service |
| Behavioral | [FinOps audit and fix](https://ai-architect-interview-playbook.vercel.app/q/behavioral/02-finops-audit-and-fix/) ([md](https://github.com/vpeetla-ai/ai-architect-interview-playbook/blob/main/behavioral/02-finops-audit-and-fix.md)) | Finding/fixing real FinOps gaps in-org |

## Related

- [ai-architecture-portfolio](https://github.com/vpeetla-ai/ai-architecture-portfolio) — org-wide ADRs and case studies
- [aegisai-enterprise-agent-platform](https://github.com/vpeetla-ai/aegisai-enterprise-agent-platform) — live consumer (Website Build agents halt on budget breach)
- [aegisloop-agentops-workbench](https://github.com/vpeetla-ai/aegisloop-agentops-workbench) — live consumer (mission dispatch metering)

MIT License
