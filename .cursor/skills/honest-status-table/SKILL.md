---
name: honest-status-table
description: >-
  Add or update README implementation status tables with ✅ Implemented, 🟡
  Partial, ❌ Planned, 📚 Conceptual. Use before portfolio updates, releases,
  or when marketing copy might oversell repo capabilities.
disable-model-invocation: true
---

# Honest Status Tables

## Required for every platform repo README

```markdown
## Implementation status

| Component | Status | Notes |
|-----------|--------|-------|
| Core graph | ✅ | ... |
| Gateway integration | 🟡 | fail-open in dev |
| Live OAuth publish | ❌ | mock adapters |
```

## Status legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Works in prod/demo with documented config |
| 🟡 | Partial, stub, or env-gated |
| ❌ | Planned, not started |
| 📚 | Documented only (educational / conceptual) |

## Portfolio rule

**Site copy must not exceed README status.** If README says 🟡 mock publish, portfolio cannot say "gateway-gated OAuth live."

## Sync checklist

1. Update repo README table
2. Update `venkat-ai-portfolio/data/ecosystem.ts` capabilities
3. Update `showcase.ts` githubRepos highlights
4. Run mental diff vs [ORG_IMPROVEMENT_PLAN_2026](https://github.com/vpeetla-ai/ai-architecture-portfolio/blob/main/docs/ORG_IMPROVEMENT_PLAN_2026.md)
