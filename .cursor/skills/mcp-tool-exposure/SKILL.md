---
name: mcp-tool-exposure
description: >-
  Expose agent tools via Model Context Protocol (MCP): stdio servers, tool
  schemas, bridge pattern, permission boundaries. Use when adding MCP servers,
  wiring LoopForge/VAP tools, or documenting the 2026 tool-access layer.
---

# MCP Tool Exposure

## When to use MCP

- Agents need **files, search, APIs, git** — not raw shell
- Same tools must work in **Cursor, Claude Code, and custom agents**
- Tool calls need **audit + permission** boundaries (pair with AegisAI gateway)

## vpeetla-ai pattern

```text
Agent (MCP client) → MCP bridge → allowlisted tools → gateway (if side effect)
```

## LoopForge reference

- `loop-engine-agent-platform/src/loop_engine/mcp/bridge.py`
- Tools: `read_file`, `search_docs` — extend, never arbitrary `exec`

## Checklist for new MCP server

1. Define tool name, input schema, output schema
2. Allowlist only — no ambient filesystem
3. Log every invocation (trace_id, agent_id, params hash)
4. Side effects → **AegisAI gateway** or HITL

## 2026 context

MCP is the de facto **agent-to-tool** layer. A2A handles **agent-to-agent** — do not conflate.

Reference: [ADR-007](https://github.com/vpeetla-ai/ai-architecture-portfolio/blob/main/adr/ADR-007-2026-agent-protocol-stack.md)
