"""FastAPI — real usage metering + budget status for AI agent fleets."""

from __future__ import annotations

import os
import secrets
from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agent_finops.models import UsageEvent
from agent_finops.pricing import estimate_cost_usd
from agent_finops.store import build_store, cost_per_compliant_outcome, record_workflow_outcome

app = FastAPI(title="Agent FinOps", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

store = build_store()


def _require_api_key(x_api_key: Annotated[str | None, Header()] = None) -> None:
    """Gate POST/PUT — recording usage and setting budgets are the only mutating
    routes here. Only enforced when AGENTFINOPS_API_KEY is set (dev/demo open)."""
    expected = os.getenv("AGENTFINOPS_API_KEY")
    if not expected:
        return
    if not x_api_key or not secrets.compare_digest(x_api_key, expected):
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key")


class RecordUsageRequest(BaseModel):
    scope_type: str
    scope_value: str
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int


class SetBudgetRequest(BaseModel):
    budget_usd: float


class WorkflowOutcomeRequest(BaseModel):
    workflow_id: str
    tenant_id: str
    eval_pass: bool = True
    policy_deny: bool = False
    hitl_required: bool = False
    hitl_approved: bool = True
    budget_ok: bool = True
    total_cost_usd: float = 0.0


@app.get("/v1/ops/metrics")
def ops_metrics() -> dict:
    agg = store.aggregate_ops() if hasattr(store, "aggregate_ops") else {"usage_events": 0, "total_cost_usd": 0.0, "budgets_configured": 0}
    return {
        "service": "agent-finops",
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "total_runs": agg.get("usage_events", 0),
        "success_rate_pct": 100.0,
        "p95_latency_ms": None,
        "active_entities": agg.get("budgets_configured", 0),
        "slo": {"target_uptime_pct": 99.5, "success_target_pct": 95.0},
        "extra": agg,
    }


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "agent-finops"}


@app.post("/v1/usage", dependencies=[Depends(_require_api_key)])
def record_usage(body: RecordUsageRequest) -> dict:
    cost_usd = estimate_cost_usd(body.model, body.prompt_tokens, body.completion_tokens)
    event = UsageEvent(
        scope_type=body.scope_type,
        scope_value=body.scope_value,
        provider=body.provider,
        model=body.model,
        prompt_tokens=body.prompt_tokens,
        completion_tokens=body.completion_tokens,
        cost_usd=cost_usd,
    )
    result = store.record_usage(event)
    return {
        "scope_type": result.scope_type,
        "scope_value": result.scope_value,
        "cost_usd": result.cost_usd,
        "total_cost_usd": result.total_cost_usd,
        "budget_usd": result.budget_usd,
        "breached": result.breached,
    }


@app.get("/v1/budget/{scope_type}/{scope_value}")
def get_budget(scope_type: str, scope_value: str) -> dict:
    budget = store.get_budget(scope_type, scope_value)
    total = store.total_cost(scope_type, scope_value)
    return {
        "scope_type": scope_type,
        "scope_value": scope_value,
        "budget_usd": budget.budget_usd if budget else None,
        "total_cost_usd": total,
        "breached": bool(budget and total > budget.budget_usd),
    }


@app.put("/v1/budget/{scope_type}/{scope_value}", dependencies=[Depends(_require_api_key)])
def set_budget(scope_type: str, scope_value: str, body: SetBudgetRequest) -> dict:
    budget = store.set_budget(scope_type, scope_value, body.budget_usd)
    return {"scope_type": budget.scope_type, "scope_value": budget.scope_value, "budget_usd": budget.budget_usd}



@app.post("/v1/outcomes", dependencies=[Depends(_require_api_key)])
def record_outcome(body: WorkflowOutcomeRequest) -> dict:
    """Record compliant-success bit for cost-per-compliant-outcome KPI (ADR-029)."""
    compliant = (
        body.eval_pass
        and not body.policy_deny
        and body.budget_ok
        and ((not body.hitl_required) or body.hitl_approved)
    )
    row = {
        "workflow_id": body.workflow_id,
        "tenant_id": body.tenant_id,
        "compliant_success": compliant,
        "eval_pass": body.eval_pass,
        "policy_deny": body.policy_deny,
        "hitl_required": body.hitl_required,
        "hitl_approved": body.hitl_approved,
        "budget_ok": body.budget_ok,
        "total_cost_usd": body.total_cost_usd,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
    record_workflow_outcome(store, row)
    return {**row, "compliant_success": compliant}


@app.get("/v1/kpi/cost-per-compliant-outcome")
def kpi_cost_per_compliant_outcome(tenant_id: str | None = None) -> dict:
    return {
        "service": "agent-finops",
        "kpi": "cost_per_compliant_outcome",
        **cost_per_compliant_outcome(store, tenant_id),
    }
