---
name: agents-that-run-for-days
description: >-
  Karpathy field notes — agents that run for days: program.md control layer,
  constrained edit surface, fixed eval harness, keep/discard loops, overnight
  autonomy. Use when designing LoopForge overnight runs, autoresearch-style
  harnesses, or LOOPS.md field notes in any vpeetla-ai repo.
---

# Agents That Run for Days (LOOPS.md field notes)

Inspired by Andrej Karpathy's [autoresearch](https://github.com/karpathy/autoresearch) and the shift from **prompt engineering → loop engineering** — agents that hypothesize, execute, measure, and iterate while you sleep.

## North star

> Remove yourself as the bottleneck on the **inner loop**. Stay the engineer on the **outer loop** (strategy, metrics, constraints, review).

## The three-file contract (Karpathy pattern)

| File | Who owns | Role |
|------|----------|------|
| `program.md` / `LOOPS.md` | **Human** | Strategy — goals, constraints, loop protocol, what to never touch |
| `train.py` / **one mutable surface** | **Agent** | Tactics — the only file (or tool scope) the agent may edit per round |
| `prepare.py` / **locked eval** | **Human** | Measurement — scoring harness the agent cannot modify (prevents metric cheating) |

In vpeetla-ai repos, map this to:

| Karpathy | LoopForge | Content Factory | Enterprise RAG |
|----------|-----------|-----------------|----------------|
| `program.md` | `loops/*.yaml` + harness config | `AGENTS.md` + pipeline spec | golden queries + eval gates |
| mutable file | `train.py` → repo patches / RAG config | draft nodes | retrieval strategy params |
| locked eval | `pytest` + review score | HITL + gateway | `eval/metrics.py` |

## LOOPS.md template (field notes)

Create `docs/LOOPS.md` or `LOOPS.md` at repo root when an agent should run overnight:

```markdown
# LOOPS — [Project name]

## Who this loop serves
- **User:** [role — e.g. platform engineer, content editor]
- **Job:** [one sentence outcome]

## Metric (one number)
- **Optimize:** [e.g. pytest pass rate, recall@5, review score]
- **Direction:** lower / higher is better
- **Floor:** never ship below [X]

## Mutable surface (agent MAY edit)
- [single file or bounded tool list]

## Locked (agent MUST NOT edit)
- eval harness, prepare.py, gateway rules, CI workflows

## Time budget per iteration
- [e.g. 5 min train, 3 min pytest, max 12 iter/hour]

## Loop protocol
1. Read state + memory hints
2. Hypothesize change
3. Apply to mutable surface only
4. Run locked eval
5. If improved → commit + lesson; else → revert
6. Repeat until budget exhausted or metric plateaus

## Stop conditions
- max iterations, cost cap, no improvement for N rounds, gateway block

## Learnings log
Append after each round: what worked, what failed, next hypothesis.
```

## Design rules (from field notes)

1. **One metric** — one comparable number per iteration; fixed time budget makes runs comparable
2. **Constraint is the feature** — narrow action space beats unlimited agent scope
3. **Markdown as programming** — `program.md` / `LOOPS.md` is the control plane, not comments in code
4. **Keep or discard** — git commit on win, `git reset` on loss (LoopForge: branch + PR, never `main`)
5. **Babysit vs overnight** — interactive tmux sessions for learning; unattended only with recovery + logs
6. **Gateway on side effects** — publish, push, deploy still require AegisAI even in long loops

## Map to vpeetla-ai stack

```text
LOOPS.md (strategy)  →  Harness (scheduler, budget)  →  Agent (inner loop)
                              ↓
                         Evaluate (pytest, golden, eval gates)
                              ↓
                         Memory (lessons, RAG version tree)
                              ↓
                         Observability (trace, Langfuse, OTLP)
```

- **LoopForge:** ODAEU harness + repo-fix graph — closest to autoresearch in org
- **Content Factory:** HITL breaks unattended publish — by design
- **Enterprise RAG:** golden query regression = locked eval
- **Skills:** when same reminder twice → SKILL.md or LOOPS.md, not chat

## Anti-patterns

- Agent edits eval metric or `prepare.py` equivalent
- Unbounded scope ("improve the whole repo")
- Overnight run without trace export or iteration log
- Side effects without gateway in unattended mode

## References

- [karpathy/autoresearch](https://github.com/karpathy/autoresearch) — overnight ML experiments
- Org skill: `loop-engineering` — ODAEU implementation
- Org skill: `agentic-engineering` — surgical diffs, verify before done
- [ADR-007](https://github.com/vpeetla-ai/ai-architecture-portfolio/blob/main/adr/ADR-007-2026-agent-protocol-stack.md) — protocol stack
- Karpathy: [From Vibe Coding to Agentic Engineering](https://www.youtube.com/watch?v=96jN2OCOfLs)
