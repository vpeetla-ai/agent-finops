"""Canonical LLM pricing — the one place rates live instead of N per-repo copies.

Rates are USD per 1M tokens, blended where providers price prompt/completion
tokens differently is intentionally not modeled here (v1) — see the fallback
note below for why an unknown model still gets a real, non-zero estimate.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelRate:
    prompt_per_million: float
    completion_per_million: float


# Sourced from each provider's public pricing pages at time of writing. Update
# here — nowhere else — when rates change.
RATES: dict[str, ModelRate] = {
    "gpt-4.1-mini": ModelRate(prompt_per_million=0.40, completion_per_million=1.60),
    "gpt-4o-mini": ModelRate(prompt_per_million=0.15, completion_per_million=0.60),
    "gemini-2.0-flash": ModelRate(prompt_per_million=0.10, completion_per_million=0.40),
    "llama3.2:3b": ModelRate(prompt_per_million=0.0, completion_per_million=0.0),  # local/Ollama
}

# Applied when a model isn't in RATES — a real, non-zero estimate, not a silent
# $0, so an unrecognized model never masquerades as free.
FALLBACK_RATE = ModelRate(prompt_per_million=0.50, completion_per_million=1.50)


def estimate_cost_usd(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> float:
    """Return the real dollar cost for a completion, given real token counts."""
    if prompt_tokens < 0 or completion_tokens < 0:
        raise ValueError("token counts must be non-negative")
    rate = RATES.get(model, FALLBACK_RATE)
    cost = (
        prompt_tokens * rate.prompt_per_million
        + completion_tokens * rate.completion_per_million
    ) / 1_000_000
    return round(cost, 8)
