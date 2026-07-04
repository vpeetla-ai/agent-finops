import pytest

from agent_finops.models import UsageEvent
from agent_finops.store import SQLiteFinOpsStore


@pytest.fixture
def store():
    return SQLiteFinOpsStore(":memory:")


def _event(scope_value="agent-1", cost=1.0):
    return UsageEvent(
        scope_type="agent",
        scope_value=scope_value,
        provider="openai",
        model="gpt-4o-mini",
        prompt_tokens=1000,
        completion_tokens=200,
        cost_usd=cost,
    )


def test_record_usage_accumulates_total(store):
    store.record_usage(_event(cost=1.0))
    result = store.record_usage(_event(cost=2.0))
    assert result.total_cost_usd == 3.0


def test_scopes_are_independent(store):
    store.record_usage(_event(scope_value="agent-1", cost=5.0))
    result = store.record_usage(_event(scope_value="agent-2", cost=1.0))
    assert result.total_cost_usd == 1.0


def test_no_budget_never_breaches(store):
    result = store.record_usage(_event(cost=1_000_000.0))
    assert result.budget_usd is None
    assert result.breached is False


def test_budget_breach_detected(store):
    store.set_budget("agent", "agent-1", 5.0)
    store.record_usage(_event(cost=3.0))
    result = store.record_usage(_event(cost=3.0))
    assert result.total_cost_usd == 6.0
    assert result.budget_usd == 5.0
    assert result.breached is True


def test_under_budget_not_breached(store):
    store.set_budget("agent", "agent-1", 5.0)
    result = store.record_usage(_event(cost=2.0))
    assert result.breached is False


def test_set_budget_is_upsert(store):
    store.set_budget("agent", "agent-1", 5.0)
    updated = store.set_budget("agent", "agent-1", 10.0)
    assert updated.budget_usd == 10.0
    assert store.get_budget("agent", "agent-1").budget_usd == 10.0
