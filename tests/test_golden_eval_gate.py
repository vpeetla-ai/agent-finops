"""Real merge gate: agent_finops.outcome_invariant_v1 from golden-eval-registry."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from agent_finops.store import DEFAULT_HUMAN_MINUTE_USD, VERIFIED_OUTCOME_VALUES, cost_per_compliant_outcome
from agent_finops.store import SQLiteFinOpsStore

try:
    from golden_eval_registry.runner import score_suite
    from golden_eval_registry.schema import parse_manifest
    from golden_eval_registry.validate import load_jsonl

    GOLDEN_EVAL_REGISTRY_AVAILABLE = True
except ImportError:
    GOLDEN_EVAL_REGISTRY_AVAILABLE = False


def _default_registry_path() -> Path:
    env = os.getenv("GOLDEN_EVAL_REGISTRY_PATH")
    if env:
        return Path(env).resolve()
    candidates = [
        Path(__file__).resolve().parents[2] / "golden-eval-registry",
        Path(__file__).resolve().parents[1] / "golden-eval-registry",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


REGISTRY_PATH = _default_registry_path()
SUITE_DIR = REGISTRY_PATH / "suites" / "agent_finops_outcome_invariant_v1"

pytestmark = pytest.mark.skipif(
    not GOLDEN_EVAL_REGISTRY_AVAILABLE,
    reason="golden-eval-registry not installed",
)


def test_agent_finops_outcome_invariant_v1_suite_passes() -> None:
    if not SUITE_DIR.exists():
        if os.getenv("CI") or os.getenv("GOLDEN_EVAL_REGISTRY_PATH"):
            pytest.fail(f"agent-finops outcome suite missing at {SUITE_DIR}")
        pytest.skip("agent-finops outcome suite missing")
    manifest = parse_manifest(SUITE_DIR / "manifest.json")
    cases = load_jsonl(manifest.cases_path)
    kpi = cost_per_compliant_outcome(SQLiteFinOpsStore(":memory:"), tenant_id=None)
    actual = {
        "verified_outcome_enum": sorted(VERIFIED_OUTCOME_VALUES),
        "kpi_keys": sorted(kpi.keys()),
        "human_minute_usd_default": DEFAULT_HUMAN_MINUTE_USD,
    }
    actual_by_id = {str(case["id"]): actual for case in cases}
    result = score_suite(manifest, cases, actual_by_id)
    failures = "\n".join(f"{failure.case_id}: {failure.detail}" for failure in result.failures)
    assert result.passed, f"golden eval regressions:\n{failures}"
