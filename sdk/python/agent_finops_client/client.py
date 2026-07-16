from __future__ import annotations

from dataclasses import dataclass

import httpx

from agent_finops.pricing import estimate_cost_usd


@dataclass(frozen=True)
class UsageResult:
    cost_usd: float
    total_cost_usd: float
    budget_usd: float | None
    breached: bool


class FinOpsClient:
    """Record real LLM usage against the agent-finops service.

    If `base_url` is unset, degrades gracefully: computes cost locally via the
    same pricing table and reports `breached=False` — matches the "fail open
    when not configured" convention used across this org (e.g. AegisAI's
    AEGISAI_GATEWAY_FAIL_OPEN) so a consumer repo never hard-fails just because
    this service isn't deployed yet.
    """

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout_seconds: float = 10.0,
    ) -> None:
        self.base_url = base_url.rstrip("/") if base_url else None
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    def record_usage(
        self,
        *,
        scope_type: str,
        scope_value: str,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> UsageResult:
        if not self.base_url:
            cost = estimate_cost_usd(model, prompt_tokens, completion_tokens)
            return UsageResult(cost_usd=cost, total_cost_usd=cost, budget_usd=None, breached=False)

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        payload = {
            "scope_type": scope_type,
            "scope_value": scope_value,
            "provider": provider,
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
        }
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(f"{self.base_url}/v1/usage", json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
        return UsageResult(
            cost_usd=data["cost_usd"],
            total_cost_usd=data["total_cost_usd"],
            budget_usd=data["budget_usd"],
            breached=data["breached"],
        )

    def get_budget_status(self, scope_type: str, scope_value: str) -> UsageResult:
        if not self.base_url:
            return UsageResult(cost_usd=0.0, total_cost_usd=0.0, budget_usd=None, breached=False)
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.get(f"{self.base_url}/v1/budget/{scope_type}/{scope_value}")
            response.raise_for_status()
            data = response.json()
        return UsageResult(
            cost_usd=0.0,
            total_cost_usd=data["total_cost_usd"],
            budget_usd=data["budget_usd"],
            breached=data["breached"],
        )


    def record_outcome(
        self,
        *,
        workflow_id: str,
        tenant_id: str,
        eval_pass: bool = True,
        policy_deny: bool = False,
        hitl_required: bool = False,
        hitl_approved: bool = True,
        budget_ok: bool = True,
        total_cost_usd: float = 0.0,
    ) -> dict:
        """ADR-029: record compliant-success bit for cost-per-compliant-outcome KPI."""
        payload = {
            "workflow_id": workflow_id,
            "tenant_id": tenant_id,
            "eval_pass": eval_pass,
            "policy_deny": policy_deny,
            "hitl_required": hitl_required,
            "hitl_approved": hitl_approved,
            "budget_ok": budget_ok,
            "total_cost_usd": total_cost_usd,
        }
        if not self.base_url:
            compliant = (
                eval_pass
                and not policy_deny
                and budget_ok
                and ((not hitl_required) or hitl_approved)
            )
            return {**payload, "compliant_success": compliant, "offline": True}
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(
                f"{self.base_url}/v1/outcomes", json=payload, headers=headers
            )
            response.raise_for_status()
            return response.json()

    def get_cost_per_compliant_outcome(self, tenant_id: str | None = None) -> dict:
        if not self.base_url:
            return {
                "kpi": "cost_per_compliant_outcome",
                "tenant_id": tenant_id,
                "compliant_outcomes": 0,
                "total_cost_usd": 0.0,
                "cost_per_compliant_outcome": None,
                "offline": True,
            }
        params = {"tenant_id": tenant_id} if tenant_id else None
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.get(
                f"{self.base_url}/v1/kpi/cost-per-compliant-outcome",
                params=params,
            )
            response.raise_for_status()
            return response.json()
