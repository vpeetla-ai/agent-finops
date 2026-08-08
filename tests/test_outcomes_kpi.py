from fastapi.testclient import TestClient

from agent_finops.api.main import app

client = TestClient(app)


def test_outcome_kpi_happy_path():
    r = client.post(
        "/v1/outcomes",
        json={
            "workflow_id": "wf-kpi-1",
            "tenant_id": "omniforge",
            "eval_pass": True,
            "policy_deny": False,
            "hitl_required": False,
            "hitl_approved": True,
            "budget_ok": True,
            "total_cost_usd": 0.25,
            "human_review_minutes": 4.0,
            "verified_outcome": "verified",
        },
    )
    assert r.status_code == 200
    assert r.json()["compliant_success"] is True
    assert r.json()["verified_outcome"] == "verified"
    k = client.get("/v1/kpi/cost-per-compliant-outcome", params={"tenant_id": "omniforge"})
    assert k.status_code == 200
    body = k.json()
    assert body["compliant_outcomes"] >= 1
    assert body["cost_per_compliant_outcome"] is not None
    assert body["verified_outcomes"] >= 1
    assert body["total_human_review_minutes"] >= 4.0
    assert body["estimated_human_cost_usd"] >= 4.0 * body["human_minute_usd"]
    assert body["fully_loaded_cost_per_verified"] is not None
    assert "verified" in body["verified_outcome_enum"]


def test_outcome_noncompliant_when_policy_deny():
    r = client.post(
        "/v1/outcomes",
        json={
            "workflow_id": "wf-deny",
            "tenant_id": "vap",
            "eval_pass": True,
            "policy_deny": True,
            "budget_ok": True,
            "total_cost_usd": 1.0,
            "verified_outcome": "rejected",
        },
    )
    assert r.status_code == 200
    assert r.json()["compliant_success"] is False


def test_outcome_rejects_invalid_verified_enum():
    r = client.post(
        "/v1/outcomes",
        json={
            "workflow_id": "wf-bad-enum",
            "tenant_id": "vap",
            "verified_outcome": "shipped",
        },
    )
    assert r.status_code == 422
