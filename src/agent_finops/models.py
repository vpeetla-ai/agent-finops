"""Domain types for usage events and budgets."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

ScopeType = str  # "agent" | "tenant" | "repo" — deliberately a plain str, not an
# enum: consumers (AegisAI's per-agent budgets, AegisLoop's per-mission/per-repo
# budgets) each have their own scope vocabulary; this service just needs a
# stable key to sum against, not to validate what it means.


@dataclass(frozen=True)
class UsageEvent:
    scope_type: ScopeType
    scope_value: str
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    recorded_at: str = ""

    def __post_init__(self) -> None:
        if not self.recorded_at:
            object.__setattr__(self, "recorded_at", datetime.now(UTC).isoformat())


@dataclass(frozen=True)
class Budget:
    scope_type: ScopeType
    scope_value: str
    budget_usd: float


@dataclass(frozen=True)
class UsageResult:
    scope_type: ScopeType
    scope_value: str
    cost_usd: float
    total_cost_usd: float
    budget_usd: float | None
    breached: bool
