---
name: rag-governance
description: >-
  Implement access-aware RAG in Enterprise RAG or VAP: hybrid retrieval, rerank,
  citations, AegisAI HITL for sensitive chunks. Use when tuning retrieval,
  adding Qdrant adapter, or wiring enterprise_rag_platform.
---

# RAG Governance

## Principles

1. **Access before ranking** — filter by tenant/role before vector search. This only holds if
   tenant/role/clearance come from a **verified** identity (JWT/OIDC claims) — never trust
   these fields if they arrive as plain request-body values with no signature behind them.
   `enterprise_rag_platform` shipped with client-asserted Principal fields for a while before
   this was caught and documented (see its `docs/adr/0004-api-auth-and-principal-trust.md`) —
   don't repeat that when wiring a new access-aware RAG endpoint.
2. **Citations required** — every answer cites chunk IDs
3. **HITL for sensitive** — low confidence or PII-tagged chunks → gateway pause

## Hybrid retrieval

```text
query → embed → vector + BM25 → merge (hybrid_alpha) → rerank → top_k
```

## VAP strategy adapter

- `enterprise_rag` strategy in venkat-ai-platform delegates to Enterprise RAG API
- Env: `ENTERPRISE_RAG_API_URL`

## LoopForge tuning (ODAEU)

- `top_k`, `hybrid_alpha`, `rerank_threshold` versioned in RAG config tree
- Lessons stored when eval fails

## Reference

- `enterprise_rag_platform` — Qdrant adapter, OTLP export
- `loop-engine-agent-platform/src/loop_engine/rag/`

## Tests

- Golden queries with expected chunk IDs
- Access denial: user without role gets empty retrieval, not leaked chunks
