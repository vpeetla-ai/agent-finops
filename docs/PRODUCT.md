# Product framing — Agent FinOps

## Who we serve

| Persona | Pain today | What they get |
|---------|------------|----------------|
| **Platform architect** | FinOps dashboards are fake — seeded numbers, never real usage | A real ledger any agent platform can call into with one HTTP request |
| **Engineering lead** | Cost governance is re-built per-team, inconsistently | One canonical pricing table and budget model, not N stale copies |
| **AI safety/governance owner** | "We couldn't pull the plug" on runaway spend | A `breached` signal a control plane can wire to a real kill-switch |

## Job-to-be-done

> "Record what an agent's LLM calls actually cost, tell the caller if that breaks a budget, and let the caller decide what to do about it."

## What we are NOT

- A policy engine or kill-switch — AegisAI already has one; this service reports truth, it doesn't enforce
- A billing/invoicing system — this tracks internal cost attribution, not customer billing
- A replacement for provider-side cost dashboards (OpenAI/Google usage pages) — this is for
  per-agent/per-tenant attribution *inside* your own fleet, which provider dashboards don't give you

## Architecture (customer view)

```text
Real LLM call → real token counts → POST /v1/usage → real cost + budget check → caller enforces
```

## Trade-offs

| Choice | Why | Cost |
|--------|-----|------|
| Standalone service vs. embedded logic | Matches org's single-purpose-repo pattern; enables cross-repo totals | Consumers must wire an HTTP call (or accept local-fallback mode) |
| Report breach, don't enforce | Each consumer's enforcement mechanism already differs (kill-switch vs. dispatch-refusal) | Consumers must remember to act on `breached` |
| One pricing table for the whole org | No per-repo drift | Must be updated here when provider rates change |
| SQLite default, Postgres for prod | Zero-config local dev | Ledger resets on redeploy unless `AGENTFINOPS_DB_BACKEND=postgres` is set |

## Success metrics

- A consumer's real token counts, once wired, produce a cost that matches the provider's own
  billing page within rounding error
- A budget set below current spend is detected as `breached=True` on the next usage record
- The SDK never raises when the service is unreachable/unconfigured — always degrades to local
  estimate

## Related

- [ADR-0001](adr/0001-standalone-cost-governance-service.md)
- [Case study](https://github.com/vpeetla-ai/ai-architecture-portfolio) (once added)
