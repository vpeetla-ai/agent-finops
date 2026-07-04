---
name: agent-protocol-stack-2026
description: >-
  Apply the 2026 agent protocol stack: Skills → MCP (tools) → Gateway (side
  effects) → Observability. Use when designing cross-repo integrations or
  explaining how vpeetla-ai repos compose for production.
---

# 2026 Agent Protocol Stack

## Four layers (vpeetla-ai)

```text
Skills (vpeetla-ai-skills)  → how engineers & agents develop
MCP                         → how agents access tools & context
Gateway (AegisAI)           → what side effects are allowed
Observability               → how we debug non-deterministic runs
```

## Repo map

| Question | Repo | Protocol focus |
|----------|------|----------------|
| How do we build? | vpeetla-ai-skills | Skills |
| What should agents do? | venkat-ai-platform | MCP client, orchestration |
| What are they allowed? | aegisai | Gateway, HITL |
| What knowledge? | enterprise_rag_platform | MCP context + access control |
| How operate fleets? | aegisloop | Observability, eval gates |
| What produce? | ai-content-factory | Gateway + HITL publish |
| How improve? | loop-engine-agent-platform | MCP + harness |
| How serve LLMs? | vllm-architecture-lab | Inference education |

## A2A (future)

VAP specialists as **A2A peers** with Agent Cards — today: in-process LangGraph. Document, don't over-implement in pattern repos.

## ADR

[ADR-007](https://github.com/vpeetla-ai/ai-architecture-portfolio/blob/main/adr/ADR-007-2026-agent-protocol-stack.md)
