---
name: governed-ai-stack
description: >-
  Maps tasks to the vpeetla-ai reference stack (VAP, AegisAI, RAG, AgentOps,
  Content, LoopForge, vLLM Lab, Skills). Use when choosing which repo to change.
---

# Governed AI Stack

Read [CONTEXT.md](../../CONTEXT.md) for terms.

## Layer routing

| If the task is about… | Work in… |
|------------------------|----------|
| Multi-agent orchestration, RAG strategies, notify | venkat-ai-platform |
| Policy, HITL, audit, tool authorization | aegisai-enterprise-agent-platform |
| Retrieval, citations, access control | enterprise_rag_platform |
| Missions, traces, eval gates, FinOps | aegisloop-agentops-workbench |
| Content pipeline, publish, cron | ai-content-factory |
| Self-improving loops, repo fix, RAG tuning | loop-engine-agent-platform |
| LLM inference, KV cache, batching education | vllm-architecture-lab |
| Golden eval fixtures, regression contracts, cross-repo quality proof | golden-eval-registry |
| Agent skills, MCP, protocol stack | vpeetla-ai-skills |
| ADRs, case studies, portfolio copy | ai-architecture-portfolio |
| Public site, ecosystem wiring | venkat-ai-portfolio |
| Single pattern reference (ReAct, etc.) | *-agent-pattern repos |

## Integration rules

- VAP **delegates** side effects; AegisAI **authorizes** them
- Enterprise RAG **feeds** VAP strategies; does not replace gateway
- LoopForge **improves** configs/prompts; does not replace orchestration

## Essay

[From Multi-Agent OS to Agent Governance](https://github.com/vpeetla-ai/ai-architecture-portfolio/blob/main/case-studies/from-multi-agent-os-to-agent-governance.md)
