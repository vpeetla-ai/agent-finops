from fastapi.testclient import TestClient

from agent_finops.api.main import app

client = TestClient(app)

USAGE_BODY = {
    "scope_type": "agent",
    "scope_value": "agent-test",
    "provider": "openai",
    "model": "gpt-4o-mini",
    "prompt_tokens": 1000,
    "completion_tokens": 200,
}


def test_health_open():
    resp = client.get("/health")
    assert resp.status_code == 200


def test_usage_open_when_no_api_key_set(monkeypatch):
    monkeypatch.delenv("AGENTFINOPS_API_KEY", raising=False)
    resp = client.post("/v1/usage", json=USAGE_BODY)
    assert resp.status_code == 200
    body = resp.json()
    assert body["cost_usd"] > 0


def test_usage_rejects_missing_key_when_required(monkeypatch):
    monkeypatch.setenv("AGENTFINOPS_API_KEY", "secret-key")
    resp = client.post("/v1/usage", json=USAGE_BODY)
    assert resp.status_code == 401


def test_usage_rejects_wrong_key(monkeypatch):
    monkeypatch.setenv("AGENTFINOPS_API_KEY", "secret-key")
    resp = client.post("/v1/usage", json=USAGE_BODY, headers={"X-API-Key": "wrong"})
    assert resp.status_code == 401


def test_usage_accepts_correct_key(monkeypatch):
    monkeypatch.setenv("AGENTFINOPS_API_KEY", "secret-key")
    resp = client.post("/v1/usage", json=USAGE_BODY, headers={"X-API-Key": "secret-key"})
    assert resp.status_code == 200


def test_budget_get_open_regardless_of_key(monkeypatch):
    monkeypatch.setenv("AGENTFINOPS_API_KEY", "secret-key")
    resp = client.get("/v1/budget/agent/agent-test")
    assert resp.status_code == 200


def test_set_budget_requires_key_when_configured(monkeypatch):
    monkeypatch.setenv("AGENTFINOPS_API_KEY", "secret-key")
    resp = client.put("/v1/budget/agent/agent-budget-test", json={"budget_usd": 5.0})
    assert resp.status_code == 401


def test_budget_breach_end_to_end(monkeypatch):
    monkeypatch.delenv("AGENTFINOPS_API_KEY", raising=False)
    client.put("/v1/budget/agent/agent-breach-test", json={"budget_usd": 0.01})
    body = dict(USAGE_BODY, scope_value="agent-breach-test", prompt_tokens=1_000_000)
    resp = client.post("/v1/usage", json=body)
    assert resp.status_code == 200
    assert resp.json()["breached"] is True
