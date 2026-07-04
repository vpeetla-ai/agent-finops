---
name: production-observability
description: >-
  Add Langfuse, LangSmith, OpenTelemetry, or structured traces to agent APIs.
  Use when instrumenting graphs, measuring cost/latency, or building eval
  regression from production traces.
---

# Production Observability

## What to trace (minimum)

| Event | Fields |
|-------|--------|
| LLM call | model, tokens, latency_ms, run_id |
| Tool call | tool_name, params_hash, result_status |
| Graph node | node_name, step, routing_decision |
| Side effect | gateway_request_id, hitl_status |

## Org conventions

| Repo | Stack |
|------|-------|
| venkat-ai-platform | Langfuse optional |
| ai-content-factory | LangSmith + Langfuse + Sentry |
| enterprise_rag_platform | OTLP export |
| aegisloop-agentops-workbench | Langfuse spans |
| loop-engine-agent-platform | harness trace_events (add Langfuse P1) |

## Eval loop

1. Capture golden traces on happy path
2. Regression test routing + tool selection (not full LLM prose)
3. Alert on latency p99 + cost per successful task

## Anti-patterns

- Logging only final answer (loses reasoning chain)
- No run_id across gateway + orchestrator + RAG

Reference: [ORG_IMPROVEMENT_PLAN_2026](https://github.com/vpeetla-ai/ai-architecture-portfolio/blob/main/docs/ORG_IMPROVEMENT_PLAN_2026.md)
